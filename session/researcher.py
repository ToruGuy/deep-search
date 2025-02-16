from dataclasses import dataclass
from typing import List, Optional
import os
import sys

# Add parent directory to path for direct script execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from session.job import Job
else:
    from .job import Job

@dataclass
class Researcher:
    """Handles the research process and job management"""
    
    def create_jobs(self, query: str) -> List[Job]:
        """Create jobs based on the input query"""
        # Implementation for creating jobs
        return []
    
    def process_jobs(self, jobs: List[Job]):
        """Process a list of jobs"""
        for job in jobs:
            job.process()
            
    def analyze_results(self, jobs: List[Job]) -> dict:
        """Analyze results from completed jobs"""
        # Implementation for analyzing results
        return {}
