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

from tools.web_search import (
    BraveSearchClient, BraveSearchResponse, SearchOptions, 
    Freshness, ResultType, SafeSearch, Units, BraveSearchResult
)
from tools.web_extract import WebExtractor, WebExtractionResult
from input_config import ResearchSettings

class JobState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class QueryConfig:
    """Configuration for a research query.
    
    Attributes:
        query (str): The main research query
        goals (List[str]): List of research goals to achieve
        context (Optional[str]): Additional context for the query
        max_depth (int): Maximum depth for recursive research
        max_results_per_goal (int): Maximum number of results to fetch per goal
    """
    query: str
    goals: List[str]
    context: Optional[str] = None
    max_depth: int = 2
    max_results_per_goal: int = 5
    
    def __post_init__(self):
        """Validate the query configuration"""
        if not self.query:
            raise ValueError("Query cannot be empty")
        if not self.goals:
            raise ValueError("At least one research goal is required")
        if self.max_depth < 1:
            raise ValueError("Max depth must be at least 1")
        if self.max_results_per_goal < 1:
            raise ValueError("Max results per goal must be at least 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert QueryConfig to dictionary format"""
        return {
            "query": self.query,
            "goals": self.goals,
            "context": self.context,
            "max_depth": self.max_depth,
            "max_results_per_goal": self.max_results_per_goal
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryConfig':
        """Create QueryConfig from dictionary"""
        return cls(
            query=data["query"],
            goals=data["goals"],
            context=data.get("context"),
            max_depth=data.get("max_depth", 2),
            max_results_per_goal=data.get("max_results_per_goal", 5)
        )

@dataclass
class JobData:
    query_config: QueryConfig
    search_results: Optional[List[BraveSearchResult]] = None
    extraction_result: Optional[WebExtractionResult] = None
    learnings: Dict[str, Any] = field(default_factory=dict)
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: JobState = JobState.NONE
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert JobData to dictionary format"""
        return {
            "job_id": self.job_id,
            "state": self.state.value,
            "query_config": self.query_config.to_dict(),
            "search_results": [result.to_dict() for result in self.search_results] if self.search_results else None,
            "extraction_result": self.extraction_result.dict() if self.extraction_result else None,
            "learnings": self.learnings,
            "error_message": self.error_message
        }


class Job:
    def __init__(
        self, 
        query_config: QueryConfig,
        settings: ResearchSettings = ResearchSettings(),
        search_client: Optional[BraveSearchClient] = None,
        web_extractor: Optional[WebExtractor] = None
    ):
        """Initialize a research job.
        
        Args:
            query_config (QueryConfig): Configuration for the research query
            settings (ResearchSettings): Research settings for the job
            search_client (Optional[BraveSearchClient]): Pre-configured search client
            web_extractor (Optional[WebExtractor]): Pre-configured web extractor
        
        Raises:
            ValueError: If query_config is invalid
        """
        if not isinstance(query_config, QueryConfig):
            raise ValueError("query_config must be an instance of QueryConfig")
            
        self._query_config = query_config
        self._settings = settings
        self._search_client = search_client
        self._web_extractor = web_extractor
        self.job_data = None  # Will be created during initialization

    @property
    def job_id(self) -> str:
        return self.job_data.job_id if self.job_data else None

    @property
    def query_config(self) -> QueryConfig:
        return self.job_data.query_config if self.job_data else self._query_config

    @property
    def state(self) -> JobState:
        return self.job_data.state if self.job_data else JobState.NONE

    @state.setter
    def state(self, value: JobState):
        if self.job_data:
            self.job_data.state = value

    @property
    def error_message(self) -> Optional[str]:
        return self.job_data.error_message if self.job_data else None

    @error_message.setter
    def error_message(self, value: Optional[str]):
        if self.job_data:
            self.job_data.error_message = value

    def initialize(self) -> bool:
        """Initialize the job.
        
        Returns:
            bool: True if initialization was successful, False otherwise
            
        Raises:
            ValueError: If required dependencies are not provided
        """
        try:
            # Create job data with provided query config
            self.job_data = JobData(query_config=self._query_config)
            
            logger.info(f"Initializing job {self.job_id} with query: {self.query_config.query}")

            # Validate search client and web extractor
            if self._search_client is None:
                raise ValueError("BraveSearchClient must be provided")
            if self._web_extractor is None:
                raise ValueError("WebExtractor must be provided")
            
            self.state = JobState.INITIALIZED
            logger.debug(f"Job {self.job_id} initialized successfully")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.state = JobState.FAILED
            logger.error(f"Job {self.job_id} initialization failed: {self.error_message}")
            return False

    async def run(self) -> bool:
        """Run the job"""
        if self.state != JobState.INITIALIZED:
            self.error_message = f"Job not initialized. Current state: {self.state}"
            self.state = JobState.FAILED
            return False

        try:
            self.state = JobState.RUNNING
            logger.info(f"Running job {self.job_id}")

            # Create search options
            search_options = self._create_search_options()

            # Perform web search
            logger.info(f"Performing search for job {self.job_id}")
            search_response = await self._search_client.search(search_options)
            
            if not search_response or not search_response.results:
                self.error_message = "No search results found"
                self.state = JobState.FAILED
                return False
                
            logger.info(f"Web search completed for job {self.job_id}")
            
            # Store search results
            self.job_data.search_results = search_response.results
            
            # Extract content from search results
            logger.info(f"Extracting content for job {self.job_id}")
            
            # Get URLs from search results
            urls = [result.url for result in search_response.results]
            
            extraction_result = await self._web_extractor.extract_content(
                urls=urls,
                research_goals=self.query_config.goals
            )
            
            if not extraction_result:
                self.error_message = "Failed to extract content from search results"
                self.state = JobState.FAILED
                return False

            # Gather all answers into one string
            learnings = f"Query: {self.query_config.query}\n" + "\n".join([
                f"Goal {i+1}: {answer}"
                for i, answer in enumerate(extraction_result.answers.values())
            ])
                
            logger.info(f"Web extraction completed for job {self.job_id}")
            
            # Store extraction result
            self.job_data.learnings = learnings
            
            self.state = JobState.COMPLETED
            logger.info(f"Job {self.job_id} completed successfully")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.state = JobState.FAILED
            logger.error(f"Job {self.job_id} failed: {self.error_message}")
            return False

    def get_results(self) -> JobData:
        """Get the job results"""
        if self.state != JobState.COMPLETED:
            logger.warning(f"Attempting to get results for incomplete job {self.job_id}")
            return None
            
        logger.debug(f"Retrieving results for job {self.job_id}")
        return self.job_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary format"""
        return {
            "state": self.state.value,
            "error_message": self.error_message,
            "job_data": self.job_data.to_dict() if self.job_data else None,
            "settings": self._settings.to_dict()
        }

    def _create_search_options(self) -> SearchOptions:
        """Create search options from research settings and query config"""
        result_types = []
        if self._settings.include_web_content:
            result_types.append(ResultType.WEB)
        if self._settings.include_news:
            result_types.append(ResultType.NEWS)
        if self._settings.include_discussions:
            result_types.append(ResultType.DISCUSSIONS)
        
        return SearchOptions(
            query=self.query_config.query,
            count=self._settings.max_results,
            freshness=Freshness.PAST_YEAR,  # Default to past year
            result_filter=result_types if result_types else None,
            safesearch=SafeSearch.MODERATE,
            extra_snippets=True,  # Always get extra context
            summary=False,
            search_lang=self._settings.language
        )


def print_job_results(job: Job):
    """Print the results of a successful job."""
    if job.state != JobState.COMPLETED:
        print(f"Job is not completed. Current state: {job.state}")
        return
        
    print("\nJob completed successfully!")
    
    results = job.get_results()
    if not results or not results.search_results:
        print("No results available.")
        return
        
    print("\nSearch Results:")
    for result in results.search_results:
        print("\n" + "="*80)
        print(f"Title: {result.title}")
        print(f"URL: {result.url}")
        print(f"Type: {result.result_type.value}")
        print(f"Description: {result.description}")
        print(f"Page Age: {result.page_age}")
        print(f"Source Type: {result.source_type}")
        
        if result.summary:
            print(f"\nSummary: {result.summary}")
        if result.extra_snippets:
            print("\nExtra Snippets:")
            for snippet in result.extra_snippets:
                print(f"  - {snippet}")
    
    print("\nExtracted Content:")
    if results.learnings:
        print(results.learnings)


async def test_job():
    """Test job functionality with a sample query"""
    try:
        # Load environment variables for API keys
        load_dotenv()
        
        # Get API keys
        brave_api_key = os.getenv('BRAVE_API_KEY')
        firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
        
        if not brave_api_key:
            raise ValueError("BRAVE_API_KEY must be set in environment")
        if not firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY must be set in environment")
        
        # Create test settings
        settings = ResearchSettings(
            max_results=3,
            language="en",
            include_web_content=True,
            include_news=True,
            include_discussions=True,
            max_depth=2,
            search_timeout=30
        )
        
        # Initialize required dependencies with API keys
        search_client = BraveSearchClient(api_key=brave_api_key)
        web_extractor = WebExtractor(api_key=firecrawl_api_key)
        
        # Create a test query config
        query_config = QueryConfig(
            query="What are the latest developments in quantum computing?",
            goals=[
                "Identify recent breakthroughs in quantum computing",
                "List major companies working on quantum computers",
                "Describe challenges in quantum computing development"
            ]
        )
        
        # Create and initialize job with dependencies
        job = Job(
            query_config=query_config,
            settings=settings,
            search_client=search_client,
            web_extractor=web_extractor
        )
        
        if not job.initialize():
            print(f"Job initialization failed: {job.error_message}")
            return
            
        print("\nRunning job...")
        if not await job.run():
            print(f"Job execution failed: {job.error_message}")
            return
            
        print("\nJob completed successfully!")
        print_job_results(job)
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Run the test
    asyncio.run(test_job())
