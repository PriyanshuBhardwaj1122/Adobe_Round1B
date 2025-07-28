"""Cross‑document synthesis and sub‑section refinement.

This module provides a function to refine the top ranked sections into
shorter summaries.  It extracts the most relevant sentences based on
term overlap with the persona and job description.  Although simplistic,
this approach reduces the amount of text presented to the user while
preserving key information.
"""

from __future__ import annotations

import re
from typing import List, Dict, Tuple


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences based on punctuation.

    Args:
        text: Raw text of a section.

    Returns:
        A list of sentences.  Sentences shorter than 20 characters are filtered out.
    """
    # Basic sentence splitter on period, exclamation or question mark
    parts = re.split(r"(?<=[.!?])\s+", text)
    # Trim and filter very short sentences
    sentences = [p.strip() for p in parts if len(p.strip()) > 20]
    return sentences


def _score_sentence(sentence: str, query_terms: set) -> float:
    """Compute a simple relevance score for a sentence.

    The score is the number of query terms appearing in the sentence divided by
    the total number of unique words in the sentence.  Terms are compared
    case‑insensitively after removing punctuation.
    """
    words = re.sub(r"[^a-zA-Z0-9\s]", " ", sentence.lower()).split()
    if not words:
        return 0.0
    overlap = query_terms.intersection(words)
    return len(overlap) / len(set(words))


def refine_subsections(
    ranked_sections: List[Dict[str, object]],
    persona: Dict[str, str],
    job: Dict[str, str],
    top_n: int = 5,
) -> List[Dict[str, object]]:
    """Generate refined summaries for the top ranked sections.

    Args:
        ranked_sections: Sections sorted by importance.  Must contain at least
            ``text``, ``document`` and ``page_number``.
        persona: Persona definition with ``role`` and optional ``description``.
        job: Job‑to‑be‑done definition with ``task``.
        top_n: Number of sections to summarise.  Defaults to 5.

    Returns:
        A list of dictionaries with keys ``document``, ``refined_text`` and
        ``page_number``.
    """
    results: List[Dict[str, object]] = []
    # Build a set of query terms from persona and job description
    query = f"{persona.get('role', '')} {persona.get('description', '')} {job.get('task', '')}"
    # Lowercase and strip punctuation
    query_terms = set(
        re.sub(r"[^a-zA-Z0-9\s]", " ", query.lower()).split()
    )
    # Limit to top N sections
    for section in ranked_sections[:top_n]:
        text = section.get("text", "")
        sentences = _split_into_sentences(text)
        if not sentences:
            refined = text.strip()[:300]
        else:
            # Score each sentence and select top two
            scored: List[Tuple[str, float]] = [
                (sent, _score_sentence(sent, query_terms)) for sent in sentences
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            top_sents = [s for s, _ in scored[:2]]
            refined = " " .join(top_sents).strip()
        results.append(
            {
                "document": section.get("document"),
                "refined_text": refined,
                "page_number": section.get("page_number"),
            }
        )
    return results


__all__ = ["refine_subsections"]