from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, create_model
from firecrawl import FirecrawlApp
from datetime import datetime
import os
import sys
import requests
from dotenv import load_dotenv
from loguru import logger

class ExtractionResult(BaseModel):
    """Core factual answers to research goals"""
    goal1: str = Field(description="Answer to the first research goal")
    goal2: Optional[str] = Field(None, description="Answer to the second research goal")
    goal3: Optional[str] = Field(None, description="Answer to the third research goal")
    goal4: Optional[str] = Field(None, description="Answer to the fourth research goal")
    goal5: Optional[str] = Field(None, description="Answer to the fifth research goal")

class WebExtractionResult(BaseModel):
    """Final consolidated extraction results"""
    timestamp: datetime = Field(default_factory=datetime.now)
    answers: Dict[str, str]
    sources: List[str] 

class WebExtractor:
    """Handles web content extraction using Firecrawl"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('FIRECRAWL_API_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided or set in FIRECRAWL_API_KEY environment variable")
            
        self.app = FirecrawlApp(api_key=self.api_key)
        logger.debug("WebExtractor initialized successfully")
        
    def _create_schema(self, research_goals: List[str]) -> Dict[str, Any]:
        """Create a schema based on research goals"""
        properties = {}
        required = ["goal1"]  # First goal is always required
        
        for i, goal in enumerate(research_goals, 1):
            field_name = f"goal{i}"
            properties[field_name] = {
                "type": "string",
                "description": goal
            }
            if i > 1:  # Make all goals after the first optional
                properties[field_name]["default"] = "NA"
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
        
    async def extract_content(self, urls: List[str], research_goals: List[str]) -> WebExtractionResult:
        """Extract factual content from URLs based on research goals"""
        logger.info(f"Starting content extraction for {len(urls)} URLs")
        
        # Format research goals
        goals_formatted = "\n".join(f"- {goal}" for goal in research_goals)
        prompt = f"""
        IMPORTANT: Provide ONLY factual, data-oriented information from these pages. Focus on core facts and verified data.
        
        For each of the following research goals, provide a direct, concise answer using ONLY information explicitly stated in the source:
        {goals_formatted}
        
        Requirements:
        1. ONLY include factual information that is explicitly stated in the sources
        2. Use precise numbers, dates, and statistics when available
        3. Keep answers concise but complete - include all relevant facts
        4. If information for a goal is not found, state "NA"
        5. Do not include opinions, interpretations, or speculative content
        """
        
        try:
            # Extract content using Firecrawl with manually created schema
            response = self.app.extract(
                urls=urls,
                params={
                    "prompt": prompt,
                    "schema": self._create_schema(research_goals),
                },
            )
            
            if not response.get("success"):
                raise ValueError(f"Extraction failed: {response.get('error', 'Unknown error')}")
                
            # Convert response data to answers dictionary
            answers = {
                f"goal{i+1}": response["data"].get(f"goal{i+1}", "NA")
                for i in range(len(research_goals))
            }
            
            return WebExtractionResult(
                answers=answers,
                sources=urls
            )
                
        except requests.HTTPError as e:
            logger.error(f"API error: {e.status_code} - {e.response.text}")
            raise ValueError("Service unavailable") from e
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Network issue: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during extraction: {str(e)}")
            raise ValueError("Failed to extract content") from e

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
        print(f"Source URLs: {results.sources}")
        print(f"Extraction Timestamp: {results.timestamp}")
        for i, goal in enumerate(test_goals, 1):
            print(f"\nGoal: {goal}")
            print(f"Answer: {results.answers.get(f'goal{i}', 'NA')}")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")