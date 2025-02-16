from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class QueryConfig:
    """Configuration for a specific research query"""
    query: str
    goals: List[str]

@dataclass
class WebExplorationResult:
    """Results from web exploration for a specific query"""
    serp_results: List[Dict]
    web_extract_results: str
    success_rating: float

@dataclass 
class SearchGrading:
    """Grading structure for search results"""
    relevance_score: float
    coverage_score: float
    depth_score: float
    source_quality: float
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relevance_score": self.relevance_score,
            "coverage_score": self.coverage_score,
            "depth_score": self.depth_score,
            "source_quality": self.source_quality,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchGrading':
        return cls(**data)

@dataclass
class StepLearnings:
    """Aggregated learnings and insights for a research step"""
    key_findings: List[str]
    areas_to_explore: List[str]
    confidence_score: float
    suggested_queries: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_findings": self.key_findings,
            "areas_to_explore": self.areas_to_explore,
            "confidence_score": self.confidence_score,
            "suggested_queries": self.suggested_queries
        }

@dataclass
class ReaserchJobData:
    """A single research job within a step"""
    query_config: QueryConfig
    exploration_results: WebExplorationResult
    learnings: Dict[str, Any]
    search_gradings: SearchGrading

@dataclass
class StepData:
    """Data for a single research step"""
    step_number: int
    jobs: List[ReaserchJobData] = field(default_factory=list)
    step_summary: Optional[str] = None
    step_learnings: Optional[StepLearnings] = None
    
    def add_job(self, job: ReaserchJobData):
        """Add a job to this step"""
        self.jobs.append(job)
    
    def get_successful_jobs(self, min_success_rating: float = 0.7) -> List[ReaserchJobData]:
        """Get jobs that meet the minimum success rating"""
        return [
            job for job in self.jobs 
            if job.exploration_results.success_rating >= min_success_rating
        ]

@dataclass
class ResearchResults:
    """Final results of the research session"""
    main_report: str
    key_learnings: List[str]
    visited_sources: List[Dict[str, Any]]  # List of sources with metadata like quality, relevance
    areas_covered: List[str]  # Areas that were thoroughly researched
    areas_to_explore: List[str]  # Areas identified for further research
    best_sources: List[Dict[str, Any]]  # Top sources with high quality scores
    additional_notes: Optional[str] = None

@dataclass
class ResearchSession:
    """Main container for all research-related data produced during a research run"""
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    steps: List[StepData] = field(default_factory=list)
    final_results: Optional[ResearchResults] = None
    
    def create_new_step(self) -> StepData:
        """Create a new research step"""
        step = StepData(step_number=len(self.steps), jobs=[])
        self.steps.append(step)
        return step
    
    def add_job_to_step(self, step_number: int, job: ReaserchJobData):
        """Add a research job to a specific step"""
        if step_number >= len(self.steps):
            raise ValueError(f"Step {step_number} does not exist")
        self.steps[step_number].add_job(job)
    
    def complete_session(self, results: ResearchResults):
        """Complete the session with final results"""
        self.final_results = results
        self.end_time = datetime.now()
    
    def get_all_successful_jobs(self, min_success_rating: float = 0.7) -> List[ReaserchJobData]:
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
            "steps": [
                {
                    "step_number": step.step_number,
                    "step_summary": step.step_summary,
                    "step_learnings": step.step_learnings.to_dict() if step.step_learnings else None,
                    "jobs": [
                        {
                            "query_config": {
                                "query": job.query_config.query,
                                "goals": job.query_config.goals
                            },
                            "exploration_results": {
                                "serp_results": job.exploration_results.serp_results,
                                "web_extract_results": job.exploration_results.web_extract_results,
                                "success_rating": job.exploration_results.success_rating
                            },
                            "learnings": job.learnings,
                            "search_gradings": job.search_gradings.to_dict()
                        } for job in step.jobs
                    ]
                } for step in self.steps
            ],
            "final_results": {
                "main_report": self.final_results.main_report,
                "key_learnings": self.final_results.key_learnings,
                "visited_sources": self.final_results.visited_sources,
                "areas_covered": self.final_results.areas_covered,
                "areas_to_explore": self.final_results.areas_to_explore,
                "best_sources": self.final_results.best_sources,
                "additional_notes": self.final_results.additional_notes
            } if self.final_results else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ResearchSession":
        """Create a ResearchSession instance from a dictionary"""
        session = cls(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
        )
        
        if data.get("end_time"):
            session.end_time = datetime.fromisoformat(data["end_time"])
        
        for step_data in data["steps"]:
            step = StepData(
                step_number=step_data["step_number"],
                jobs=[],
                step_summary=step_data.get("step_summary"),
                step_learnings=StepLearnings.from_dict(step_data["step_learnings"]) if step_data.get("step_learnings") else None
            )
            
            for job_data in step_data["jobs"]:
                job = ReaserchJobData(
                    query_config=QueryConfig(
                        query=job_data["query_config"]["query"],
                        goals=job_data["query_config"]["goals"]
                    ),
                    exploration_results=WebExplorationResult(
                        serp_results=job_data["exploration_results"]["serp_results"],
                        web_extract_results=job_data["exploration_results"]["web_extract_results"],
                        success_rating=job_data["exploration_results"]["success_rating"]
                    ),
                    learnings=job_data["learnings"],
                    search_gradings=SearchGrading.from_dict(job_data["search_gradings"])
                )
                step.add_job(job)
            
            session.steps.append(step)
        
        if data.get("final_results"):
            session.final_results = ResearchResults(
                main_report=data["final_results"]["main_report"],
                key_learnings=data["final_results"]["key_learnings"],
                visited_sources=data["final_results"]["visited_sources"],
                areas_covered=data["final_results"]["areas_covered"],
                areas_to_explore=data["final_results"]["areas_to_explore"],
                best_sources=data["final_results"]["best_sources"],
                additional_notes=data["final_results"]["additional_notes"]
            )
        
        return session
