from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# Add the root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from input_config import ResearchInput, ResearchSettings
from session.step import Step, StepData
from session.researcher import Researcher, ResearchResults
from tools.web_search import BraveSearchClient
from tools.web_extract import WebExtractor

@dataclass
class SessionData:
    """Main container for all research-related data produced during a research run"""
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    steps: List[StepData] = field(default_factory=list)
    final_results: Optional[ResearchResults] = None

class SessionState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RESEARCHING = "researching"
    COMPLETED = "completed"
    ERROR = "error"

class Session:
    """Main session controller that manages the research process"""
    
    def __init__(self, research_input: ResearchInput):
        """Initialize the research session with required components
        
        Args:
            research_input: Configuration for the research session
            
        Raises:
            ValueError: If required API keys are missing or research input is invalid
        """
        load_dotenv()
        
        if not research_input.validate():
            raise ValueError("Invalid research input")
            
        self.research_input = research_input
        self.state = SessionState.NONE
        self.error_message: Optional[str] = None
        
        # Generate a unique session ID using timestamp
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_data = SessionData(session_id=session_id)
        
        # Initialize clients
        brave_api_key = os.getenv('BRAVE_API_KEY')
        firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not brave_api_key:
            raise ValueError("BRAVE_API_KEY must be set in environment")
        if not firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY must be set in environment")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment")
            
        self.search_client = BraveSearchClient(api_key=brave_api_key)
        self.web_extractor = WebExtractor(api_key=firecrawl_api_key)
        self.researcher = Researcher(
            api_key=openai_api_key,
            breath=self.research_input.settings.max_depth
        )
        self.state = SessionState.INITIALIZED
            
    async def run(self) -> bool:
        """Start the research process
        
        Returns:
            bool: True if research completed successfully, False otherwise
        """
        if self.state != SessionState.INITIALIZED:
            logger.error("Cannot start research - session not initialized")
            return False
            
        try:
            self.state = SessionState.RESEARCHING
            all_learnings = []
            all_sources = []
            step_number = 1
            
            while step_number <= self.research_input.settings.max_depth:
                logger.info(f"Starting research step {step_number}")
                
                # Generate queries for this step using researcher
                queries = self.researcher.create_queries(
                    self.research_input.query_topic,
                    all_learnings
                )
                logger.info("Step {} queries: {}", step_number, queries)
                
                # Initialize research step with clients and queries
                step = Step(
                    step_number=step_number,
                    query_configs=queries,  # Pass the generated queries directly
                    settings=self.research_input.settings,
                    search_client=self.search_client,
                    web_extractor=self.web_extractor
                )
                
                # Run the research step
                if not await step.run():
                    raise Exception("Research step failed")
                    
                # Get results
                step_data = step.get_results()
                self.session_data.steps.append(step_data)
                
                # Log step results
                logger.info(f"\n{'='*50}\nStep {step_number} Results\n{'='*50}")
                
                # Log learnings
                logger.info("\nLearnings from this step:")
                if step_data.learnings:
                    all_learnings.append(step_data.learnings)
                    for learning in step_data.learnings.split('\n'):
                        if learning.strip():
                            logger.info(f"  • {learning.strip()}")
                
                # Log sources
                logger.info("\nSources visited in this step:")
                step_sources = []
                for job_id, job_data in step_data.jobs_data.items():
                    if job_data.search_results:
                        for result in job_data.search_results:
                            source = {
                                "title": result.title,
                                "url": result.url,
                                "page_age": result.page_age,
                                "description": result.description
                            }
                            step_sources.append(source)
                            logger.info(f"\n  Source: {result.title}")
                            logger.info(f"  URL: {result.url}")
                            logger.info(f"  Age: {result.page_age or 'Unknown'}")
                            logger.info(f"  Description: {result.description}")
                
                all_sources.extend(step_sources)
                logger.info(f"\n{'='*50}\n")
                
                step_number += 1
                
            # Generate final research results using researcher
            logger.info("Generating final research report")
            self.session_data.final_results = self.researcher.write_report(all_learnings)
            
            self.state = SessionState.COMPLETED
            self.session_data.end_time = datetime.now()
            return True
            
        except Exception as e:
            self.state = SessionState.ERROR
            self.error_message = str(e)
            logger.error(f"Research failed: {e}")
            return False

    def get_status(self) -> dict:
        """Get the current status of the research session"""
        return {
            "state": self.state.value,
            "error": self.error_message if self.error_message else None,
            "has_results": bool(self.session_data and self.session_data.final_results)
        }

if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Load environment variables
    load_dotenv()
    
    # Create example research input with settings including OpenAI key
    research_input = ResearchInput(
        query_topic="Game-Changing AI Developments in 2025: Emerging Trends, Key Innovations, and Industry Leaders Shaping the Future",
        settings=ResearchSettings(
            max_depth=4,
            search_timeout=300,
            max_results=3,
            include_web_content=True,
            include_news=True,
            include_discussions=True,
            language="en",
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
    )
    
    # Create and run session
    session = Session(research_input=research_input)
    
    print("Initializing research session...")
    if session.state != SessionState.INITIALIZED:
        print(f"Session initialization failed: {session.error_message}")
        exit(1)
    
    print("\nStarting research process...")
    if not asyncio.run(session.run()):
        print(f"Research process failed: {session.error_message}")
        exit(1)
        
    # Print final summary
    print(f"\n{'='*50}\nFinal Research Summary\n{'='*50}")
    print("\nMain Report:")
    print(session.session_data.final_results.main_report)
    
    print("\nKey Learnings:")
    for learning in session.session_data.final_results.key_learnings:
        print(f"  • {learning}")
    
    print("\nAreas Covered:")
    for area in session.session_data.final_results.areas_covered:
        print(f"  • {area}")
    
    print("\nAreas to Explore:")
    for area in session.session_data.final_results.areas_to_explore:
        print(f"  • {area}")
    
    print("\nAll Sources Used:")
    all_sources = []
    for step_data in session.session_data.steps:
        for job_id, job_data in step_data.jobs_data.items():
            if job_data.search_results:
                for result in job_data.search_results:
                    source = {
                        "title": result.title,
                        "url": result.url,
                        "page_age": result.page_age,
                        "description": result.description
                    }
                    all_sources.append(source)
    
    for i, source in enumerate(all_sources, 1):
        print(f"\n{i}. {source['title']}")
        print(f"   URL: {source['url']}")
        print(f"   Age: {source['page_age'] or 'Unknown'}")
        print(f"   Description: {source['description']}")
    
    print(f"\n{'='*50}\n")
