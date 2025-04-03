from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import os
import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools import (
    search_tool, 
    wiki_tool, 
    save_tool, 
    scrape_tool, 
    math_tool, 
    weather_tool, 
    news_tool,
    reddit_tool
)
# Import MCP tools
from mcp_tools import mcp_tools
import re
import json
import time
from time import sleep
import sys

# Check if running in Cursor environment
def is_cursor_environment():
    """Check if we're running in the Cursor environment."""
    # Check for Cursor-specific functions in globals
    cursor_functions = [
        "mcp_firecrawl_firecrawl_scrape",
        "mcp_firecrawl_firecrawl_search",
        "mcp_server_sequential_thinking_sequentialthinking"
    ]
    
    # Check if any of the Cursor functions are in globals
    for func_name in cursor_functions:
        if func_name in globals():
            return True
    
    return False

# Print warning if not in Cursor
cursor_detected = is_cursor_environment()
if not cursor_detected:
    print("\n" + "!" * 80)
    print("WARNING: Not running in Cursor environment!")
    print("Advanced tools like SequentialThinking and AdvancedWebSearch will use fallbacks.")
    print("For full functionality, run this script in Cursor using:")
    print("  1. /run main.py (in Cursor chat)")
    print("  2. %cursor run main.py (in Jupyter notebook)")
    print("!" * 80 + "\n")
else:
    print("\n" + "=" * 80)
    print("Cursor environment detected - all advanced tools will be available!")
    print("=" * 80 + "\n")

