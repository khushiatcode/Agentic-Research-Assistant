# Agentic Research Assistant

An autonomous AI research assistant that leverages multiple tools including web search, Wikipedia, and advanced reasoning capabilities for comprehensive research and analysis.

## Setup

1. Clone the repository
```bash
git clone https://github.com/khushiatcode/Agentic-Research-Assistant.git
cd Agentic-Research-Assistant
```

2. Create a virtual environment and install dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your API keys:
```bash
# Create .env file
touch .env  # On Windows use: type nul > .env

# Add your API keys to .env file:
DEEPSEEK_API_KEY=your_api_key_here
WEATHER_API_KEY=your_weather_api_key_here
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_google_cse_id_here
```

4. Run the application
```bash
python main.py
```

## Features

- Advanced AI-powered research capabilities
- Web search integration
- Weather information lookup
- News aggregation
- Natural language processing
- Comprehensive documentation analysis

## Security Note

This project uses environment variables for API keys and sensitive information. Never commit your `.env` file or expose your API keys in the code.

## Running Locally

Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```