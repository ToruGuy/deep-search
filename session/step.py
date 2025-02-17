import os
import sys
from datetime import datetime
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from loguru import logger

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from session.job import Job, JobState, QueryConfig, JobData
from tools.web_extract import WebExtractor
from tools.web_search import BraveSearchClient
from input_config import ResearchSettings

class StepState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class StepData:
    """Data collected during the research step"""
    step_number: int
    state: StepState
    error_message: Optional[str]
    jobs_data: Dict[str, JobData]  # Map of job_id to JobData
    learnings: str  # Concatenated learnings from all jobs
    timestamp: datetime = field(default_factory=lambda: datetime.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "state": self.state.value,
            "error_message": self.error_message,
            "jobs_data": {job_id: job_data.to_dict() for job_id, job_data in self.jobs_data.items()},
            "learnings": self.learnings,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class Step:
    """A research step that manages multiple jobs and aggregates their results"""
    step_number: int
    query_configs: List[QueryConfig]
    settings: ResearchSettings
    search_client: Optional[BraveSearchClient] = None
    web_extractor: Optional[WebExtractor] = None
    state: StepState = StepState.NONE
    jobs: Dict[str, Job] = field(default_factory=dict)  # Map of job_id to Job
    error_message: Optional[str] = None

    def __init__(
        self,
        step_number: int,
        query_configs: List[QueryConfig],
        settings: ResearchSettings,
        search_client: Optional[BraveSearchClient] = None,
        web_extractor: Optional[WebExtractor] = None
    ):
        """Initialize the research step with required dependencies"""
        logger.info(f"Initializing research step {step_number}")
        load_dotenv()
        try:
            self.step_number = step_number
            self.query_configs = query_configs
            self.settings = settings
            self.state = StepState.NONE
            self.jobs = {}
            self.error_message = None
            
            # Initialize dependencies if not provided
            if search_client is None:
                brave_api_key = os.getenv('BRAVE_API_KEY')
                if not brave_api_key:
                    raise ValueError("BRAVE_API_KEY must be set in environment")
                self.search_client = BraveSearchClient(api_key=brave_api_key)
            else:
                self.search_client = search_client
                
            if web_extractor is None:
                firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
                if not firecrawl_api_key:
                    raise ValueError("FIRECRAWL_API_KEY must be set in environment")
                self.web_extractor = WebExtractor(api_key=firecrawl_api_key)
            else:
                self.web_extractor = web_extractor
            
            # Initialize jobs from query configs
            if self.query_configs:
                for config in self.query_configs:
                    job_id = self.add_job(config)
                    if not job_id:
                        raise ValueError(f"Failed to add job: {self.error_message}")
            
            self.state = StepState.INITIALIZED
            logger.debug("Research step initialized successfully")
            
        except Exception as e:
            self.error_message = str(e)
            self.state = StepState.FAILED
            logger.error(f"Research step initialization failed: {self.error_message}")
            raise

    def add_job(self, query_config: QueryConfig) -> Optional[str]:
        """Add a new job to the research step. Returns job_id if successful, None otherwise."""
        logger.info(f"Adding new job with query: {query_config.query}")
        try:
            job = Job(
                query_config=query_config,
                search_client=self.search_client,
                web_extractor=self.web_extractor,
                settings=self.settings
            )
            
            if not job.initialize():
                raise ValueError(f"Failed to initialize job: {job.error_message}")
                
            self.jobs[job.job_id] = job
            logger.debug(f"Job {job.job_id} added successfully. Total jobs: {len(self.jobs)}")
            return job.job_id
        except Exception as e:
            self.error_message = f"Failed to add job: {str(e)}"
            return None
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by its ID"""
        return self.jobs.get(job_id)

    async def _run_job(self, job_id: str, job: Job) -> None:
        """Run a single job"""
        logger.debug(f"Processing job {job_id}")
        if not job.initialize():
            logger.warning(f"Job {job_id} initialization failed: {job.error_message}")
            return
            
        await job.run()
        if job.state != JobState.COMPLETED:
            logger.warning(f"Job {job_id} execution failed: {job.error_message}")

    async def run(self) -> bool:
        """Run all jobs in the research step concurrently"""
        if self.state != StepState.INITIALIZED:
            self.error_message = f"Cannot run step in state: {self.state}"
            logger.error(f"Cannot run step: {self.error_message}")
            return False
            
        logger.info(f"Running research step {self.step_number} with {len(self.jobs)} jobs")
        try:
            self.state = StepState.RUNNING
            
            # Create tasks for all jobs
            job_tasks = []
            for job_id, job in self.jobs.items():
                task = asyncio.create_task(self._run_job(job_id, job))
                job_tasks.append(task)
            
            # Wait for all jobs to complete
            await asyncio.gather(*job_tasks)
            
            # Check if any jobs failed
            failed_jobs = [job for job in self.jobs.values() if job.state == JobState.FAILED]
            if failed_jobs:
                job_errors = [f"{job.job_id}: {job.error_message}" for job in failed_jobs]
                self.error_message = f"Some jobs failed: {'; '.join(job_errors)}"
                self.state = StepState.FAILED
                logger.error(f"Research step failed: {self.error_message}")
                return False
            
            self.state = StepState.COMPLETED
            logger.info(f"Research step {self.step_number} completed successfully")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.state = StepState.FAILED
            logger.error(f"Research step failed: {self.error_message}")
            return False
    
    def _create_step_learnings(self) -> str:
        """Create step learnings by concatenating all job learnings.
        
        Returns:
            str: Combined learnings from all completed jobs
        """
        logger.debug("Creating step learnings")
        successful_jobs = [job for job in self.jobs.values() if job.state == JobState.COMPLETED]
        
        all_learnings = []
        for job in successful_jobs:
            job_data = job.get_results()
            if job_data and job_data.learnings:
                all_learnings.append(job_data.learnings)
        
        if not all_learnings:
            return "No learnings collected from the research"
            
        return "\n".join(all_learnings)

    def get_results(self) -> Optional[StepData]:
        """Get the research step results.
        
        Returns:
            Optional[StepData]: Step data including all job data and learnings if step is completed
        """
        if self.state != StepState.COMPLETED:
            logger.warning(f"Attempting to get results for incomplete step {self.step_number}")
            return None
        
        logger.debug(f"Retrieving results for step {self.step_number}")
        
        # Collect all job data
        jobs_data = {}
        for job_id, job in self.jobs.items():
            job_data = job.get_results()
            if job_data:
                jobs_data[job_id] = job_data
        
        # Create step data with all collected information
        return StepData(
            step_number=self.step_number,
            state=self.state,
            error_message=self.error_message,
            jobs_data=jobs_data,
            learnings=self._create_step_learnings()
        )

if __name__ == "__main__":
    import asyncio
    
    async def test_research_step():
        try:
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
            
            # Create test queries
            test_queries = [
                ("Latest developments in quantum computing", [
                    "What are the most recent breakthroughs?",
                    "Which companies are leading the field?"
                ]),
                ("Artificial General Intelligence progress", [
                    "What are the current limitations?",
                    "What are the major research directions?"
                ])
            ]
            
            # Create query configs
            query_configs = []
            for query, goals in test_queries:
                query_configs.append(QueryConfig(query=query, goals=goals))
            
            # Create research step
            step = Step(
                step_number=1, 
                query_configs=query_configs,
                settings=settings
            )
            
            # Create progress monitoring task
            async def monitor_progress():
                while step.state in [StepState.NONE, StepState.INITIALIZED, StepState.RUNNING]:
                    print("\nCurrent Progress:")
                    for job_id, job in step.jobs.items():
                        print(f"Job {job_id}:")
                        print(f"  State: {job.state.value}")
                        print(f"  Query: {job.query_config.query}")
                        if job.error_message:
                            print(f"  Error: {job.error_message}")
                    print()
                    await asyncio.sleep(0.2)
            
            # Run step and monitor progress concurrently
            progress_task = asyncio.create_task(monitor_progress())
            run_task = asyncio.create_task(step.run())
            
            # Wait for step to complete
            success = await run_task
            await progress_task  # Wait for final progress update
            
            if not success:
                print(f"Step failed: {step.error_message}")
                return
                
            # Get and print results
            results = step.get_results()
            if results:
                print("\nStep Results:")
                print(f"Number of jobs: {len(results.jobs_data)}")
                print("\nLearnings:")
                print(results.learnings)
            
        except Exception as e:
            print(f"Test failed with error: {str(e)}")
            raise
    
    # Run the test
    asyncio.run(test_research_step())
