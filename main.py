#!/usr/bin/env python3
"""
Deep Search - Main Entry Point
Run this script to perform research on a specified topic.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

from input_config import ResearchInput, ResearchSettings
from session.session import Session

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)

async def main():
    """Run the deep search process on a specified topic."""
    load_dotenv()
    
    # Check for required API keys
    required_keys = ['BRAVE_API_KEY', 'FIRECRAWL_API_KEY', 'OPENAI_API_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        logger.error(f"Missing required API keys: {', '.join(missing_keys)}")
        logger.error("Please set these in your .env file")
        return
    
    # Configure research settings
    settings = ResearchSettings(
        max_depth=3,             # Number of research steps
        search_timeout=300,      # Timeout in seconds
        max_results=3,          # Maximum search results
        include_web_content=True,
        include_news=True,
        include_discussions=True,
        language="en"
    )
    
    # Define research topic - this is a broad topic that will yield good results
    research_topic = "Impact of artificial intelligence on healthcare in 2025"
    
    # Create research input
    research_input = ResearchInput(
        query_topic=research_topic,
        settings=settings
    )
    
    # Log start of research
    logger.info(f"Starting deep search on topic: {research_topic}")
    start_time = datetime.now()
    
    # Initialize and run research session
    session = Session(research_input)
    success = await session.run()
    
    # Log completion and results
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if success:
        results = session.session_data.final_results
        logger.info(f"Research completed successfully in {duration:.2f} seconds!")
        
        # Display key findings
        print("\n" + "="*80)
        print(f"RESEARCH RESULTS: {research_topic}")
        print("="*80)
        
        print("\nMAIN REPORT:")
        print("-"*80)
        print(results.main_report)
        
        print("\nKEY LEARNINGS:")
        print("-"*80)
        for i, learning in enumerate(results.key_learnings, 1):
            print(f"{i}. {learning}")
        
        print("\nAREAS COVERED:")
        print("-"*80)
        for i, area in enumerate(results.areas_covered, 1):
            print(f"{i}. {area}")
        
        print("\nAREAS FOR FURTHER EXPLORATION:")
        print("-"*80)
        for i, area in enumerate(results.areas_to_explore, 1):
            print(f"{i}. {area}")
            
        if results.additional_notes:
            print("\nADDITIONAL NOTES:")
            print("-"*80)
            print(results.additional_notes)
    else:
        logger.error(f"Research failed: {session.error_message}")
        print(f"\nERROR: {session.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
