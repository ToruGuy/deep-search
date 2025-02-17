from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, create_model
from firecrawl import FirecrawlApp
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

def create_extraction_schema(research_goals: List[str]):
    """Create a dynamic schema based on research goals"""
    logger.debug(f"Creating extraction schema for {len(research_goals)} goals")
    fields = {}
    
    # Add a field for each research goal
    for i, goal in enumerate(research_goals, 1):
        fields[f"goal{i}"] = (str, Field(description=goal))
        logger.trace(f"Added field goal{i} with description: {goal}")
    
    # Create and return the dynamic model
    schema = create_model("DynamicExtractionSchema", **fields)
    logger.debug("Extraction schema created successfully")
    return schema

@dataclass
class WebExtractor:
    """Handles web content extraction using Firecrawl"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('FIRECRAWL_API_KEY')
        if not self.api_key:
            logger.error("API key not provided and not found in environment variables")
            raise ValueError("API key must be provided or set in FIRECRAWL_API_KEY environment variable")
            
        logger.debug("Initializing FirecrawlApp")
        self.app = FirecrawlApp(api_key=self.api_key)
        logger.debug("WebExtractor initialized successfully")
        
    async def extract_content(self, urls: List[str], research_goals: List[str]) -> Dict[str, Any]:
        """
        Extract factual content from URLs based on research goals
        
        Args:
            urls: List of URLs to extract content from
            research_goals: List of research goals to get answers for
            
        Returns:
            Dictionary containing answers for each goal
        """
        logger.info(f"Starting content extraction for {len(urls)} URLs")
        
        # Create prompt emphasizing factual, concise responses
        goals_formatted = "\n".join(f"- {goal}" for goal in research_goals)
        prompt = f"""
        IMPORTANT: Provide ONLY factual, data-oriented information from these pages. Focus on core facts and verified data.
        
        For each of the following research goals, provide a direct, concise answer using ONLY information explicitly stated in the source:
        {goals_formatted}
        
        Requirements:
        1. ONLY include factual information that is explicitly stated in the sources
        2. Use precise numbers, dates, and statistics when available
        3. Keep answers concise but complete - include all relevant facts
        4. If information for a goal is not found, state "No factual information found"
        5. Do not include opinions, interpretations, or speculative content
        """
        
        try:
            # Create dynamic schema based on goals
            ExtractionSchema = create_extraction_schema(research_goals)
            logger.debug("Created extraction schema")
            
            # Extract content using Firecrawl
            logger.debug("Starting content extraction")
            response = self.app.extract(
                urls=urls,
                params={
                    "prompt": prompt,
                    "schema": ExtractionSchema.model_json_schema(),
                },
            )
            
            if response.get("success"):
                logger.info(f"Successfully extracted content from {len(urls)} URLs")
                return response["data"]
            else:
                logger.error(f"Extraction failed: {response.get('error', 'Unknown error')}")
                raise Exception(f"Extraction failed: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error during content extraction: {str(e)}")
            raise Exception(f"Error during content extraction: {str(e)}")
            
    def _validate_urls(self, urls: List[str]) -> bool:
        """Validate URLs format"""
        if not urls or not isinstance(urls, list):
            return False
        return all(isinstance(url, str) and url.startswith(('http://', 'https://')) for url in urls)


if __name__ == "__main__":
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Load environment variables
    load_dotenv()
    
    # Create extractor
    extractor = WebExtractor()
    
    # Test URLs and goals
    test_urls = [
        "https://en.wikipedia.org/wiki/Quantum_computing"
    ]
    
    test_goals = [
        "What is the current qubit record for quantum computers?",
        "What are the main technical challenges in scaling quantum computers?",
        "What companies are leading in quantum computer development?"
    ]
    
    print("Testing content extraction...")
    try:
        import asyncio
        results = asyncio.run(extractor.extract_content(test_urls, test_goals))
        
        print("\nExtraction Results:")
        for i, goal in enumerate(test_goals, 1):
            print(f"\nGoal: {goal}")
            print(f"Answer: {results[f'goal{i}']}")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")