"""PDF processing utilities.

This module wraps Poppler command‑line tools (``pdfinfo`` and ``pdftotext``)
to extract text from PDF files without internet access.  It uses simple
heuristics to detect headings and group subsequent lines into sections.  Each
section contains a title, the concatenated text and the page number on which
the section begins.

The heuristics are intentionally lightweight to satisfy performance
constraints; they may not perfectly match the hierarchy of every document but
provide a reasonable approximation for most text‑heavy PDFs.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import List, Dict, Tuple


def _run_pdfinfo(filepath: str) -> int:
    """Return the number of pages in the PDF via the ``pdfinfo`` command.

    Args:
        filepath: Path to the PDF file.

    Returns:
        The total number of pages.

    Raises:
        RuntimeError: If the command fails or page count cannot be parsed.
    """
    try:
        result = subprocess.run(
            ["pdfinfo", filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        for line in result.stdout.decode("utf-8", errors="ignore").splitlines():
            if line.lower().startswith("pages"):
                # Format: "Pages:           10"
                parts = line.split(":")
                if len(parts) > 1:
                    count_str = parts[1].strip()
                    try:
                        return int(count_str)
                    except ValueError:
                        continue
        raise RuntimeError(f"Could not determine page count for {filepath}")
    except Exception as exc:
        raise RuntimeError(f"pdfinfo failed for {filepath}: {exc}") from exc


def _run_pdftotext_page(filepath: str, page_num: int) -> str:
    """Extract text from a single page of a PDF using ``pdftotext``.

    Args:
        filepath: Path to the PDF file.
        page_num: 1‑based page number to extract.

    Returns:
        A string containing the plain text of the page.

    Raises:
        RuntimeError: If the command fails.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-f", str(page_num), "-l", str(page_num), filepath, "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return result.stdout.decode("utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"pdftotext failed on page {page_num} of {filepath}: {exc}") from exc


def _is_heading(line: str) -> bool:
    """Determine whether a line of text appears to be a heading.

    The heuristic checks for short, title‑like phrases: lines shorter than
    100 characters and fewer than 15 words, where the majority of words start
    with an uppercase letter or digit, or the entire line is uppercase.  Lines
    that begin with enumeration patterns (e.g. ``"1."`` or ``"2.1"``) are also
    considered headings.

    Args:
        line: The text line to evaluate.

    Returns:
        True if the line is likely a heading, False otherwise.
    """
    text = line.strip()
    if not text:
        return False
    # Exclude very long lines
    if len(text) > 100:
        return False
    words = text.split()
    if len(words) > 15:
        return False
    # Check enumeration patterns (e.g. "1.", "2.3", "A.")
    if re.match(r"^(\d+\.\d*|\d+|[A-Z])\.\s", text):
        return True
    # Count words starting with uppercase or digits
    cap_count = sum(1 for w in words if w and (w[0].isupper() or w[0].isdigit()))
    if cap_count / len(words) >= 0.6:
        return True
    # All uppercase (ignore numbers)
    letters_only = re.sub(r"[^A-Za-z]", "", text)
    if letters_only and letters_only.isupper():
        return True
    return False


def parse_pdf(filepath: str) -> List[Dict[str, object]]:
    """Parse a PDF into a list of sections.

    Each section contains a title (heading) and the associated body text.  The
    function iterates through each page, extracts text with ``pdftotext`` and
    applies a simple heading detection heuristic.  Consecutive lines after a
    heading are grouped until the next heading or end of page.

    Args:
        filepath: Path to the PDF file.

    Returns:
        A list of dictionaries, each with keys ``section_title``, ``text`` and
        ``page_number``.
    """
    if not os.path.exists(filepath) or not filepath.lower().endswith(".pdf"):
        raise ValueError(f"Invalid PDF path: {filepath}")
    num_pages = _run_pdfinfo(filepath)
    sections: List[Dict[str, object]] = []
    for page_num in range(1, num_pages + 1):
        try:
            page_text = _run_pdftotext_page(filepath, page_num)
        except RuntimeError:
            # If extraction fails for a page, skip it
            continue
        lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
        current_title = None
        current_lines: List[str] = []
        for line in lines:
            if _is_heading(line):
                # Flush previous section
                if current_title is not None:
                    sections.append(
                        {
                            "section_title": current_title,
                            "text": " ".join(current_lines).strip(),
                            "page_number": page_num,
                        }
                    )
                current_title = line
                current_lines = []
            else:
                current_lines.append(line)
        # Flush remainder of page
        if current_title is not None and current_lines:
            sections.append(
                {
                    "section_title": current_title,
                    "text": " ".join(current_lines).strip(),
                    "page_number": page_num,
                }
            )
        elif current_title is None and lines:
            # No headings detected on this page – treat whole page as a section
            sections.append(
                {
                    "section_title": f"Page {page_num}",
                    "text": " ".join(lines).strip(),
                    "page_number": page_num,
                }
            )
    return sections


__all__ = ["parse_pdf"]