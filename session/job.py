from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import os
import sys
import uuid
from datetime import datetime
from loguru import logger

# Add the root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from session.research_session_configs import QueryConfig, WebExplorationResult, SearchGrading, ReaserchJobData
from tools.web_search import BraveSearchClient, BraveSearchResult
from tools.web_extract import WebExtractor

class JobState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    query_config: QueryConfig
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: JobState = JobState.NONE
    exploration_results: Optional[WebExplorationResult] = None
    learnings: Dict[str, Any] = field(default_factory=dict)
    search_gradings: Optional[SearchGrading] = None
    error_message: Optional[str] = None
    _search_client: Optional[BraveSearchClient] = None
    _web_extractor: Optional[WebExtractor] = None
    
    def initialize(self) -> bool:
        """Initialize the job"""
        logger.info(f"Initializing job {self.job_id} with query: {self.query_config.query}")
        try:
            if not self.query_config or not self.query_config.query:
                self.error_message = "Invalid query configuration: missing query"
                self.state = JobState.FAILED
                logger.error(f"Job {self.job_id} initialization failed: {self.error_message}")
                return False
                
            if not self.query_config.goals or len(self.query_config.goals) == 0:
                self.error_message = "Invalid query configuration: no research goals provided"
                self.state = JobState.FAILED
                logger.error(f"Job {self.job_id} initialization failed: {self.error_message}")
                return False
            
            # Initialize search client and web extractor
            self._search_client = BraveSearchClient()
            self._web_extractor = WebExtractor()
            
            self.state = JobState.INITIALIZED
            logger.debug(f"Job {self.job_id} initialized successfully")
            return True
        except Exception as e:
            self.error_message = str(e)
            self.state = JobState.FAILED
            logger.error(f"Job {self.job_id} initialization failed: {self.error_message}")
            return False
    
    async def run(self) -> bool:
        """Run the job to get web exploration results"""
        if self.state != JobState.INITIALIZED:
            self.error_message = f"Cannot run job in state: {self.state}"
            logger.error(f"Cannot run job {self.job_id}: {self.error_message}")
            return False
            
        logger.info(f"Starting job {self.job_id} execution")
        try:
            self.state = JobState.RUNNING
            
            # Perform web search
            logger.debug(f"Starting web search for job {self.job_id}")
            search_results = await self._search_client.search(
                query=self.query_config.query,
                count=3  # Adjust based on your needs
            )
            logger.info(f"Found {len(search_results)} search results for job {self.job_id}")
            
            # Convert search results to SERP format
            serp_results = [
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description
                }
                for result in search_results
            ]
            
            # Extract URLs for content extraction
            urls = [result.url for result in search_results]
            
            # Extract content using Firecrawl
            logger.debug(f"Starting web extraction for job {self.job_id}")
            extraction_results = await self._web_extractor.extract_content(
                urls=urls,
                research_goals=self.query_config.goals
            )
            logger.info(f"Web extraction completed for job {self.job_id}")
            
            # Create exploration results
            self.exploration_results = WebExplorationResult(
                serp_results=serp_results,
                web_extract_results=extraction_results,
                success_rating=0.8 if serp_results else 0.0
            )
            
            # Create search grading
            self.search_gradings = SearchGrading(
                relevance_score=0.8 if serp_results else 0.0,
                coverage_score=0.7 if serp_results else 0.0,
                depth_score=0.6 if serp_results else 0.0,
                source_quality=0.9 if serp_results else 0.0,
                notes="Results from Brave Search API and Firecrawl extraction"
            )
            
            self.state = JobState.COMPLETED
            logger.info(f"Job {self.job_id} completed successfully")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.state = JobState.FAILED
            logger.error(f"Job {self.job_id} execution failed: {self.error_message}")
            return False
    
    def get_results(self) -> ReaserchJobData:
        """Get the job data in ReaserchJobData format"""
        logger.debug(f"Retrieving results for job {self.job_id}")
        return ReaserchJobData(
            query_config=self.query_config,
            exploration_results=self.exploration_results,
            learnings=self.learnings,
            search_gradings=self.search_gradings
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary format"""
        logger.debug(f"Converting job {self.job_id} to dictionary")
        return {
            "state": self.state.value,
            "error_message": self.error_message,
            "exploration_results": self.exploration_results.__dict__ if self.exploration_results else None,
            "search_gradings": self.search_gradings.__dict__ if self.search_gradings else None
        }


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    def print_job_results(job: Job):
        """Print the results of a successful job."""
        print("\nJob completed successfully!")
        
        results = job.get_results()
        if not results.exploration_results:
            print("No exploration results available.")
            return
            
        print("\nExploration Results:")
        print("\nSERP Results:")
        for result in results.exploration_results.serp_results:
            print(f"- {result['title']}: {result['url']}")
        
        print("\nExtracted Answers:")
        for i, goal in enumerate(results.query_config.goals, 1):
            print(f"\nGoal: {goal}")
            print(f"Answer: {results.exploration_results.web_extract_results[f'goal{i}']}")
        
        if results.search_gradings:
            print("\nSearch Grading:")
            print(f"Relevance: {results.search_gradings.relevance_score}")
            print(f"Coverage: {results.search_gradings.coverage_score}")
            print(f"Depth: {results.search_gradings.depth_score}")
            print(f"Source Quality: {results.search_gradings.source_quality}")
            print(f"Notes: {results.search_gradings.notes}")
    
    async def test_job():
        # Load environment variables
        load_dotenv()
        
        # Create test query config
        query_config = QueryConfig(
            query="Fastest production car",
            goals=[
                "What's the fastest production car make and model?",
                "What's the top speed?",
                "How much it costs?"
            ]
        )
        
        # Create job
        job = Job(query_config=query_config)
        
        # Initialize and run job
        print("Initializing job...")
        if not job.initialize():
            print(f"Job initialization failed: {job.error_message}")
            return False
            
        print("Running job...")
        if not await job.run():
            print(f"Job failed: {job.error_message}")
            return False
            
        # Print results if successful
        print_job_results(job)
        return True
    
    # Run the test
    asyncio.run(test_job())
