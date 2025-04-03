# AI Research Assistant

An advanced AI-powered research assistant that combines multiple information sources and specialized tools to answer complex research questions.

## Features

- Comprehensive web search with intelligent rate limiting
- Wikipedia integration
- News and Reddit data retrieval
- Advanced analysis tools for complex queries
- Automatic research report generation
- Clean, user-friendly Streamlit interface

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd ai-research-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
DEEPSEEK_API_KEY=your_api_key_here
```

## Running Locally

Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

## Deployment

The app can be deployed on:
- Streamlit Cloud
- Hugging Face Spaces
- Railway.app
- Render.com

See deployment instructions in the documentation.

## Usage

1. Enter your DeepSeek API key in the sidebar
2. Type your research query in the text area
3. Click "Start Research"
4. View results and download reports

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License 