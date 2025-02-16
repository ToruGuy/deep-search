from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import os
import sys
from datetime import datetime
from loguru import logger

# Add the root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Use absolute imports when running as script
if __name__ == "__main__":
    from session.job import Job, JobState
    from session.research_session_configs import (
        QueryConfig,
        WebExplorationResult,
        SearchGrading,
        ReaserchJobData,
        StepData,
        StepLearnings
    )
else:
    # Use relative imports when imported as module
    from .job import Job, JobState
    from .research_session_configs import (
        QueryConfig,
        WebExplorationResult,
        SearchGrading,
        ReaserchJobData,
        StepData,
        StepLearnings
    )

class ResearchStepState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ResearchStep:
    """A research step that manages multiple jobs and aggregates their results"""
    
    step_number: int
    state: ResearchStepState = ResearchStepState.NONE
    jobs: Dict[str, Job] = field(default_factory=dict)  # Map of job_id to Job
    step_data: Optional[StepData] = None
    error_message: Optional[str] = None
    
    def initialize(self) -> bool:
        """Initialize the research step"""
        logger.info(f"Initializing research step {self.step_number}")
        try:
            self.step_data = StepData(step_number=self.step_number)
            self.state = ResearchStepState.INITIALIZED
            logger.debug("Research step initialized successfully")
            return True
        except Exception as e:
            self.error_message = str(e)
            self.state = ResearchStepState.FAILED
            logger.error(f"Research step initialization failed: {self.error_message}")
            return False
    
    def add_job(self, query_config: QueryConfig) -> Optional[str]:
        """Add a new job to the research step. Returns job_id if successful, None otherwise."""
        logger.info(f"Adding new job with query: {query_config.query}")
        try:
            job = Job(query_config=query_config)
            self.jobs[job.job_id] = job
            logger.debug(f"Job {job.job_id} added successfully. Total jobs: {len(self.jobs)}")
            return job.job_id
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Failed to add job: {self.error_message}")
            return None
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by its ID"""
        return self.jobs.get(job_id)
    
    async def _run_job(self, job_id: str, job: Job) -> None:
        """Run a single job and add its results to step data if successful"""
        logger.debug(f"Processing job {job_id}")
        if not job.initialize():
            logger.warning(f"Job {job_id} initialization failed: {job.error_message}")
            return

        if not await job.run():
            logger.warning(f"Job {job_id} execution failed: {job.error_message}")
            return

        # Add successful job results to step data
        if job.state == JobState.COMPLETED:
            job_results = job.get_results()
            self.step_data.add_job(job_results)
            logger.debug(f"Added results from job {job_id}: {job_results.query_config.query}")

    async def run(self) -> bool:
        """Run all jobs in the research step concurrently"""
        if self.state != ResearchStepState.INITIALIZED:
            self.error_message = f"Cannot run step in state: {self.state}"
            logger.error(f"Cannot run step: {self.error_message}")
            return False
        
        if not self.jobs:
            self.error_message = "No jobs to run"
            logger.error(f"Cannot run step: {self.error_message}")
            return False
        
        logger.info(f"Running research step {self.step_number} with {len(self.jobs)} jobs concurrently")
        self.state = ResearchStepState.RUNNING
        
        try:
            # Run all jobs concurrently
            await asyncio.gather(*[
                self._run_job(job_id, job) 
                for job_id, job in self.jobs.items()
            ])
            
            # Check if we have any successful jobs
            successful_jobs = self.step_data.get_successful_jobs()
            if not successful_jobs:
                self.error_message = "No jobs completed successfully"
                self.state = ResearchStepState.FAILED
                logger.error(f"Research step failed: {self.error_message}")
                return False
            
            # Create step learnings from successful jobs
            self._create_step_learnings()
            
            self.state = ResearchStepState.COMPLETED
            logger.info(f"Research step {self.step_number} completed successfully")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.state = ResearchStepState.FAILED
            logger.error(f"Research step failed: {self.error_message}")
            return False
    
    def _create_step_learnings(self):
        """Create step learnings from successful jobs"""
        logger.debug("Creating step learnings")
        successful_jobs = self.step_data.get_successful_jobs()
        
        # Combine all web extraction results
        all_findings = []
        total_confidence = 0.0
        
        for job_data in successful_jobs:
            if job_data.exploration_results and job_data.exploration_results.web_extract_results:
                # Add all extracted information
                all_findings.append(f"Query: {job_data.query_config.query}")
                for goal_num, goal in enumerate(job_data.query_config.goals, 1):
                    answer = job_data.exploration_results.web_extract_results.get(f"goal{goal_num}")
                    if answer:
                        all_findings.append(f"- {goal}: {answer}")
                all_findings.append("")  # Add blank line between jobs
                
                # Add to confidence
                total_confidence += job_data.exploration_results.success_rating
        
        # Calculate average confidence
        avg_confidence = total_confidence / len(successful_jobs) if successful_jobs else 0.0
        
        # Create step learnings with combined knowledge
        self.step_data.step_learnings = StepLearnings(
            key_findings=all_findings,
            areas_to_explore=[],  # Simplified: not tracking separately
            confidence_score=avg_confidence,
            suggested_queries=[]  # Simplified: not tracking separately
        )
        logger.debug("Step learnings created successfully")
    
    def get_results(self) -> StepData:
        """Get the research step results"""
        logger.debug(f"Retrieving results for step {self.step_number}")
        return self.step_data

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    async def test_research_step():
        # Load environment variables
        load_dotenv()
        
        # Create a test research step
        step = ResearchStep(step_number=1)
        
        # Initialize step
        print("Initializing research step...")
        if not step.initialize():
            print(f"Step initialization failed: {step.error_message}")
            return False
        
        # Add test jobs
        test_queries = [
            ("What are the latest AI breakthroughs?", [
                "What are the most significant AI developments in the past year?",
                "Which companies are leading AI innovation?",
                "What are the practical applications of these breakthroughs?"
            ]),
            ("AI impact on society", [
                "How is AI affecting employment?",
                "What are the ethical concerns with AI?",
                "What are the positive social impacts of AI?"
            ])
        ]
        
        job_ids = []  # Keep track of job IDs
        for query, goals in test_queries:
            query_config = QueryConfig(query=query, goals=goals)
            job_id = step.add_job(query_config)
            if job_id:
                job_ids.append(job_id)
                print(f"Added job {job_id} with query: {query}")
            else:
                print(f"Failed to add job: {step.error_message}")
                return False
        
        # Run the step
        print(f"\nRunning research step with {len(job_ids)} jobs...")
        if not await step.run():
            print(f"Step execution failed: {step.error_message}")
            return False
        
        # Get and print results
        results = step.get_results()
        print("\nStep Results:")
        print(f"Number of successful jobs: {len(results.get_successful_jobs())}")
        
        if results.step_learnings:
            print("\nStep Learnings:")
            print("Key Findings:")
            for finding in results.step_learnings.key_findings:
                print(f"{finding}")
            
            print("\nAreas to Explore:")
            for area in results.step_learnings.areas_to_explore:
                print(f"{area}")
            
            print(f"\nConfidence Score: {results.step_learnings.confidence_score:.2f}")
            
            print("\nSuggested Queries:")
            for query in results.step_learnings.suggested_queries:
                print(f"{query}")
        
        return True
    
    # Run the test
    asyncio.run(test_research_step())
