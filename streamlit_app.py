import streamlit as st
from dotenv import load_dotenv
import os
from main import (
    clean_strange_characters,
    needs_advanced_tools,
    save_formatted_response_to_file,
    save_raw_response_to_file,
    rate_limited_executor,
    llm3
)

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🔍",
    layout="wide"
)

# Title and description
st.title("🤖 Advanced AI Research Assistant")
st.markdown("""
This tool helps you conduct comprehensive research on any topic using:
- Web Search with rate limiting
- Wikipedia integration
- News and Reddit data
- Advanced analysis tools
""")

# Sidebar for API keys
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("DeepSeek API Key", type="password")
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("Built with Streamlit, LangChain, and DeepSeek")

# Main interface
query = st.text_area("Enter your research query:", height=100)

if st.button("Start Research", type="primary"):
    if not api_key:
        st.error("Please enter your DeepSeek API Key in the sidebar")
    else:
        try:
            with st.spinner("Conducting research..."):
                # Check if query needs advanced tools
                if needs_advanced_tools(query):
                    st.info("📊 Complex query detected. Using advanced analysis tools...")
                    advanced_query = f"This is a complex question requiring advanced analysis tools. Please provide a comprehensive answer: {query}"
                    raw_response = rate_limited_executor.invoke({"query": advanced_query})
                else:
                    raw_response = rate_limited_executor.invoke({"query": query})

                # Process and display results
                if raw_response:
                    output = raw_response.get("output")
                    if isinstance(output, str):
                        output = clean_strange_characters(output)
                    
                    # Display results in expandable sections
                    with st.expander("📝 Research Results", expanded=True):
                        st.markdown(output)
                    
                    # Save results
                    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"research_{current_time}.txt"
                    
                    save_raw_response_to_file(raw_response, f"raw_response_{current_time}.txt")
                    
                    # Offer download buttons
                    st.download_button(
                        label="Download Research Report",
                        data=output,
                        file_name=filename,
                        mime="text/plain"
                    )
                    
                    # Show sources and tools used
                    if isinstance(raw_response, dict):
                        with st.expander("🔍 Sources and Tools"):
                            if "sources" in raw_response:
                                st.markdown("### Sources")
                                for source in raw_response["sources"]:
                                    st.markdown(f"- {source}")
                            if "tools_used" in raw_response:
                                st.markdown("### Tools Used")
                                for tool in raw_response["tools_used"]:
                                    st.markdown(f"- {tool}")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.markdown("Please try again with a different query or check your API key.") 