# Audio Transcription Agent (audio_transcription_agent.py)

## Brief Description
The Listener Agent. Use this to transcribe audio or video files into text.

## Prerequisites
1. **External API Keys**: Keys for specialized vision or audio models (e.g. OpenAI, Anthropic).
2. **Local Packages**: Tesseract or ffmpeg.

## Step-by-Step Setup Guide
1. Install system dependencies if using local processing: `brew install tesseract ffmpeg`.
2. If using cloud APIs, export your keys: `export OPENAI_API_KEY="sk-..."`.

## How to Update
- The code for this agent lives in `agents/audio_transcription_agent.py`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