# Functions to save both raw and formatted outputs to text files
def save_formatted_response_to_file(response, filename):
    """Save a nicely formatted version of the structured response to a file."""
    try:
        # Format the research report
        formatted_output = format_research_report(response)
        
        # Save to the timestamped file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(formatted_output)
        print(f"Formatted response saved to: {filename}")
        
        # Also append to the fixed output.txt file
        with open("output.txt", 'a', encoding='utf-8') as f:
            f.write("\n\n" + "="*80 + "\n")
            f.write(f"RESEARCH SESSION: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            f.write(formatted_output)
            f.write("\n\n" + "-"*80 + "\n\n")
        print(f"Research also appended to: output.txt")
        
        return True
    except Exception as e:
        print(f"Error saving formatted response: {e}")
        return False

def format_research_report(response):
    """Format a research response into a well-structured report."""
    output = []
    output.append(f"=== RESEARCH REPORT ===\n")
    output.append(f"TOPIC: {response.topic}\n")
    output.append(f"{'-' * 80}\n\n")
    
    output.append(f"SUMMARY:\n{response.summary}\n\n")
    
    output.append(f"KEY FINDINGS:\n")
    for i, finding in enumerate(response.key_findings, 1):
        output.append(f"{i}. {finding}\n")
    output.append(f"\n")
    
    output.append(f"ANALYSIS:\n{response.analysis}\n\n")
    
    output.append(f"CONCLUSIONS:\n{response.conclusions}\n\n")
    
    if response.limitations:
        output.append(f"LIMITATIONS:\n{response.limitations}\n\n")
    
    output.append(f"SOURCES:\n")
    for i, source in enumerate(response.sources, 1):
        output.append(f"{i}. {source}\n")
    output.append(f"\n")
    
    output.append(f"TOOLS USED:\n")
    for i, tool in enumerate(response.tools_used, 1):
        output.append(f"{i}. {tool}\n")
    output.append(f"\n")
    
    if response.follow_up_questions:
        output.append(f"FOLLOW-UP QUESTIONS:\n")
        for i, question in enumerate(response.follow_up_questions, 1):
            output.append(f"{i}. {question}\n")
    
    return "".join(output)

def save_raw_response_to_file(response, filename):
    """Save the raw response to a file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(str(response))
        print(f"Raw response saved to: {filename}")
        
        # Also append the raw full response to a single file
        with open("full_research_log.txt", 'a', encoding='utf-8') as f:
            f.write("\n\n" + "="*80 + "\n")
            f.write(f"RESEARCH SESSION: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            # If this is a dictionary with an output key, extract the full text
            if isinstance(response, dict) and 'output' in response:
                f.write(str(response['output']))
            else:
                f.write(str(response))
            f.write("\n\n" + "-"*80 + "\n\n")
        print(f"Full research log also appended to: full_research_log.txt")
        
        return True
    except Exception as e:
        print(f"Error saving raw response: {e}")
        return False

def cleanup_output(output_text):
    """Clean up and extract valid JSON from model output."""
    if not output_text:
        return None
    
    # Remove any trailing incomplete words or fragments (like "DOIs")
    output_text = re.sub(r'\b\w+$', '', output_text).strip()
    
    # Try to find JSON-like content (with relaxed matching)
    # First, try to find content inside triple backticks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output_text)
    if json_match:
        potential_json = json_match.group(1).strip()
    else:
        # If no triple backticks, look for content that looks like JSON object
        json_pattern = r'(\{[\s\S]*\})'
        json_match = re.search(json_pattern, output_text)
        potential_json = json_match.group(1) if json_match else output_text
    
    # Try to parse it as JSON
    try:
        parsed_json = json.loads(potential_json)
        return parsed_json
    except json.JSONDecodeError:
        # If direct parsing fails, try more aggressive cleaning
        try:
            # Remove any non-JSON content and fix common issues
            cleaned = re.sub(r'(\w+):', r'"\1":', potential_json)  # Convert keys without quotes
            cleaned = re.sub(r'\'', r'"', cleaned)  # Replace single quotes with double quotes
            cleaned = re.sub(r',\s*\}', r'}', cleaned)  # Remove trailing commas
            cleaned = re.sub(r',\s*$', '', cleaned)  # Remove trailing commas at the end of lines
            
            # Ensure it's properly terminated
            if not cleaned.strip().endswith('}'):
                cleaned = cleaned.strip() + '}'
                
            return json.loads(cleaned)
        except:
            return None

def create_fallback_response(query, output_text):
    """Create a fallback response when parsing fails completely."""
    # Try to extract some useful content from the raw output
    truncated_output = output_text[:1000] + "..." if len(output_text) > 1000 else output_text
    
    # See if we can identify tools that were used
    tools_used = ["Error recovery"]
    tool_pattern = r"Invoking: `(.*?)`"
    tool_matches = re.findall(tool_pattern, output_text)
    if tool_matches:
        tools_used = list(set(tool_matches))  # Remove duplicates
    
    # Try to extract sources if any
    sources = []
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    url_matches = re.findall(url_pattern, output_text)
    if url_matches:
        sources = list(set(url_matches))[:5]  # Take up to 5 unique URLs
    
    return ResearchResponse(
        topic=query,
        summary=f"The research assistant collected information but couldn't format it properly. Here's what was found:\n\n{truncated_output[:300]}...",
        key_findings=["Information was gathered but could not be properly structured"],
        analysis="The assistant searched for information on the topic, but the response format was not compatible with the expected structure.",
        conclusions="The information is available in the raw response file for manual review.",
        sources=sources,
        tools_used=tools_used,
        limitations="Response could not be parsed into the expected format.",
        follow_up_questions=["Could you ask a more specific question?", 
                             "Would you like to focus on a particular aspect of this topic?"]
    )

def retry_with_simplified_query(query, llm):
    """Try a direct approach with the LLM to get a properly formatted response."""
    try:
        # Create a simpler prompt that focuses just on getting valid JSON
        retry_prompt = f"""
You need to provide information about the following query in a valid JSON format:

QUERY: {query}

You MUST format your response as a valid JSON object with these fields:
- topic: The main topic of research
- summary: A concise summary of your findings (1-2 paragraphs)
- key_findings: A list of 3-5 key points as strings
- analysis: A short analysis of the topic (1-2 paragraphs)
- conclusions: Brief conclusions (1 paragraph)
- sources: A list of sources as strings
- tools_used: A list of tools used as strings
- limitations: Any limitations of your research
- follow_up_questions: A list of 2-3 follow-up questions as strings

IMPORTANT: Only respond with the JSON object, nothing else.
"""
        # Call the model directly
        response = llm.invoke(retry_prompt)
        if response and isinstance(response.content, str):
            # Try to parse the response
            try:
                cleaned = cleanup_output(response.content)
                if cleaned:
                    return ResearchResponse(**cleaned)
            except:
                pass
        return None
    except Exception as e:
        print(f"Error during retry: {e}")
        return None

load_dotenv()  #loads environment variables from .env file


#trial run
# response = llm3.invoke("What are different interpretations of the bhagavad gita?")
# print(response)

#lets make it a bit advanced
#lets make a prompt template


#now we define a simple python class which will specify the type of content we want our LLM to return (output we want to see)
class ResearchResponse(BaseModel):  #research response is the name of the class
    topic: str
    summary: str
    key_findings: list[str]
    analysis: str
    conclusions: str
    sources: list[str]
    tools_used: list[str]
    limitations: str = ""
    follow_up_questions: list[str] = []

#set up the LLM
# llm = ChatOpenAI(model="gpt-4o-mini")
# llm2 = ChatAnthropic(model="claude-3-5-sonnet-20240620")
# Use ChatOpenAI with Open Router base URL for DeepSeek
llm3 = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    model="deepseek/deepseek-chat"  # Reverting to the original model ID
)

# Add post-processing to guide the model's output format
class PostProcessingOutputParser(PydanticOutputParser):
    def __init__(self, pydantic_object):
        super().__init__(pydantic_object=pydantic_object)
    
    def parse(self, text):
        """Override parse to guide the model to correct output format."""
        try:
            # Try standard parsing first
            return super().parse(text)
        except Exception as e:
            # If it fails, try to extract properly formatted JSON
            cleaned_json = cleanup_output(text)
            if cleaned_json:
                return self.pydantic_object(**cleaned_json)
            raise e

#parser allows us to take the output of the LLM and parse it into the model and use it like a python object inside our code
parser = PostProcessingOutputParser(pydantic_object=ResearchResponse)

#now we create a prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", #it is the information that we want to give to the LLM so it knows what to do
            """
            You are an advanced AI research assistant with extensive knowledge and capabilities. 
            
            Your primary goal is to provide accurate, well-researched, and comprehensive answers to user queries.
            You have access to the following tools:
            
            BASIC TOOLS:
            - Search: Search the web for real-time information
            - Wikipedia: Access Wikipedia articles for in-depth knowledge
            - WebScraper: Extract information from specific web pages
            - Calculator: Perform mathematical calculations with precision
            - WeatherInfo: Provide current weather information for locations worldwide
            - NewsSearch: Find the latest news on various topics
            - RedditSearch: Get information and discussions from Reddit
            - SaveResearch: Save your findings to files for future reference
            
            ADVANCED TOOLS (USE THESE FOR COMPREHENSIVE RESEARCH):
            - AdvancedWebScraper: Scrape web pages with sophisticated extraction - USE THIS for detailed content extraction from specific URLs
            - AdvancedWebSearch: Search and extract detailed content from multiple pages - USE THIS for deeper search than basic Search
            - DeepWebCrawler: Crawl websites deeply to gather comprehensive information - USE THIS for exploring entire websites
            - DeepResearch: Conduct comprehensive AI-powered research on complex topics - USE THIS for complex or philosophical topics
            - SequentialThinking: Break down complex problems through step-by-step reasoning - USE THIS for analysis requiring multiple steps
            
            TOOL SELECTION GUIDELINES:
            - For simple factual questions: Use basic Search or Wikipedia
            - For complex analysis questions: ALWAYS use SequentialThinking
            - For deep research on topics with multiple perspectives: USE DeepResearch
            - When you have a specific website: USE AdvancedWebScraper to extract detailed content
            - For topics requiring evaluation of multiple sources: USE AdvancedWebSearch

            IMPORTANT SEARCH GUIDELINES:
            - Be strategic with web searches to avoid rate limiting
            - Make search queries specific and targeted rather than broad
            - Limit the number of search queries for a single question (max 3-4 searches)
            - Prefer Wikipedia for general knowledge before using search
            - If search is rate-limited, use alternative tools like Wikipedia or WebScraper
            - Batch your information needs into fewer, well-constructed search queries
            - Avoid consecutive searches - gather information from each result fully
            - Always check if information is already available before searching again
            
            Follow these research principles:
            1. Thoroughly explore the topic using appropriate tools
            2. Verify information from multiple sources when possible
            3. Provide balanced perspectives on controversial topics
            4. Cite your sources and maintain academic integrity
            5. Organize information clearly and logically
            6. For complex topics, use sequential thinking to break down the problem
            
            Your final response should be thorough and comprehensive. While JSON formatting is helpful for structured data, the most important aspect is providing high-quality information from your research tools. Focus on producing detailed, insightful analysis rather than worrying about strict formatting.
            
            When you complete your research, use the SaveResearch tool to save your findings.
            
            Here are the expected fields for your research report:
            - topic: The main topic of research
            - summary: A concise summary of your findings
            - key_findings: A list of the most important points
            - analysis: In-depth analysis of the topic
            - conclusions: The conclusions of your research
            - sources: A list of sources used
            - tools_used: A list of the tools you used
            - limitations: Any limitations of your research
            - follow_up_questions: Suggested follow-up questions
            
            IMPORTANT OUTPUT RULES:
            1. Do NOT add random characters or non-Latin characters to your response
            2. Do NOT add Chinese, Japanese or other non-English text 
            3. Do NOT end your response with meaningless fragments like "insic", "letter", etc.
            4. Keep your entire response in English only
            5. End your response in a clean, professional manner
            
            Remember, the quality and depth of your research is more important than strict formatting.
            """
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

# Validate tool availability
def print_available_tools(tools_list):
    """Print all available tools and their descriptions."""
    print("\n=== AVAILABLE RESEARCH TOOLS ===")
    
    # Group tools by category
    basic_tools = []
    advanced_tools = []
    
    for tool in tools_list:
        if tool.name in ["AdvancedWebScraper", "AdvancedWebSearch", "DeepWebCrawler", 
                        "DeepResearch", "SequentialThinking"]:
            advanced_tools.append(tool)
        else:
            basic_tools.append(tool)
    
    # Print basic tools
    print("\n--- BASIC TOOLS ---")
    for i, tool in enumerate(basic_tools, 1):
        print(f"{i}. {tool.name}: {tool.description[:100]}...")
    
    # Print advanced tools
    print("\n--- ADVANCED TOOLS ---")
    for i, tool in enumerate(advanced_tools, 1):
        print(f"{i}. {tool.name}: {tool.description[:100]}...")
    
    print(f"\nTotal: {len(tools_list)} tools available ({len(basic_tools)} basic, {len(advanced_tools)} advanced)")
    print("=" * 40 + "\n")

# Combine standard tools with MCP tools
tools = [
    search_tool, 
    wiki_tool, 
    save_tool, 
    scrape_tool, 
    math_tool, 
    weather_tool, 
    news_tool, 
    reddit_tool,
    *mcp_tools  # Add all MCP tools
]

# Print available tools
print_available_tools(tools)

# Create the agent
agent = create_tool_calling_agent(
    llm = llm3, 
    prompt = prompt, 
    tools = tools #these are the things LLM/ agent can use that we either write ourself or can bring in from things like langchain community hub
)

# Add rate limiting for API calls
class RateLimitedAgentExecutor:
    def __init__(self, agent_executor, min_delay=1.0, max_searches=4):
        """
        Wrapper for AgentExecutor that adds rate limiting
        
        Args:
            agent_executor: The AgentExecutor to wrap
            min_delay: Minimum delay in seconds between tool calls
            max_searches: Maximum number of search operations allowed
        """
        self.agent_executor = agent_executor
        self.min_delay = min_delay
        self.last_call_time = 0
        
    def invoke(self, input_data):
        """Execute the agent with rate limiting"""
        # Add delay if needed
        current_time = time.time()
        elapsed = current_time - self.last_call_time
        
        if elapsed < self.min_delay and self.last_call_time > 0:
            sleep_time = self.min_delay - elapsed
            print(f"⏱️ Rate limiting: Waiting {sleep_time:.2f}s between API calls")
            time.sleep(sleep_time)
            
        # Update last call time and execute
        self.last_call_time = time.time()
        return self.agent_executor.invoke(input_data)

# Wrap the agent executor with rate limiting
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
rate_limited_executor = RateLimitedAgentExecutor(agent_executor, min_delay=2.0)  # 2-second minimum delay

def needs_advanced_tools(query):
    """Determine if a query is complex enough to warrant advanced tools."""
    # Keywords that suggest complex analysis
    complex_keywords = [
        "analyze", "compare", "contrast", "evaluate", "synthesize", "implications",
        "philosophy", "ethical", "complex", "nuanced", "perspectives", "comprehensive",
        "detailed", "in-depth", "thorough", "step by step", "breakdown", "multiple",
        "impact", "effects", "causes", "relationship", "interpret", "meaning",
        "versus", "vs", "pros and cons", "advantages", "disadvantages", "debate",
        "controversy", "different views", "theory", "framework", "approach", "method"
    ]
    
    # Check if any complex keywords are in the query (case-insensitive)
    query_lower = query.lower()
    has_complex_keywords = any(keyword in query_lower for keyword in complex_keywords)
    
    # Check for question complexity (multiple questions or long query)
    has_multiple_questions = query_lower.count("?") > 1
    is_long_query = len(query.split()) > 15
    
    return has_complex_keywords or has_multiple_questions or is_long_query

# Use the rate-limited executor instead of the original
query = input("What can I help you with today?")

# Check if the query needs advanced tools
if needs_advanced_tools(query):
    print("📊 Complex query detected. Using advanced tools for comprehensive analysis...")
    # Modify the query to encourage advanced tool usage
    advanced_query = f"This is a complex question requiring advanced analysis tools like SequentialThinking or DeepResearch. Please provide a comprehensive answer using the most appropriate advanced tools: {query}"
    raw_response = rate_limited_executor.invoke({"query": advanced_query})
else:
    raw_response = rate_limited_executor.invoke({"query": query})

print("Raw response type:", type(raw_response))
print("Raw response keys:", raw_response.keys() if isinstance(raw_response, dict) else "Not a dict")
print("Output type:", type(raw_response.get("output")) if isinstance(raw_response, dict) else "N/A")

# Save raw response first
current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
raw_filename = f"raw_response_{current_time}.txt"
save_raw_response_to_file(raw_response, raw_filename)

def clean_strange_characters(text):
    """Remove strange characters like Chinese characters and nonsense text that sometimes appear at the end."""
    if not text:
        return text
        
    # Pattern to match non-Latin characters (including Chinese, Arabic, etc.)
    non_latin_pattern = r'[^\x00-\x7F]+'
    
    # Pattern to match random short strings that don't make sense in context
    nonsense_pattern = r'\b\w{1,4}(?:insic|letter|char|[A-Z]{2,})\b'
    
    # Replace found patterns with empty string
    cleaned_text = re.sub(non_latin_pattern, '', text)
    cleaned_text = re.sub(nonsense_pattern, '', cleaned_text)
    
    # Also remove any lines that are just a few characters
    lines = cleaned_text.split('\n')
    cleaned_lines = [line for line in lines if len(line.strip()) > 5 or len(line.strip()) == 0]
    
    return '\n'.join(cleaned_lines)

# Now parse the response
try:
    output = raw_response.get("output")
    
    # Clean any strange characters from the output
    if isinstance(output, str):
        output = clean_strange_characters(output)
    
    # First, save the full raw output which contains all the tool outputs
    with open("full_research_output.txt", 'w', encoding='utf-8') as f:
        f.write(str(output))
    print(f"Complete research process saved to: full_research_output.txt")
    
    # Also append to the single log file
    with open("research_log.txt", 'a', encoding='utf-8') as f:
        f.write("\n\n" + "="*80 + "\n")
        f.write(f"RESEARCH SESSION: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("QUERY: " + query + "\n")
        f.write("="*80 + "\n\n")
        f.write(str(output))
        f.write("\n\n" + "-"*80 + "\n\n")
    print(f"Research also appended to: research_log.txt")
    
    # Try to parse as JSON if possible, but don't require it
    try:
        # Try direct parsing if it's just a string
        structured_response = parser.parse(output)
        print("Successfully parsed output as JSON.")
        structured_filename = f"formatted_response_{current_time}.txt"
        save_formatted_response_to_file(structured_response, structured_filename)
    except Exception as parse_error:
        print(f"JSON parsing failed: {parse_error}")
        print("Using raw output instead - this is fine!")
        # Just use the raw output directly
        
except Exception as e:
    print("Error in processing the response:", e)
    print("Raw response:", raw_response)


