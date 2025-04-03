#lets add tools

from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from datetime import datetime
import requests
import json
import os
import re
import math
import numpy as np
from typing import List, Optional
from bs4 import BeautifulSoup
import time
import random
from duckduckgo_search.exceptions import DuckDuckGoSearchException

# it can search the duckduckgo search engine

# Improved fallback search with better responses
def fallback_search(query):
    """A more advanced fallback search method when DuckDuckGo is rate-limited"""
    # First try to provide a useful general response with Wikipedia knowledge
    try:
        # Try to use Wikipedia for this query instead
        wikipedia_result = wikipedia.run(query)
        if wikipedia_result and len(wikipedia_result) > 100:
            return f"DuckDuckGo search is currently rate-limited. Using Wikipedia instead:\n\n{wikipedia_result}\n\n(Note: This result is from Wikipedia rather than a web search. For more specific or recent information, please try again later.)"
    except Exception:
        pass
    
    # If Wikipedia fails or returns minimal results, provide a structured explanation
    return (
        "🚫 Search is currently rate-limited. Here are some suggestions:\n\n"
        "1. **Be more specific** with your query\n"
        "2. **Use Wikipedia** instead for general knowledge\n"
        "3. **Try the WebScraper tool** if you know a specific website with relevant information\n"
        "4. **Wait a few minutes** before attempting another search\n\n"
        f"Your query was: '{query}'\n\n"
        "This limitation is due to DuckDuckGo's rate limiting policy and not an issue with the research assistant itself."
    )

# Function to improve search queries
def optimize_search_query(query):
    """Optimize a search query to reduce chances of rate limiting"""
    # Remove common filler words that don't add search value
    filler_words = ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "about", "is", "are"]
    
    # Split into words and filter out very short words and filler words
    words = query.split()
    if len(words) > 8:  # If query is long, try to shorten it
        important_words = [w for w in words if len(w) > 2 and w.lower() not in filler_words]
        if len(important_words) > 3:  # Make sure we still have enough meaningful words
            return " ".join(important_words)
    
    # If the query is already concise, just return it
    return query

# Add search result caching
_search_cache = {}  # Global cache for search results

# Update the RateLimitedSearchTool to use the optimized queries
class RateLimitedSearchTool:
    # Class variable to track last search time across all instances
    _last_search_time = 0
    _min_delay_between_searches = 5.0  # 5 seconds minimum between searches
    
    def __init__(self, search_runner, max_retries=3, initial_backoff=5, use_cache=True):
        self.search_runner = search_runner
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff  # Increased to 5 seconds
        self.use_cache = use_cache
        self.name = "Search"
        self.description = "Use this to search the web for information"
    
    def run(self, query):
        """Run the search with retry logic for rate limiting"""
        # Check cache first if enabled
        if self.use_cache and query in _search_cache:
            print(f"🔄 Using cached result for query: '{query}'")
            return _search_cache[query]
            
        # Add delay between consecutive searches
        current_time = time.time()
        elapsed = current_time - RateLimitedSearchTool._last_search_time
        
        if elapsed < RateLimitedSearchTool._min_delay_between_searches and RateLimitedSearchTool._last_search_time > 0:
            delay_time = RateLimitedSearchTool._min_delay_between_searches - elapsed
            print(f"🕒 Search cooldown: Waiting {delay_time:.2f}s before next search...")
            time.sleep(delay_time)
        
        # Optimize the query first
        optimized_query = optimize_search_query(query)
        if optimized_query != query:
            print(f"Optimized query: '{query}' → '{optimized_query}'")
            
            # Check cache for optimized query
            if self.use_cache and optimized_query in _search_cache:
                print(f"🔄 Using cached result for optimized query: '{optimized_query}'")
                return _search_cache[optimized_query]
        
        # Update last search time
        RateLimitedSearchTool._last_search_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            try:
                result = self.search_runner.run(optimized_query)
                # Cache the result
                if self.use_cache:
                    _search_cache[query] = result
                    _search_cache[optimized_query] = result
                return result
            except DuckDuckGoSearchException as e:
                if "Ratelimit" in str(e) and attempt < self.max_retries:
                    # Calculate backoff with jitter (longer delays)
                    backoff_time = self.initial_backoff * (3 ** attempt) + random.uniform(1, 3)
                    print(f"⚠️ Search rate limited. Retrying in {backoff_time:.2f} seconds... (Attempt {attempt+1}/{self.max_retries})")
                    time.sleep(backoff_time)
                else:
                    print("⚠️ Switching to fallback search method...")
                    return fallback_search(query)
            except Exception as e:
                return f"Unexpected search error: {str(e)}"

# Create the standard DuckDuckGo search
standard_search = DuckDuckGoSearchRun()

# Replace the standard search with our rate-limited version
search_tool = Tool(
    name = "Search",
    description = "Use this to search the web for information",
    func = RateLimitedSearchTool(standard_search).run
)

#now we will create a tool that can search the wikipedia
wikipedia = WikipediaAPIWrapper()
wiki_tool = Tool(
    name = "Wikipedia",
    description = "Search Wikipedia for information on a specific topic",
    func = wikipedia.run
)

#creating custom tool
def save_to_txt(data: str, filename: str = "output.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"---- Research Report ----- \nTimestamp: {timestamp} \n\n{data}\n\n"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)
    
    return f"Data saved to {filename}"

save_tool = Tool(
    name = "Save to txt",
    description = "Use this to save the data to a txt file",
    func = save_to_txt
)

# Tool to save research findings to a file
def save_research(research_data: str, filename: Optional[str] = None) -> str:
    """Save research data to a file."""
    if not filename:
        filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, "w") as f:
        f.write(research_data)
    
    return f"Research saved successfully to {filename}"

