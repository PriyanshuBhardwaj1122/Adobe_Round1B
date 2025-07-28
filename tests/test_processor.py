"""Unit tests for the PDF processor."""

import os
import unittest
from pathlib import Path
import sys

# Add the src directory to sys.path so that modules can be imported directly
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pdf_processor import parse_pdf  # type: ignore


class TestPDFProcessor(unittest.TestCase):
    def setUp(self) -> None:
        # Use the sample challenge document placed in the repository for testing
        self.sample_pdf = Path(__file__).resolve().parent.parent / "6874faecd848a_Adobe_India_Hackathon_-_Challenge_Doc.pdf"
        if not self.sample_pdf.exists():
            self.skipTest("Sample PDF not available")

    def test_parse_pdf_returns_sections(self):
        sections = parse_pdf(str(self.sample_pdf))
        # Ensure we extracted at least one section
        self.assertTrue(len(sections) > 0)
        # Check keys in first section
        first = sections[0]
        self.assertIn("section_title", first)
        self.assertIn("text", first)
        self.assertIn("page_number", first)
        # Ensure page_number is integer and >= 1
        self.assertIsInstance(first["page_number"], int)
        self.assertGreaterEqual(first["page_number"], 1)


if __name__ == "__main__":
    unittest.main()