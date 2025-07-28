"""Content analysis and relevance scoring.

This module provides functions to compute semantic similarity scores between
sections and a persona/job description using TF‑IDF and cosine similarity.
Additional heuristics for persona overlap, actionability and cross‑document
importance are implemented here.  The weights for each component can be
adjusted via constants at the top of the file.
"""

from __future__ import annotations

from typing import List, Dict, Tuple, Iterable
import re
import math
from collections import Counter

# Weight constants for the relevance score
WEIGHT_SEMANTIC = 0.40
WEIGHT_PERSONA = 0.25
WEIGHT_ACTION = 0.20
WEIGHT_CROSS_DOC = 0.15

# A small list of action verbs to approximate "actionability"
ACTION_VERBS = {
    "create", "design", "develop", "optimize", "optimise",
    "evaluate", "analyze", "analyse", "build", "identify", "summarize",
    "summarise", "implement", "compare", "assess", "improve", "discover",
    "predict", "plan", "execute", "monitor", "measure"
}


def _clean_text(text: str) -> str:
    """Lowercase and remove non‑alphanumeric characters for simple matching."""
    return re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())


def _tokenize(text: str) -> List[str]:
    """Tokenize and normalise a piece of text into lower‑cased words without punctuation."""
    return re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower()).split()


def _compute_tf(words: List[str]) -> Dict[str, float]:
    """Compute term frequency for a list of words."""
    if not words:
        return {}
    counts = Counter(words)
    total = len(words)
    return {w: c / total for w, c in counts.items()}


def _compute_idf(doc_tokens: List[List[str]]) -> Dict[str, float]:
    """Compute inverse document frequency for a list of documents (token lists)."""
    idf: Dict[str, float] = {}
    total_docs = len(doc_tokens)
    # Count documents containing each term
    doc_counts: Dict[str, int] = {}
    for tokens in doc_tokens:
        seen = set(tokens)
        for token in seen:
            doc_counts[token] = doc_counts.get(token, 0) + 1
    for token, doc_count in doc_counts.items():
        # Add 1 to numerator and denominator to avoid division by zero
        idf[token] = math.log((1 + total_docs) / (1 + doc_count)) + 1.0
    return idf


def _compute_tfidf_vector(tf: Dict[str, float], idf: Dict[str, float]) -> Dict[str, float]:
    """Compute a TF‑IDF vector from term frequency and IDF dictionaries."""
    return {word: tf_val * idf.get(word, 0.0) for word, tf_val in tf.items()}


