"""Entrypoint for the persona‑driven document intelligence system.

This script reads input JSON files from the ``/app/input`` directory, parses
the referenced PDFs, ranks sections based on persona and job information, and
writes a result JSON file into the ``/app/output`` directory.  It is intended
to be run inside the Docker container specified in the project.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Dict, List

# When the script is executed directly (without using -m), the package context
# may not be set, leading to relative import failures.  Append the directory
# containing this file to sys.path so that modules can be imported as top‑level.
if __package__ is None or __package__ == "":
    import os as _os, sys as _sys
    _current_dir = _os.path.dirname(_os.path.abspath(__file__))
    if _current_dir not in _sys.path:
        _sys.path.insert(0, _current_dir)

from pdf_processor import parse_pdf  # type: ignore
from persona_matcher import rank_sections  # type: ignore
from document_intelligence import refine_subsections  # type: ignore

# Optional automatic persona detection.  If persona and job information
# are missing from the input JSON, we attempt to infer them from the
# document text using simple heuristics.  The function is imported on
# demand to avoid circular dependencies when this module is used on its
# own.  See ``auto_processor.detect_persona_and_job`` for details.
try:
    from auto_processor import detect_persona_and_job  # type: ignore
except Exception:
    detect_persona_and_job = None  # type: ignore


def process_input_file(input_path: str, input_dir: str, output_dir: str) -> None:
    """Process a single input JSON and write an output JSON.

    Args:
        input_path: Absolute path to the input JSON file.
        input_dir: Directory containing the input file and referenced PDFs.
        output_dir: Directory where the output JSON should be written.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        try:
            input_data = json.load(f)
        except json.JSONDecodeError as exc:
            print(f"Skipping {input_path}: invalid JSON ({exc})", file=sys.stderr)
            return
    # Extract persona and job descriptors
    persona: Dict[str, str] = input_data.get("persona", {}) or {}
    job: Dict[str, str] = input_data.get("job_to_be_done", {}) or {}
    docs_info: List[Dict[str, str]] = input_data.get("documents", []) or []
    if not docs_info:
        print(f"Skipping {input_path}: no documents specified", file=sys.stderr)
        return
    all_sections: List[Dict[str, object]] = []
    # Parse each PDF and accumulate sections
    # Also accumulate raw text for persona detection if needed
    concatenated_text: List[str] = []
    for doc in docs_info:
        filename = doc.get("filename")
        if not filename:
            continue
        pdf_path = os.path.join(input_dir, filename)
        try:
            sections = parse_pdf(pdf_path)
        except Exception as exc:
            print(f"Error processing {pdf_path}: {exc}", file=sys.stderr)
            continue
        # Append text for persona detection
        for sec in sections:
            concatenated_text.append(str(sec.get("text", "")))
            # Annotate each section with its originating document
            sec_copy = sec.copy()
            sec_copy["document"] = filename
            all_sections.append(sec_copy)
    if not all_sections:
        print(f"No sections extracted from documents in {input_path}", file=sys.stderr)
        return
    # If persona or job descriptors are missing, attempt automatic detection
    if (not persona.get("role") or not job.get("task")) and detect_persona_and_job:
        try:
            full_text = " ".join(concatenated_text)
            detected_persona, detected_job = detect_persona_and_job(full_text)
            # Only fill missing fields
            if not persona.get("role"):
                persona.update(detected_persona)
            if not job.get("task"):
                job.update(detected_job)
        except Exception:
            pass  # Silently ignore detection failures
    # Rank sections
    ranked = rank_sections(all_sections, persona, job)
    # Determine the number of top sections to include – at most 5
    top_n = min(5, len(ranked))
    top_sections = ranked[:top_n]
    # Prepare extracted sections output (without internal score)
    extracted = [
        {
            "document": sec.get("document"),
            "section_title": sec.get("section_title"),
            "importance_rank": sec.get("importance_rank"),
            "page_number": sec.get("page_number"),
        }
        for sec in top_sections
    ]
    # Refine sub‑sections
    refined = refine_subsections(top_sections, persona, job, top_n=top_n)
    # Metadata
    metadata = {
        "input_documents": [doc.get("filename") for doc in docs_info],
        "persona": persona.get("role", ""),
        "job_to_be_done": job.get("task", ""),
        "processing_timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
    }
    output_data = {
        "metadata": metadata,
        "extracted_sections": extracted,
        "subsection_analysis": refined,
    }
    # Determine output file name (e.g. input.json -> input_output.json)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_filename = f"{base_name}_output.json"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(output_data, out_f, ensure_ascii=False, indent=2)
    print(f"Processed {input_path} -> {output_path}")


def main() -> None:
    """Main entrypoint for CLI execution."""
    # Input and output directories default to /app/input and /app/output
    #input_dir = os.environ.get("INPUT_DIR", "/app/input")
    #output_dir = os.environ.get("OUTPUT_DIR", "/app/output")
    input_dir = "../input_pdfs"
    output_dir = "../output"
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    # Process each JSON file
    for entry in os.listdir(input_dir):
        if entry.lower().endswith(".json"):
            input_path = os.path.join(input_dir, entry)
            try:
                process_input_file(input_path, input_dir, output_dir)
            except Exception as exc:
                print(f"Error processing {input_path}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()