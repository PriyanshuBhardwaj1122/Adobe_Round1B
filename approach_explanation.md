# Approach Explanation – Adobe Hackathon Round 1B

This project tackles the challenge of building a persona‑driven document intelligence system that extracts and prioritizes the most relevant content from a collection of PDFs — based on a user’s persona (their role) and a job‑to‑be‑done (their goal). The key constraint? The entire solution must run offline, use only CPU, stay under 1 GB in size, and process everything in under 60 seconds.


## PDF Processing

We start by converting each PDF to plain text using pdftotext from the Poppler suite. This tool is fast, reliable, and works well in constrained environments without requiring internet access.

 How we detect sections:
•	For each page, we scan the lines and treat short,     well-formatted lines as potential headings:
•	Lines under 100 characters and 15 words.
•	Title‑cased or UPPERCASE text.
•	Or lines that start with enumeration (like 1. or 2.1).
•	Once a heading is found, we group the following lines as that section’s content.
•	If no headings are found on a page, we treat the whole page as a section called "Page N".

This approach is intentionally simple and robust, letting us handle diverse document layouts without relying on fonts or visual styles. It’s fast and works surprisingly well.

## Content Analysis & Relevance Scoring

Once sections are extracted, we score each one based on how relevant it is to the persona and the job they’re trying to do. We use a multi-factor scoring system:

1. Semantic Similarity (40%)

We build TF-IDF vectors for each section and compare them to a query vector made from the persona + job description. This gives us a core similarity score.

2. Persona Match (25%)

We check how many keywords from the persona’s role appear in the section — boosting content that clearly matches their expertise.

3. Actionability (20%)

We reward sections that contain action verbs like “design”, “implement”, “analyse”, etc. These are the parts of the document that sound doable and useful.

4. Cross-Document Importance (15%)

If a heading shows up in multiple documents (like “Conclusion” or “Architecture”), we give it a small bonus — assuming repeated ideas are more likely to be important.

All four scores are combined into a single relevance score. Sections are then sorted and ranked accordingly.

## Sub‑Section Refinement & Synthesis

From the top-ranked sections, we extract just the most useful sentences. We split each section into sentences and select the ones that best match the persona/job context — based on word overlap.

It’s a lightweight, extractive summarization method that works well without needing a large language model. 


## Performance & Constraint Handling

This system is built from the ground up to be resource-efficient:
	•	All processing is offline and CPU-only.
	•	We use plain-text processing and sparse vectors to minimize memory.
	•	No network access or cloud APIs.
	•	Total runtime and memory usage stay well within the limits