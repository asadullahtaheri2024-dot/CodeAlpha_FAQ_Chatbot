import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import F
from django.core.cache import cache

from .models import FAQ, Category, Conversation, Message, UnansweredQuery
from .search_engine import search_engine
from .autocomplete import autocomplete_index
from .domain_guard import classify_domain, REFUSAL_MESSAGE

CAPABILITY_QUERIES = {
    "what can you do", "what can you use for", "what are you",
    "who are you", "what can i ask", "what can you help with",
    "what topics", "what subjects", "what do you know",
    "help", "capabilities", "what can you answer",
    "how can you help", "what is your purpose"
}

def _ensure_indexes_ready():
    if not cache.get('indexes_ready'):
        search_engine.refresh()
        autocomplete_index.refresh()
        cache.set('indexes_ready', True, 300)

@ensure_csrf_cookie
def chat_view(request):
    if not request.session.session_key:
        request.session.create()
    _ensure_indexes_ready()

    categories = Category.objects.all()
    popular = FAQ.objects.filter(is_active=True).order_by('-views')[:5]
    return render(request, 'chatbot/chat.html', {
        'categories': categories,
        'popular': popular,
    })

def _get_conversation(request):
    if not request.session.session_key:
        request.session.create()
    sk = request.session.session_key
    conv, _ = Conversation.objects.get_or_create(
        session_key=sk,
        defaults={'user_agent': request.META.get('HTTP_USER_AGENT', '')[:300]}
    )
    return conv

@require_GET
def api_suggest(request):
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({'suggestions': []})

    _ensure_indexes_ready()
    suggestions = autocomplete_index.suggest(query, limit=6)
    return JsonResponse({'suggestions': suggestions})

@require_POST
def api_ask(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    query = (data.get('message') or '').strip()
    if not query:
        return JsonResponse({'error': 'Empty message'}, status=400)
    if len(query) > 500:
        return JsonResponse({'error': 'Message too long'}, status=400)

    _ensure_indexes_ready()
    conv = _get_conversation(request)
    Message.objects.create(conversation=conv, sender='user', text=query)

    # 1. Check for Capability Questions
    q_lower = query.lower().strip()
    if q_lower in CAPABILITY_QUERIES or any(phrase in q_lower for phrase in CAPABILITY_QUERIES):
        faq = FAQ.objects.filter(question__icontains="what can i use this chatbot for").first()
        if faq:
            return JsonResponse({
                'type': 'answer', 'answer': faq.answer, 'question': faq.question,
                'faq_id': faq.id, 'confidence': 1.0,
                'category': 'Artificial Intelligence', 'suggestions': [],
            })

    # 2. Domain guard
    is_cs, domain_conf, subfield = classify_domain(query)

    if not is_cs:
        UnansweredQuery.objects.get_or_create(
            query__iexact=query,
            defaults={'query': f"[OFF-TOPIC] {query}", 'count': 1}
        )
        Message.objects.create(conversation=conv, sender='bot', text=REFUSAL_MESSAGE, confidence=0.0)
        return JsonResponse({
            'type': 'refusal', 'answer': REFUSAL_MESSAGE, 'confidence': 0.0,
            'suggestions': [
                {'id': s['id'], 'question': s['question'], 'score': 0}
                for s in FAQ.objects.filter(is_active=True).order_by('-priority', '-views')[:4].values('id', 'question')
            ],
        })

    # 3. Search
    results = search_engine.search(query, top_k=3)

    if results:
        faq, confidence = results[0]
        if confidence < 0.2:
            return _refuse_weak_match(conv, query)

        FAQ.objects.filter(id=faq['id']).update(views=F('views') + 1)
        faq_obj = FAQ.objects.get(id=faq['id'])

        Message.objects.create(conversation=conv, sender='bot', text=faq['answer'], matched_faq=faq_obj, confidence=confidence)

        suggestions = [{'id': r[0]['id'], 'question': r[0]['question'], 'score': r[1]} for r in results[1:]]

        return JsonResponse({
            'type': 'answer', 'answer': faq['answer'], 'question': faq['question'],
            'faq_id': faq['id'], 'confidence': confidence,
            'category': faq.get('category', ''), 'suggestions': suggestions,
        })

    return _refuse_weak_match(conv, query)

def _refuse_weak_match(conv, query):
    UnansweredQuery.objects.get_or_create(
        query__iexact=query,
        defaults={'query': query, 'count': 1}
    )
    fallback = list(FAQ.objects.filter(is_active=True).order_by('-priority', '-views')[:5].values('id', 'question'))
    msg = "🤔 That's a Computer Science topic, but I don't have a specific answer in my knowledge base yet. Here are some related questions you might find useful:"
    
    Message.objects.create(conversation=conv, sender='bot', text=msg, confidence=0.0)
    return JsonResponse({
        'type': 'fallback', 'answer': msg, 'confidence': 0.0,
        'suggestions': [{'id': s['id'], 'question': s['question'], 'score': 0} for s in fallback],
    })

@require_POST
def api_feedback(request):
    try:
        data = json.loads(request.body)
        faq_id = int(data.get('faq_id'))
        helpful = bool(data.get('helpful'))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid payload'}, status=400)

    field = 'helpful_count' if helpful else 'not_helpful_count'
    FAQ.objects.filter(id=faq_id).update(**{field: F(field) + 1})
    return JsonResponse({'ok': True})

def api_faq_detail(request, faq_id):
    try:
        faq = FAQ.objects.select_related('category').get(id=faq_id, is_active=True)
    except FAQ.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    FAQ.objects.filter(id=faq_id).update(views=F('views') + 1)
    return JsonResponse({
        'id': faq.id, 'question': faq.question, 'answer': faq.answer,
        'category': faq.category.name if faq.category else '',
    })

@require_POST
def api_reset(request):
    conv = _get_conversation(request)
    conv.messages.all().delete()
    return JsonResponse({'ok': True})