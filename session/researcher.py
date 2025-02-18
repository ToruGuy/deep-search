from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import os
import sys
from datetime import datetime
from openai import OpenAI
from pydantic import BaseModel, field_validator
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="DEBUG")

# Add parent directory to path for direct script execution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from session.job import Job, QueryConfig

@dataclass
class ResearchResults:
    """Final results of the research session"""
    main_report: str
    key_learnings: List[str]
    # visited_sources: List[Dict[str, Any]]  # List of sources with metadata like quality, relevance
    areas_covered: List[str]  # Areas that were thoroughly researched
    areas_to_explore: List[str]  # Areas identified for further research
    # best_sources: List[Dict[str, Any]]  # Top sources with high quality scores
    additional_notes: Optional[str] = None

class ResearchReport(BaseModel):
    """Schema for research report validation"""
    main_report: str
    key_learnings: List[str]
    areas_covered: List[str]
    areas_to_explore: List[str]
    
    @field_validator('key_learnings', 'areas_covered', 'areas_to_explore')
    @classmethod
    def validate_list_length(cls, v: List[str]) -> List[str]:
        """Ensure lists are not empty"""
        if not v:
            return []
        return v

class ResearchJob(BaseModel):
    """Single research job configuration"""
    query: str
    goals: List[str]
    
    @field_validator('goals')
    @classmethod
    def validate_goals_length(cls, v: List[str]) -> List[str]:
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
        self.query_prompt = self._get_query_prompt()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt with current timestamp"""
        now = datetime.now().isoformat()
        logger.debug("Generating system prompt with timestamp: {}", now)
        return f"""You are an expert researcher. Today is {now}. Follow these instructions when responding:
  - You may be asked to research subjects that is after your knowledge cutoff, assume the user is right when presented with news.
  - The user is a highly experienced analyst, no need to simplify it, be as detailed as possible and make sure your response is correct.
  - Be highly organized.
  - Suggest solutions that I didn't think about.
  - Be proactive and anticipate my needs.
  - Treat me as an expert in all subject matter.
  - Mistakes erode my trust, so be accurate and thorough.
  - Provide detailed explanations, I'm comfortable with lots of detail.
  - Value good arguments over authorities, the source is irrelevant.
  - Consider new technologies and contrarian ideas, not just the conventional wisdom.
  - You may use high levels of speculation or prediction, just flag it for me."""
    
    def _get_query_prompt(self) -> str:
        """Get the query generation prompt"""
        return """For each research topic, you will generate:
1. SERP-Optimized Search Query:
   - Use natural language that matches common search patterns
   - Include specific keywords and terms that will rank well in search results
   - Keep it concise but informative
   - Focus on getting high-quality, relevant search results
   - Avoid complex operators or special characters

2. Research Goals for AI Extraction (2-4 goals):
   - Provide detailed, specific data points to extract
   - Include numerical metrics, dates, and measurable outcomes
   - Specify relationships between entities and technical details
   - Focus on key trends, comparisons, and practical implementations"""
    
    def create_queries(self, main_goal: str, learnings: List[str] = None) -> List[QueryConfig]:
        """Create a set of research queries based on the main goal and previous learnings."""
        learnings = learnings or []
        logger.debug("Creating queries for goal: '{}' with {} previous learnings", 
                    main_goal, len(learnings))
        
        try:
            completion = self.client.beta.chat.completions.parse(
                model="o3-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"{self.query_prompt}\n\nBased on the main research goal: '{main_goal}'\nPrevious learnings: {learnings if learnings else 'None'}\nGenerate {self.breath} research queries with their corresponding extraction goals.\nEach query should explore a different aspect of the main goal.\nImportant: Provide exactly 4 or fewer specific goals for each query."}
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
            logger.error(f"Failed to create queries: {e}")
            # Return a basic query config as fallback
            return [QueryConfig(
                query=main_goal,
                goals=["Extract key findings and results", "Identify main conclusions"]
            )]
    
    def write_report(self, learnings: List[str]) -> ResearchResults:
        """Generate a comprehensive report based on all gathered learnings"""
        logger.debug("Writing report based on {} learnings", len(learnings))
        try:
            completion = self.client.beta.chat.completions.parse(
                model="o3-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"""Based on the following research findings, create a comprehensive research report:

Research Findings:
{chr(10).join(f'- {learning}' for learning in learnings)}

Create a professional research report with the following sections:

1. main_report: Write this as a formal research report with these components:
   - Executive Summary: Brief overview of key findings and implications
   - Background: Context and importance of the research topic
   - Methodology: How the research was conducted
   - Key Findings: Detailed analysis of discoveries, supported by data
   - Implications: What these findings mean for the field
   - Future Outlook: Predicted developments and trends
   Use proper formatting with headers and maintain a professional tone.

2. key_learnings: List specific, actionable insights that emerged from the research:
   - Focus on concrete, verifiable findings
   - Include metrics and data points where available
   - Highlight unexpected discoveries
   - Note significant trends and patterns

3. areas_covered: List the main areas that were thoroughly researched:
   - Technical aspects explored
   - Market segments analyzed
   - Methodologies examined
   - Time periods covered

4. areas_to_explore: Identify promising areas for further research:
   - Knowledge gaps discovered
   - Emerging trends requiring more investigation
   - Potential future developments to monitor
   - Questions raised by current findings

Important:
- Be thorough and detailed in your analysis
- Support claims with data from the findings
- Maintain a professional, academic tone
- Focus on actionable insights and implications
- Flag any speculative conclusions clearly"""}
                ],
                response_format=ResearchReport
            )
            
            result = completion.choices[0].message.parsed
            return ResearchResults(
                main_report=result.main_report,
                key_learnings=result.key_learnings,
                areas_covered=result.areas_covered,
                areas_to_explore=result.areas_to_explore,
                additional_notes="Report generated from research findings"
            )
            
        except Exception as e:
            logger.error(f"Failed to write report: {e}")
            return ResearchResults(
                main_report="Failed to generate report",
                key_learnings=learnings,
                areas_covered=[],
                areas_to_explore=[],
                additional_notes=f"Error during report generation: {str(e)}"
            )

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
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
    print("\nTesting write_report:")
    test_learnings = [
        "GPT-4 has demonstrated unprecedented capabilities in coding, showing 90% success rate in complex programming tasks",
        "New breakthrough: Google's Gemini Ultra achieved human-expert level performance across 57 subjects",
        "Microsoft and OpenAI partnership led to significant cost reduction in AI model training, reported 40% efficiency gain",
        "Anthropic's Claude 3 showed remarkable improvement in reasoning and safety, reducing hallucinations by 80%",
        "Meta's LLAMA 3 open-source model matched proprietary models while using 50% less compute power"
    ]
    
    report = researcher.write_report(test_learnings)
    print("\nGenerated Research Report:")
    print("\nMain Report:")
    print(report.main_report)
    print("\nKey Learnings:")
    for learning in report.key_learnings:
        print(f"- {learning}")
    print("\nAreas Covered:")
    for area in report.areas_covered:
        print(f"- {area}")
    print("\nAreas to Explore:")
    for area in report.areas_to_explore:
        print(f"- {area}")
    print("\nAdditional Notes:")
    print(report.additional_notes)
