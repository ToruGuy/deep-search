from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import sys

# Add parent directory to path for direct script execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from session.research_session_configs import StepData, ReaserchJobData, StepLearnings
    from session.job import Job, JobState
else:
    from .research_session_configs import StepData, ReaserchJobData, StepLearnings
    from .job import Job, JobState

class StepState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ResearchStep:
    step_number: int
    jobs: List[Job] = field(default_factory=list)
    state: StepState = StepState.NONE
    error_message: Optional[str] = None
    _executor: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(max_workers=5))
    
    def initialize(self) -> bool:
        """Initialize the research step"""
        try:
            if not self.jobs:
                self.error_message = "No jobs configured for the step"
                self.state = StepState.FAILED
                return False
                
            for job in self.jobs:
                if not job.initialize():
                    self.error_message = f"Failed to initialize job: {job.error_message}"
                    self.state = StepState.FAILED
                    return False
                    
            self.state = StepState.INITIALIZED
            return True
        except Exception as e:
            self.error_message = str(e)
            self.state = StepState.FAILED
            return False
            
    async def run_jobs(self):
        """Run all jobs concurrently"""
        if self.state != StepState.INITIALIZED:
            raise ValueError(f"Cannot run jobs in state: {self.state}")
            
        self.state = StepState.RUNNING
        
        try:
            # Create tasks for each job
            tasks = []
            for job in self.jobs:
                task = asyncio.create_task(self._run_job(job))
                tasks.append(task)
                
            # Wait for all jobs to complete
            await asyncio.gather(*tasks)
            
            # Check if any jobs failed
            if any(job.state == JobState.FAILED for job in self.jobs):
                self.state = StepState.FAILED
                self.error_message = "One or more jobs failed"
            else:
                self.state = StepState.COMPLETED
                
        except Exception as e:
            self.state = StepState.FAILED
            self.error_message = str(e)
            
    async def _run_job(self, job: Job):
        """Run a single job"""
        try:
            # Simulate job execution
            job.state = JobState.RUNNING
            # Add actual job execution logic here
            await asyncio.sleep(1)  # Placeholder for actual work
            job.state = JobState.COMPLETED
        except Exception as e:
            job.state = JobState.FAILED
            job.error_message = str(e)
            
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress of all jobs"""
        total_jobs = len(self.jobs)
        completed = sum(1 for job in self.jobs if job.state == JobState.COMPLETED)
        failed = sum(1 for job in self.jobs if job.state == JobState.FAILED)
        running = sum(1 for job in self.jobs if job.state == JobState.RUNNING)
        
        return {
            "total": total_jobs,
            "completed": completed,
            "failed": failed,
            "running": running,
            "progress_percentage": (completed + failed) / total_jobs * 100 if total_jobs > 0 else 0
        }
        
    def to_step_data(self) -> StepData:
        """Convert to StepData format"""
        step_data = StepData(step_number=self.step_number)
        
        for job in self.jobs:
            if job.state == JobState.COMPLETED:
                research_job = ReaserchJobData(
                    query_config=job.query_config,
                    exploration_results=job.exploration_results,
                    search_gradings=job.search_gradings
                )
                step_data.add_job(research_job)
                
        return step_data
