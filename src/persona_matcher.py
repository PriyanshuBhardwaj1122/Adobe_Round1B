"""Persona‑based ranking of document sections.

This module exposes a function that takes extracted sections along with persona
and job descriptors and returns the sections sorted by descending relevance.
Each section is annotated with an ``importance_rank`` field starting at 1.
"""

from __future__ import annotations

from typing import List, Dict
# When executed without package context, modify sys.path so local modules are importable.
if __package__ is None or __package__ == "":
    import os as _os, sys as _sys
    _current_dir = _os.path.dirname(_os.path.abspath(__file__))
    if _current_dir not in _sys.path:
        _sys.path.insert(0, _current_dir)

from content_analyzer import compute_relevance_scores  # type: ignore


def rank_sections(
    sections: List[Dict[str, object]],
    persona: Dict[str, str],
    job: Dict[str, str],
) -> List[Dict[str, object]]:
    """Rank sections based on persona and job relevance.

    Args:
        sections: List of section dictionaries.  Each must contain at least
            ``section_title``, ``text``, ``page_number`` and ``document`` keys.
        persona: Persona definition with ``role`` and optional ``description``.
        job: Job‑to‑be‑done definition with ``task``.

    Returns:
        A new list of sections sorted by descending relevance score.  Each
        dictionary includes an added ``importance_rank`` key.
    """
    if not sections:
        return []
    scores = compute_relevance_scores(sections, persona, job)
    # Pair each section with its score
    paired = list(zip(sections, scores))
    # Sort by score descending; stable sort ensures original order for ties
    paired.sort(key=lambda x: x[1], reverse=True)
    ranked_sections = []
    for idx, (section, score) in enumerate(paired, start=1):
        sec_copy = section.copy()
        sec_copy["importance_rank"] = idx
        sec_copy["_score"] = float(score)
        ranked_sections.append(sec_copy)
    return ranked_sections


__all__ = ["rank_sections"]