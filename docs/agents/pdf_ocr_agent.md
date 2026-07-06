# Pdf Ocr Agent (pdf_ocr_agent.py)

## Brief Description
The Archivist Agent for Documents. Use this to extract text from PDFs or run OCR on scanned documents.

## Prerequisites
1. **External API Keys**: Keys for specialized vision or audio models (e.g. OpenAI, Anthropic).
2. **Local Packages**: Tesseract or ffmpeg.

## Step-by-Step Setup Guide
1. Install system dependencies if using local processing: `brew install tesseract ffmpeg`.
2. If using cloud APIs, export your keys: `export OPENAI_API_KEY="sk-..."`.

## How to Update
- The code for this agent lives in `agents/pdf_ocr_agent.py`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
