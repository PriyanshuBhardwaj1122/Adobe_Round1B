"""Automatic persona detection and document processing.

This module provides a high‑level interface for processing a directory of PDFs
without requiring a pre‑constructed input JSON.  It performs basic persona
detection on the extracted text, constructs persona and job descriptors
accordingly, ranks sections using the existing ranking logic and writes the
results as JSON files.  The goal is to allow end‑to‑end processing of a folder
of PDFs with minimal manual configuration.

The persona detection implemented here uses simple keyword heuristics.  If a
document contains words like ``research`` or ``student`` in the text then a
corresponding persona role and job task are assigned.  Users can extend
``detect_persona_and_job`` to implement more sophisticated logic or integrate
their own models.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Tuple, List

# Ensure local imports work when executed outside of a package context
import sys as _sys
import os as _os
_current_dir = _os.path.dirname(_os.path.abspath(__file__))
if _current_dir not in _sys.path:
    _sys.path.insert(0, _current_dir)

from pdf_processor import parse_pdf  # type: ignore
from persona_matcher import rank_sections  # type: ignore
from document_intelligence import refine_subsections  # type: ignore


def detect_persona_and_job(full_text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Infer a persona and job description from raw text.

    This function uses simple keyword‑matching heuristics to guess the
    appropriate persona role and job task.  It looks for words such as
    ``research``, ``student`` and ``analyst``.  If none of these match, a
    default persona of ``Reader`` with a generic summarisation task is
    returned.

    Args:
        full_text: Concatenated text of all sections extracted from a PDF.

    Returns:
        A tuple containing the persona dictionary (with a ``role`` key) and
        the job dictionary (with a ``task`` key).
    """
    lower = full_text.lower()
    # Default values
    role = "Reader"
    task = "Summarise the key sections of the document"
    # Heuristic checks for more specific roles and tasks
    if "research" in lower or "literature" in lower:
        role = "Researcher"
        task = "Prepare a literature review of the document’s contributions"
    elif "student" in lower or "exam" in lower or "undergraduate" in lower:
        role = "Student"
        task = "Identify and study the key concepts for exam preparation"
    elif "analysis" in lower or "analyst" in lower or "financial" in lower:
        role = "Business Analyst"
        task = "Extract insights and analyse trends from the document"
    elif "patient" in lower or "medical" in lower or "nursing" in lower:
        role = "Healthcare Professional"
        task = "Summarise clinical information relevant to patient care"
    return {"role": role}, {"task": task}


def process_pdf(pdf_path: str, output_dir: str) -> None:
    """Process a single PDF file and write an output JSON.

    The function parses the PDF into sections, detects the persona and job
    descriptors, ranks the sections based on relevance, refines the top
    sections and writes a JSON summary to ``output_dir``.  The output file
    name is derived from the PDF’s base name with ``_output.json`` appended.

    Args:
        pdf_path: Absolute path to the PDF file.
        output_dir: Directory where the output JSON should be written.
    """
    # Extract sections and assign document names
    sections = parse_pdf(pdf_path)
    # Combine all text to detect persona and job
    full_text = " ".join([sec.get("text", "") for sec in sections])
    persona, job = detect_persona_and_job(full_text)
    # Annotate each section with the document name
    base_name = os.path.basename(pdf_path)
    for sec in sections:
        sec["document"] = base_name
    # Rank sections and select top 5
    ranked = rank_sections(sections, persona, job)
    top_n = min(5, len(ranked))
    top_sections = ranked[:top_n]
    # Prepare extracted sections output
    extracted = [
        {
            "document": sec.get("document"),
            "section_title": sec.get("section_title"),
            "importance_rank": sec.get("importance_rank"),
            "page_number": sec.get("page_number"),
        }
        for sec in top_sections
    ]
    # Refine sub‑sections using existing logic
    refined = refine_subsections(top_sections, persona, job, top_n=top_n)
    # Build metadata
    metadata = {
        "input_documents": [base_name],
        "persona": persona.get("role", ""),
        "job_to_be_done": job.get("task", ""),
        "processing_timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
    }
    output_data = {
        "metadata": metadata,
        "extracted_sections": extracted,
        "subsection_analysis": refined,
    }
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    # Determine output file name
    output_filename = os.path.splitext(base_name)[0] + "_output.json"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        import json
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"Processed {pdf_path} -> {output_path}")


def process_directory(pdf_dir: str, output_dir: str) -> None:
    """Process all PDFs in a directory.

    Iterates over every file in ``pdf_dir`` with a ``.pdf`` extension and
    processes each via ``process_pdf``.  Non‑PDF files are ignored.  Output
    JSON files are written to ``output_dir``.

    Args:
        pdf_dir: Directory containing PDF files.
        output_dir: Target directory for JSON summaries.
    """
    for entry in os.listdir(pdf_dir):
        if entry.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, entry)
            try:
                process_pdf(pdf_path, output_dir)
            except Exception as exc:
                print(f"Error processing {pdf_path}: {exc}")


if __name__ == "__main__":
    # If executed as a script, process PDFs from the directory specified by
    # the ``PDF_DIR`` environment variable or default to "/app/input".  Output
    # will be written to ``/app/output``.
    pdf_dir = os.environ.get("PDF_DIR", "/app/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/app/output")
    process_directory(pdf_dir, output_dir)