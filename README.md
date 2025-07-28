Here’s a more natural, human-friendly rewrite of your project README in Markdown — ready to paste into your README.md file:

⸻

 Adobe Hackathon Round 1B – Persona-Driven Document Intelligence

 Overview

This project is a reference solution for Round 1B of Adobe’s Connecting the Dots Hackathon. The goal? Turn a set of related PDFs into a personalised knowledge base.

Given:
	•	A persona (who the user is), and
	•	A job to be done (what they’re trying to achieve),

…the system scans all PDFs, finds the most relevant sections, ranks them by importance, and extracts concise summaries of the best content.

It works offline, uses only CPU, and is built to comply with strict runtime and memory limits.

⸻

 System Architecture

The project follows a clean, modular design with components that are easy to test and extend. Here’s a quick breakdown:

1.  PDF Processing (src/pdf_processor.py)
	•	Uses the command-line tool pdftotext to convert each page to raw text.
	•	Detects headings using simple rules: short, title-cased lines or enumerated items.
	•	Groups following paragraphs under each heading and captures metadata like section title and page number.

2.  Content Analysis (src/content_analyzer.py)
	•	Builds TF-IDF vectors for all sections and for a combined query made from the persona + task.
	•	Computes:
	•	Cosine similarity
	•	Persona term overlap
	•	Actionability score (based on verbs like “build”, “design”, etc.)
	•	Cross-document heading frequency
	•	Combines all into a single relevance score per section.

3.  Persona Matching (src/persona_matcher.py)
	•	Takes in all section scores and produces a ranked list with an importance_rank field.

4. Multi-Document Intelligence (src/document_intelligence.py)
	•	From the top sections, extracts the most relevant sentences using word overlap with the persona and task — producing clean, targeted subsection summaries.

5.  Entrypoint (src/main.py)
	•	Orchestrates everything:
	•	Loads input from /app/input
	•	Runs the full processing pipeline
	•	Outputs a JSON result to /app/output, including timestamps and metadata.

Setup & Execution

Everything runs inside a Docker container, fully offline, and works on AMD64 architecture.

Build the container:

docker build --platform linux/amd64 -t persona-intelligence:latest ./adobe-hackathon-round1b

 Run the container:

docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  persona-intelligence:latest

	•	Place your input JSON and associated PDFs in the input/ folder.
	•	Processed output will appear in the output/ folder.
Input Format

Each input JSON file should follow this structure:

{
  "challenge_info": {
    "challenge_id": "your_id_here",
    "test_case_name": "test1",
    "description": "Task description"
  },
  "documents": [
    {"filename": "doc1.pdf", "title": "Title A"},
    {"filename": "doc2.pdf", "title": "Title B"}
  ],
  "persona": {
    "role": "Data Scientist",
    "description": "Works on machine learning models"
  },
  "job_to_be_done": {
    "task": "Evaluate scalable model serving solutions"
  }
}
Output Format

Here’s what you’ll get in the result:

{
  "metadata": {
    "input_documents": ["doc1.pdf", "doc2.pdf"],
    "persona": "Data Scientist",
    "job_to_be_done": "Evaluate scalable model serving solutions",
    "processing_timestamp": "2025-07-18T15:34:56.502"
  },
  "extracted_sections": [
    {
      "document": "doc1.pdf",
      "section_title": "Serving Infrastructure Overview",
      "importance_rank": 1,
      "page_number": 5
    },
    ...
  ],
  "subsection_analysis": [
    {
      "document": "doc1.pdf",
      "refined_text": "This section discusses scalable container-based serving using Kubernetes and gRPC.",
      "page_number": 5
    },
    ...
  ]
}
 Performance & Constraints

This solution was engineered to run fully offline and efficiently on CPU:
	•	Lightweight, plain-text processing using pdftotext
	•	Custom TF-IDF implementation (no heavy ML libraries)
	•	No internet, no GPUs, no frills
	•	Fast enough to process documents well within the time and memory limits
# Adobe_1b