def _cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors represented as dicts."""
    if not vec1 or not vec2:
        return 0.0
    # Compute dot product
    dot = 0.0
    # Iterate over smaller vector for efficiency
    if len(vec1) < len(vec2):
        for word, val in vec1.items():
            dot += val * vec2.get(word, 0.0)
    else:
        for word, val in vec2.items():
            dot += val * vec1.get(word, 0.0)
    # Compute norms
    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def compute_semantic_similarity(sections: List[Dict[str, object]], query: str) -> List[float]:
    """Compute cosine similarity between each section and the query using TF‑IDF.

    This implementation avoids external libraries by computing TF‑IDF vectors
    manually.  It uses simple tokenization and sparse vector representations.

    Args:
        sections: List of section dictionaries with a ``text`` field.
        query: A combined persona/job description string.

    Returns:
        A list of similarity scores corresponding to each section.
    """
    # Build tokenised documents for query and sections
    section_tokens = [_tokenize(sec.get("text", "")) for sec in sections]
    query_tokens = _tokenize(query)
    # Compute IDF across all documents (query + sections)
    idf = _compute_idf([query_tokens] + section_tokens)
    # Compute TF-IDF vectors
    query_tf = _compute_tf(query_tokens)
    query_vec = _compute_tfidf_vector(query_tf, idf)
    sims: List[float] = []
    for tokens in section_tokens:
        tf = _compute_tf(tokens)
        vec = _compute_tfidf_vector(tf, idf)
        sims.append(_cosine_similarity(vec, query_vec))
    return sims


def compute_persona_match(sections: List[Dict[str, object]], persona_role: str) -> List[float]:
    """Compute persona word overlap scores for each section.

    The score is the fraction of unique words from the persona role that
    appear in the section text.  Both strings are lowercased and stripped of
    punctuation for comparison.

    Args:
        sections: List of section dictionaries with a ``text`` field.
        persona_role: The persona role string (e.g. "PhD Researcher in Computational Biology").

    Returns:
        A list of scores in [0, 1].
    """
    persona_words = set(_clean_text(persona_role).split())
    scores: List[float] = []
    for sec in sections:
        sec_words = set(_clean_text(sec.get("text", "")).split())
        if not persona_words or not sec_words:
            scores.append(0.0)
        else:
            overlap = persona_words.intersection(sec_words)
            scores.append(len(overlap) / len(persona_words))
    return scores


def compute_actionability(sections: List[Dict[str, object]]) -> List[float]:
    """Estimate the actionability of each section based on action verbs.

    The score is the ratio of action verbs to total words in the section.  Only
    exact, lower‑cased matches from the ACTION_VERBS set are counted.

    Args:
        sections: List of section dictionaries with a ``text`` field.

    Returns:
        A list of scores in [0, 1].
    """
    scores: List[float] = []
    for sec in sections:
        words = _clean_text(sec.get("text", "")).split()
        if not words:
            scores.append(0.0)
            continue
        action_count = sum(1 for w in words if w in ACTION_VERBS)
        scores.append(action_count / len(words))
    return scores


def compute_cross_document_importance(sections: List[Dict[str, object]]) -> List[float]:
    """Compute a cross‑document importance score based on repeated section titles.

    Sections with titles that occur in multiple documents are given a higher
    score.  The score for each section is normalised by the maximum frequency
    observed among titles.

    Args:
        sections: List of section dictionaries with ``section_title`` and ``document`` fields.

    Returns:
        A list of scores in [0, 1].
    """
    # Count occurrences of each title across documents
    title_counts: Dict[str, set] = {}
    for sec in sections:
        title = sec.get("section_title", "")
        doc = sec.get("document", "")
        title_counts.setdefault(title, set()).add(doc)
    freq_map = {title: len(docs) for title, docs in title_counts.items()}
    max_freq = max(freq_map.values()) if freq_map else 1
    scores: List[float] = []
    for sec in sections:
        title = sec.get("section_title", "")
        freq = freq_map.get(title, 1)
        scores.append(freq / max_freq)
    return scores


def compute_relevance_scores(
    sections: List[Dict[str, object]],
    persona: Dict[str, str],
    job: Dict[str, str],
) -> List[float]:
    """Compute the overall relevance score for each section.

    Args:
        sections: List of section dictionaries.
        persona: Dictionary with at least a ``role`` key and optionally a ``description``.
        job: Dictionary with a ``task`` key describing the job to be done.

    Returns:
        A list of final scores in [0, 1].
    """
    # Construct query from persona and job
    persona_role = persona.get("role", "")
    persona_desc = persona.get("description", "")
    job_task = job.get("task", "")
    query = f"{persona_role} {persona_desc} {job_task}".strip()
    # Compute individual components
    semantic = compute_semantic_similarity(sections, query)
    persona_match_scores = compute_persona_match(sections, persona_role + " " + persona_desc)
    actionability_scores = compute_actionability(sections)
    cross_doc_scores = compute_cross_document_importance(sections)
    # Normalise each component to [0, 1]
    def normalise(arr: List[float]) -> List[float]:
        if not arr:
            return arr
        max_val = max(arr)
        min_val = min(arr)
        if max_val == min_val:
            return [0.0 for _ in arr]
        return [(x - min_val) / (max_val - min_val) for x in arr]

    sem_norm = normalise(semantic)
    pers_norm = normalise(persona_match_scores)
    act_norm = normalise(actionability_scores)
    cross_norm = normalise(cross_doc_scores)
    # Weighted sum
    scores: List[float] = []
    for i in range(len(sections)):
        score = (
            WEIGHT_SEMANTIC * sem_norm[i]
            + WEIGHT_PERSONA * pers_norm[i]
            + WEIGHT_ACTION * act_norm[i]
            + WEIGHT_CROSS_DOC * cross_norm[i]
        )
        scores.append(score)
    return scores


__all__ = [
    "compute_semantic_similarity",
    "compute_persona_match",
    "compute_actionability",
    "compute_cross_document_importance",
    "compute_relevance_scores",
]