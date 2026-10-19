"""
Fast autocomplete suggestions for the chat input.
Uses a pre-built in-memory index for instant lookups (< 5ms).
100% offline — no external APIs.
"""
import re
import threading
from functools import lru_cache
from difflib import SequenceMatcher


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-\?\.]", ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


class AutocompleteIndex:
    """
    Thread-safe in-memory index for live suggestions.
    Rebuilt whenever FAQs change.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._entries = []      # list of {id, question, keywords, category, views}
        self._prefix_map = {}   # first-word -> [entry indices]
        self._built = False

    def build(self, entries):
        """entries: list of dicts with id, question, keywords, category, views"""
        with self._lock:
            self._entries = list(entries)
            self._prefix_map = {}
            for idx, e in enumerate(self._entries):
                normalized = _normalize(e['question'])
                # Index by every word in the question
                for word in set(normalized.split()):
                    if len(word) >= 2:
                        self._prefix_map.setdefault(word[:3], []).append(idx)
            self._built = True

    def refresh(self):
        """Reload from database."""
        from .models import FAQ
        qs = FAQ.objects.filter(is_active=True).values(
            'id', 'question', 'keywords', 'views',
            'category__name'
        )
        entries = [{
            'id': f['id'],
            'question': f['question'],
            'keywords': f['keywords'] or '',
            'category': f['category__name'] or '',
            'views': f['views'] or 0,
        } for f in qs]
        self.build(entries)

    def suggest(self, query: str, limit: int = 6, min_score: float = 0.25):
        """
        Return top suggestions for the given partial query.
        Fast enough to run on every keystroke.
        """
        if not self._built or not query or len(query.strip()) < 2:
            return []

        with self._lock:
            entries = self._entries
            q = _normalize(query)
            q_tokens = q.split()

            # Step 1: Candidate filtering via prefix map (fast)
            candidate_ids = set()
            for tok in q_tokens:
                if len(tok) >= 3:
                    candidate_ids.update(self._prefix_map.get(tok[:3], []))

            # If no prefix candidates, fall back to all (still fast for <10k FAQs)
            candidates = (
                [entries[i] for i in candidate_ids]
                if candidate_ids else entries
            )

            # Step 2: Score each candidate
            scored = []
            for e in candidates:
                score = self._score(q, q_tokens, e)
                if score >= min_score:
                    scored.append((score, e))

            # Step 3: Sort & trim
            scored.sort(key=lambda x: (-x[0], -x[1]['views']))
            return [
                {
                    'id': e['id'],
                    'question': e['question'],
                    'category': e['category'],
                    'score': round(score, 3),
                }
                for score, e in scored[:limit]
            ]

    @staticmethod
    @lru_cache(maxsize=2048)
    def _score_cached(q: str, q_tokens: tuple, question_norm: str,
                      keywords_norm: str, views: int) -> float:
        score = 0.0

        # Exact substring match (strong signal)
        if q in question_norm:
            score += 0.5 + 0.05 * min(len(q) / 20, 1)

        # Prefix match on any word
        for tok in q_tokens:
            for word in question_norm.split():
                if word.startswith(tok):
                    score += 0.15

        # Keyword matches
        for tok in q_tokens:
            if tok in keywords_norm:
                score += 0.2

        # Fuzzy fallback (for typos)
        if score < 0.2 and len(q) >= 3:
            ratio = SequenceMatcher(None, q, question_norm).ratio()
            if ratio > 0.55:
                score += ratio * 0.4

        # Popularity nudge
        score += min(views / 1000.0, 0.1)

        return min(score, 1.0)

    def _score(self, q: str, q_tokens: list, entry: dict) -> float:
        qn = _normalize(entry['question'])
        kn = _normalize(entry.get('keywords', ''))
        return self._score_cached(q, tuple(q_tokens), qn, kn, entry['views'])


# Global instance
autocomplete_index = AutocompleteIndex()