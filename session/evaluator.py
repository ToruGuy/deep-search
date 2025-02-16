from dataclasses import dataclass
from typing import List
import os
import sys

# Add parent directory to path for direct script execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from session.job import Job
else:
    from .job import Job

@dataclass
class Evaluator:
    """Evaluates research results from jobs"""
    
    def evaluate_jobs(self, jobs: List[Job]) -> dict:
        """Evaluate results from completed jobs"""
        # Implementation for evaluating job results
        return {}
    
    def aggregate_results(self, evaluation_results: List[dict]) -> dict:
        """Aggregate evaluation results into final output"""
        # Implementation for aggregating results
        return {}
