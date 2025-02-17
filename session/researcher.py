from dataclasses import dataclass
from typing import List, Optional
import os
import sys
from datetime import datetime
from openai import OpenAI
from pydantic import BaseModel, validator
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="DEBUG")

# Add parent directory to path for direct script execution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from session.job import Job
from session.research_session_configs import QueryConfig

class ResearchJob(BaseModel):
    """Single research job configuration"""
    query: str
    goals: List[str]

    @validator('goals')
    def validate_goals_length(cls, v):
        """Ensure goals list doesn't exceed 4 items"""
        if len(v) > 4:
            logger.warning(f"Truncating goals list from {len(v)} to 4 items")
            return v[:4]
        return v

class ResearchJobs(BaseModel):
    """Collection of research jobs"""
    jobs: List[ResearchJob]

@dataclass
class Researcher:
    """Handles the research process and job management"""
    api_key: str
    breath: int = 3  # Default number of queries to generate
    
    def __post_init__(self):
        """Initialize OpenAI client and load system prompt"""
        logger.debug("Initializing Researcher with breath={}", self.breath)
        self.client = OpenAI(api_key=self.api_key)
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt with current timestamp"""
        now = datetime.now().isoformat()
        logger.debug("Generating system prompt with timestamp: {}", now)
        return f"""You are an expert researcher specializing in creating effective search queries and extraction goals. Actual date is {now}.
For each research topic, you will generate:
1. SERP-Optimized Search Query:
   - Use natural language that matches common search patterns
   - Include specific keywords and terms that will rank well in search results
   - Keep it concise but informative
   - Focus on getting high-quality, relevant search results
   - Avoid complex operators or special characters

2. Research Goals for AI Extraction (maximum 4 goals):
   - Provide detailed, specific data points to extract
   - Include numerical metrics, dates, and measurable outcomes
   - Specify relationships between entities and technical details
   - Focus on key trends, comparisons, and practical implementations"""
    
    def create_queries(self, main_goal: str, learnings: List[str] = None) -> List[QueryConfig]:
        """Create a set of research queries based on the main goal and previous learnings.
        Returns a list of QueryConfig objects, each containing:
        - query: SERP-optimized search query for browser search
        - goals: Detailed extraction goals for AI to process the search results (max 4)
        """
        learnings = learnings or []
        logger.debug("Creating queries for goal: '{}' with {} previous learnings", 
                    main_goal, len(learnings))
        
        try:
            completion = self.client.beta.chat.completions.parse(
                model="o3-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"""Based on the main research goal: '{main_goal}'
Previous learnings: {learnings if learnings else 'None'}
Generate {self.breath} research queries with their corresponding extraction goals.
Each query should explore a different aspect of the main goal.
Important: Provide exactly 4 or fewer specific goals for each query."""}
                ],
                response_format=ResearchJobs
            )
            
            result = completion.choices[0].message.parsed
            logger.debug("Generated {} research jobs", len(result.jobs))
            return [QueryConfig(
                query=job.query,
                goals=job.goals
            ) for job in result.jobs]
        except Exception as e:
            logger.error("Error generating queries: {}", str(e))
            return [QueryConfig(
                query=main_goal,
                goals=[f"Error generating queries: {str(e)}"]
            )]
    
    def write_report(self, learnings: List[str]) -> str:
        """Generate a comprehensive report based on all gathered learnings"""
        logger.debug("Writing report based on {} learnings", len(learnings))
        try:
            response = self.client.chat.completions.create(
                model="o3-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Based on the following research findings, write a comprehensive report:\nFindings:\n{chr(10).join(f'- {learning}' for learning in learnings)}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = f"Error generating report: {str(e)}"
            logger.error(error_msg)
            return error_msg

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

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        sys.exit(1)
    
    # Initialize researcher
    researcher = Researcher(api_key=api_key, breath=3)
    
    # Test create_queries
    print("\nTesting create_queries:")
    main_goal = "What are the latest AI breakthroughs?"
    query_configs = researcher.create_queries(main_goal)
    print("Generated Query Configurations:")
    for i, config in enumerate(query_configs, 1):
        print(f"\n{i}. Query: {config.query}")
        print("   Goals:")
        for goal in config.goals:
            print(f"   - {goal}")
    
    # Test write_report
    # print("\nTesting write_report:")
    # test_learnings = [
    #     "GPT-4 has shown remarkable improvements in reasoning capabilities",
    #     "New breakthrough in quantum computing achieved 1000 qubit milestone",
    #     "Advanced AI models now capable of generating and executing code"
    # ]
    # report = researcher.write_report(test_learnings)
    # print("\nGenerated Report:")
    # print(report)
