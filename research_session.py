from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from input_config import ResearchInput, ResearchSettings

@dataclass
class QueryConfig:
    """Configuration for a single query including its specific research goals"""
    query: str
    goals: List[str]

@dataclass
class WebExplorationResult:
    """Results from exploring web content for a specific query"""
    serp_results: List[Dict]
    web_extract: Dict
    query_results: List[Dict]
    success_rating: float  # 0-1 rating of how well this query achieved its goals

@dataclass
class QueryLearnings:
    """Learnings and insights gained from a specific query"""
    key_findings: List[str]
    suggested_follow_up_queries: List[QueryConfig]
    areas_to_explore: List[str]
    confidence_score: float

@dataclass
class ResearchJob:
    """A single research job that explores one query path"""
    query_config: QueryConfig
    exploration_results: WebExplorationResult
    learnings: QueryLearnings
    search_gradings: Dict

@dataclass
class StepData:
    """A research step that can contain multiple parallel research jobs"""
    step_number: int
    jobs: List[ResearchJob]
    step_summary: Optional[str] = None  # Summary of findings across all jobs in this step
    
    def add_job(self, job: ResearchJob):
        """Add a new research job to this step"""
        self.jobs.append(job)
    
    def get_successful_jobs(self, min_success_rating: float = 0.7) -> List[ResearchJob]:
        """Get jobs that were successful in achieving their goals"""
        return [
            job for job in self.jobs 
            if job.exploration_results.success_rating >= min_success_rating
        ]
    
    def get_all_findings(self) -> List[str]:
        """Get all key findings from all jobs in this step"""
        findings = []
        for job in self.jobs:
            findings.extend(job.learnings.key_findings)
        return findings

@dataclass
class ResearchResults:
    """Final consolidated results from the entire research session"""
    main_report: str
    key_learnings: List[Dict]  # List of key insights with supporting evidence
    additional_notes: List[str]

@dataclass
class ResearchSession:
    """Main container for all research-related data produced during a research run"""
    
    # Session metadata
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Input configuration
    input_config: ResearchInput
    research_settings: ResearchSettings = field(default_factory=lambda: ResearchSettings())
    
    def __post_init__(self):
        # Initialize research_settings from input_config if not provided
        if not self.research_settings:
            self.research_settings = self.input_config.settings
    
    # Research data
    steps: List[StepData] = field(default_factory=list)
    final_results: Optional[ResearchResults] = None
    
    def create_new_step(self) -> StepData:
        """Create a new research step"""
        step = StepData(step_number=len(self.steps), jobs=[])
        self.steps.append(step)
        return step
    
    def add_job_to_step(self, step_number: int, job: ResearchJob):
        """Add a research job to a specific step"""
        if step_number >= len(self.steps):
            raise ValueError(f"Step {step_number} does not exist")
        self.steps[step_number].add_job(job)
    
    def complete_session(self, results: ResearchResults):
        """Complete the session with final results"""
        self.final_results = results
        self.end_time = datetime.now()
    
    def get_all_successful_jobs(self, min_success_rating: float = 0.7) -> List[ResearchJob]:
        """Get all successful jobs across all steps"""
        successful_jobs = []
        for step in self.steps:
            successful_jobs.extend(step.get_successful_jobs(min_success_rating))
        return successful_jobs
    
    def get_step_progression(self) -> List[List[QueryConfig]]:
        """Get the progression of queries organized by steps"""
        return [
            [job.query_config for job in step.jobs]
            for step in self.steps
        ]
    
    def to_dict(self) -> Dict:
        """Convert the entire session to a dictionary for storage/serialization"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "input_config": self.input_config.to_dict(),
            "research_settings": self.research_settings.to_dict(),
            "steps": [
                {
                    "step_number": step.step_number,
                    "step_summary": step.step_summary,
                    "jobs": [
                        {
                            "query_config": {
                                "query": job.query_config.query,
                                "goals": job.query_config.goals
                            },
                            "exploration_results": {
                                "serp_results": job.exploration_results.serp_results,
                                "web_extract": job.exploration_results.web_extract,
                                "query_results": job.exploration_results.query_results,
                                "success_rating": job.exploration_results.success_rating
                            },
                            "learnings": {
                                "key_findings": job.learnings.key_findings,
                                "suggested_follow_up_queries": [
                                    {
                                        "query": q.query,
                                        "goals": q.goals
                                    } for q in job.learnings.suggested_follow_up_queries
                                ],
                                "areas_to_explore": job.learnings.areas_to_explore,
                                "confidence_score": job.learnings.confidence_score
                            },
                            "search_gradings": job.search_gradings
                        } for job in step.jobs
                    ]
                } for step in self.steps
            ],
            "final_results": {
                "main_report": self.final_results.main_report,
                "key_learnings": self.final_results.key_learnings,
                "additional_notes": self.final_results.additional_notes
            } if self.final_results else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ResearchSession":
        """Create a ResearchSession instance from a dictionary"""
        input_config = ResearchInput.from_dict(data["input_config"])
        research_settings = ResearchSettings(**data["research_settings"])
        session = cls(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            input_config=input_config,
            research_settings=research_settings
        )
        
        if data.get("end_time"):
            session.end_time = datetime.fromisoformat(data["end_time"])
        
        for step_data in data["steps"]:
            step = StepData(
                step_number=step_data["step_number"],
                jobs=[],
                step_summary=step_data.get("step_summary")
            )
            
            for job_data in step_data["jobs"]:
                job = ResearchJob(
                    query_config=QueryConfig(
                        query=job_data["query_config"]["query"],
                        goals=job_data["query_config"]["goals"]
                    ),
                    exploration_results=WebExplorationResult(
                        serp_results=job_data["exploration_results"]["serp_results"],
                        web_extract=job_data["exploration_results"]["web_extract"],
                        query_results=job_data["exploration_results"]["query_results"],
                        success_rating=job_data["exploration_results"]["success_rating"]
                    ),
                    learnings=QueryLearnings(
                        key_findings=job_data["learnings"]["key_findings"],
                        suggested_follow_up_queries=[
                            QueryConfig(
                                query=q["query"],
                                goals=q["goals"]
                            ) for q in job_data["learnings"]["suggested_follow_up_queries"]
                        ],
                        areas_to_explore=job_data["learnings"]["areas_to_explore"],
                        confidence_score=job_data["learnings"]["confidence_score"]
                    ),
                    search_gradings=job_data["search_gradings"]
                )
                step.add_job(job)
            
            session.steps.append(step)
        
        if data.get("final_results"):
            session.final_results = ResearchResults(
                main_report=data["final_results"]["main_report"],
                key_learnings=data["final_results"]["key_learnings"],
                additional_notes=data["final_results"]["additional_notes"]
            )
        
        return session