save_tool = Tool(
    name = "SaveResearch",
    description = "Save research findings to a file. Provide the research data and optionally a filename.",
    func = save_research
)

# Web page scraper
def scrape_webpage(url: str) -> str:
    """Scrape and extract main content from a webpage."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Truncate if too long
        if len(text) > 8000:
            return text[:8000] + "... [content truncated]"
        return text
    except Exception as e:
        return f"Error scraping webpage: {str(e)}"

scrape_tool = Tool(
    name = "WebScraper",
    description = "Scrape and extract content from a webpage. Provide the full URL.",
    func = scrape_webpage
)

# Calculator tool
def calculator(expression: str) -> str:
    """Calculate mathematical expressions."""
    try:
        # Clean the expression
        expression = expression.replace('^', '**')
        
        # Disallow dangerous operations
        if any(op in expression for op in ['import', 'eval', 'exec', 'compile', 'open', '__']):
            return "Invalid expression: potentially unsafe operations"
        
        # Add numpy functions to namespace
        allowed_np_funcs = {
            'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
            'sqrt': np.sqrt, 'log': np.log, 'log10': np.log10,
            'abs': np.abs, 'exp': np.exp
        }
        
        # Create safe namespace
        safe_dict = {**allowed_np_funcs, 'pi': math.pi, 'e': math.e}
        
        # Evaluate the expression
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating: {str(e)}"

math_tool = Tool(
    name = "Calculator",
    description = "Calculate mathematical expressions. Supports basic arithmetic, trigonometric functions (sin, cos, tan), sqrt, log, and constants like pi and e.",
    func = calculator
)

# Weather tool
def get_weather(location: str) -> str:
    """Get current weather for a location."""
    try:
        api_key = os.environ.get("WEATHER_API_KEY")
        if not api_key:
            return "Weather API key not found in environment variables"
        
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': location,
            'appid': api_key,
            'units': 'metric'
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather_desc = data['weather'][0]['description']
        temp = data['main']['temp']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        
        return f"Weather in {location}: {weather_desc}, Temperature: {temp}°C, Humidity: {humidity}%, Wind speed: {wind_speed} m/s"
    except Exception as e:
        return f"Error getting weather: {str(e)}"

weather_tool = Tool(
    name = "WeatherInfo",
    description = "Get current weather information for a location. Provide city name, country.",
    func = get_weather
)

# News API tool
def get_news(query: str, limit: int = 5) -> str:
    """Get latest news on a topic."""
    try:
        api_key = os.environ.get("NEWS_API_KEY")
        if not api_key:
            return "News API key not found in environment variables"
        
        base_url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'apiKey': api_key,
            'pageSize': limit,
            'sortBy': 'publishedAt'
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['totalResults'] == 0:
            return f"No news found for query: {query}"
        
        news_items = []
        for idx, article in enumerate(data['articles'][:limit], 1):
            title = article['title']
            source = article['source']['name']
            url = article['url']
            published = article['publishedAt'][:10]  # Just the date
            news_items.append(f"{idx}. {title} - {source} ({published})\n   URL: {url}")
        
        return f"Latest news on '{query}':\n\n" + "\n\n".join(news_items)
    except Exception as e:
        return f"Error fetching news: {str(e)}"

news_tool = Tool(
    name = "NewsSearch",
    description = "Search for latest news articles on a topic. Provide search query and optionally the number of results.",
    func = get_news
)

# Reddit scraping tool
def scrape_reddit(query: str, limit: int = 5, sort: str = "relevance") -> str:
    """Scrape Reddit for information on a topic."""
    try:
        # Format the query for URL
        formatted_query = query.replace(' ', '+')
        
        # Search URL
        url = f"https://www.reddit.com/search/?q={formatted_query}&sort={sort}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find posts (the structure may change, this is a basic implementation)
        posts = []
        post_elements = soup.find_all('div', {'data-testid': 'post-container'})
        
        if not post_elements:
            # Try alternate selectors if the above didn't work
            post_elements = soup.select('div[data-click-id="body"]')
            
        if not post_elements:
            return f"Couldn't extract Reddit posts using the current scraping method. Reddit may have changed their layout."
        
        # Extract limited number of posts
        for idx, post in enumerate(post_elements[:limit], 1):
            try:
                # Try to get title
                title_elem = post.find('h3')
                title = title_elem.text.strip() if title_elem else "No title found"
                
                # Try to get subreddit
                subreddit_elem = post.find('a', {'data-click-id': 'subreddit'})
                subreddit = subreddit_elem.text.strip() if subreddit_elem else "Unknown subreddit"
                
                # Try to get URL
                link_elem = post.find('a', {'data-click-id': 'body'})
                link = "https://www.reddit.com" + link_elem['href'] if link_elem and 'href' in link_elem.attrs else "No link found"
                
                posts.append(f"{idx}. {title}\n   Subreddit: {subreddit}\n   URL: {link}")
            except Exception as e:
                posts.append(f"{idx}. Error extracting post details: {str(e)}")
        
        if not posts:
            return f"No results found on Reddit for query: {query}"
            
        return f"Reddit results for '{query}':\n\n" + "\n\n".join(posts)
    except Exception as e:
        return f"Error scraping Reddit: {str(e)}"

reddit_tool = Tool(
    name = "RedditSearch",
    description = "Search Reddit for discussions and information on a topic. Provide a search query and optionally the number of results and sort method ('relevance', 'hot', 'new', 'top').",
    func = scrape_reddit
)


