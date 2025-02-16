from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from research_session import QueryConfig, WebExplorationResult, SearchGrading
from tools.web_search import BraveSearchClient, BraveSearchResult

class JobState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    query_config: QueryConfig
    state: JobState = JobState.NONE
    exploration_results: Optional[WebExplorationResult] = None
    search_gradings: Optional[SearchGrading] = None
    error_message: Optional[str] = None
    _search_client: Optional[BraveSearchClient] = None
    
    def initialize(self) -> bool:
        """Initialize the job"""
        try:
            if not self.query_config or not self.query_config.query:
                self.error_message = "Invalid query configuration: missing query"
                self.state = JobState.FAILED
                return False
                
            if not self.query_config.goals or len(self.query_config.goals) == 0:
                self.error_message = "Invalid query configuration: no research goals provided"
                self.state = JobState.FAILED
                return False
            
            # Initialize search client
            self._search_client = BraveSearchClient()
            
            self.state = JobState.INITIALIZED
            return True
        except Exception as e:
            self.error_message = str(e)
            self.state = JobState.FAILED
            return False
    
    async def run(self) -> bool:
        """Run the job to get web exploration results"""
        if self.state != JobState.INITIALIZED:
            self.error_message = f"Cannot run job in state: {self.state}"
            return False
            
        try:
            self.state = JobState.RUNNING
            
            # Perform web search
            search_results = await self._search_client.search(
                query=self.query_config.query,
                count=10  # Adjust based on your needs
            )
            
            # Convert search results to SERP format
            serp_results = [
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description
                }
                for result in search_results
            ]
            
            # For now, we'll use a simple concatenation of descriptions as web extract
            # In a real implementation, you'd want to actually fetch and process the content
            web_extract = "\n\n".join(result.description for result in search_results)
            
            # Create exploration results
            self.exploration_results = WebExplorationResult(
                serp_results=serp_results,
                web_extract_results=web_extract,
                success_rating=0.8 if serp_results else 0.0
            )
            
            # Create basic search grading
            # In a real implementation, you'd want to actually evaluate the results
            self.search_gradings = SearchGrading(
                relevance_score=0.8 if serp_results else 0.0,
                coverage_score=0.7 if serp_results else 0.0,
                depth_score=0.6 if serp_results else 0.0,
                source_quality=0.9 if serp_results else 0.0,
                notes="Results from Brave Search API"
            )
            
            self.state = JobState.COMPLETED
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.state = JobState.FAILED
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary format"""
        return {
            "query_config": self.query_config.__dict__,
            "state": self.state.value,
            "exploration_results": self.exploration_results.__dict__ if self.exploration_results else None,
            "search_gradings": self.search_gradings.to_dict() if self.search_gradings else None,
            "error_message": self.error_message
        }


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    async def test_job():
        # Load environment variables
        load_dotenv()
        
        # Create test query config
        query_config = QueryConfig(
            query="What are the latest developments in quantum computing?",
            goals=["Understand recent breakthroughs", "Learn about quantum supremacy"]
        )
        
        # Create and test job
        job = Job(query_config=query_config)
        
        # Test initialization
        print("Testing job initialization...")
        init_success = job.initialize()
        print(f"Initialization {'successful' if init_success else 'failed'}")
        print(f"Job state: {job.state}")
        print(f"Error message: {job.error_message}")
        
        if init_success:
            # Test running the job
            print("\nTesting job execution...")
            run_success = await job.run()
            print(f"Execution {'successful' if run_success else 'failed'}")
            print(f"Job state: {job.state}")
            print(f"Error message: {job.error_message}")
            
            if run_success:
                # Print results
                print("\nJob Results:")
                print(f"SERP Results: {len(job.exploration_results.serp_results)} items")
                print("\nFirst result:")
                print(f"Title: {job.exploration_results.serp_results[0]['title']}")
                print(f"URL: {job.exploration_results.serp_results[0]['url']}")
                print(f"Description: {job.exploration_results.serp_results[0]['description'][:200]}...")
                print(f"\nSuccess Rating: {job.exploration_results.success_rating}")
                print(f"Search Grading: {job.search_gradings.to_dict()}")
    
    # Run the test
    asyncio.run(test_job())
