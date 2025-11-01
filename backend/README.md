# Backend Setup

## Installation
1. Create a virtual environment: `python -m venv venv`
2. Activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`

## Configuration
1. Get an OpenAI API key from https://platform.openai.com/
2. Replace `your_openai_api_key_here` in `.env` with your actual API key

## Running the Server
```bash
python app.py