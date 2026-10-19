"""
Main FAQ search engine.
Combines TF-IDF similarity + keyword overlap + fuzzy matching.
100% offline — all computation is local.
"""
import re
import logging
from difflib import SequenceMatcher

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

STOPWORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'of', 'in', 'on',
    'at', 'to', 'for', 'with', 'by', 'from', 'as', 'and', 'or', 'but',
    'if', 'then', 'so', 'that', 'this', 'these', 'those', 'i', 'you',
    'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'its', 'our', 'their', 'what', 'how', 'when',
    'where', 'who', 'why', 'which', 'please', 'help', 'need', 'want',
    'get', 'make', 'know', 'about', 'there', 'here', 'just', 'also'
}


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-\?\.]", ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def tokenize(text: str) -> list:
    return [t for t in normalize(text).split() if t and t not in STOPWORDS]


def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


class FAQSearchEngine:
    """Singleton-style matching engine. Call refresh() when FAQs change."""

    def __init__(self):
        self.faqs = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self._built = False

    def build(self, faqs):
        """faqs: list of dicts {id, question, answer, keywords, category, priority}"""
        self.faqs = list(faqs)
        if not self.faqs:
            self._built = False
            return

        docs = []
        for f in self.faqs:
            parts = [f['question']]
            if f.get('keywords'):
                parts.append(f['keywords'])
            if f.get('category'):
                parts.append(f['category'])
            parts.append(' '.join(tokenize(f['question'])))
            docs.append(normalize(' '.join(parts)))

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
            token_pattern=r'\b\w+\b'
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(docs)
        self._built = True
        logger.info(f"Search engine built with {len(self.faqs)} entries")

    def refresh(self):
        from .models import FAQ
        qs = FAQ.objects.filter(is_active=True).select_related('category')
        faqs = [{
            'id': f.id,
            'question': f.question,
            'answer': f.answer,
            'keywords': f.keywords or '',
            'category': f.category.name if f.category else '',
            'priority': f.priority,
        } for f in qs]
        self.build(faqs)

    def search(self, query: str, top_k: int = 3, threshold: float = 0.15):
        if not self._built or not query.strip():
            return []

        norm_q = normalize(query)
        q_tokens = set(tokenize(query))

        q_vec = self.vectorizer.transform([norm_q])
        sims = cosine_similarity(q_vec, self.tfidf_matrix).flatten()

        boosted = sims.copy()
        for i, faq in enumerate(self.faqs):
            faq_text = normalize(faq['question'] + ' ' + faq.get('keywords', ''))
            faq_tokens = set(tokenize(faq_text))

            if q_tokens and faq_tokens:
                overlap = len(q_tokens & faq_tokens) / len(q_tokens)
                boosted[i] += overlap * 0.25

            if norm_q and norm_q in normalize(faq['question']):
                boosted[i] += 0.3

            if len(q_tokens) <= 4:
                ratio = fuzzy_ratio(norm_q, normalize(faq['question']))
                if ratio > 0.6:
                    boosted[i] += ratio * 0.15

            boosted[i] += min(faq.get('priority', 0), 10) * 0.005

        idxs = np.argsort(boosted)[::-1][:top_k]
        results = []
        for i in idxs:
            score = float(boosted[i])
            if score >= threshold:
                results.append((self.faqs[i], round(score, 3)))
        return results


# Global instance
search_engine = FAQSearchEngine()