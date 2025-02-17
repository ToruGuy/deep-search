from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import os
import sys

# Add the root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from input_config import ResearchInput, ResearchSettings
from session.research_session_configs import ResearchSession, ResearchResults, QueryConfig
from session.researcher import Researcher
from session.research_step import ResearchStep, ResearchStepState
from loguru import logger

class SessionState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RESEARCHING = "researching"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class Session:
    research_input: ResearchInput
    state: SessionState = SessionState.NONE
    session_data: Optional[ResearchSession] = None
    error_message: Optional[str] = None
    
    def initialize(self) -> bool:
        """Initialize the research session"""
        try:
            if not self.research_input.validate():
                self.state = SessionState.ERROR
                self.error_message = "Invalid research input"
                return False
                
            # Generate a unique session ID using timestamp
            from datetime import datetime
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.session_data = ResearchSession(session_id=session_id)
            self.state = SessionState.INITIALIZED
            return True
        except Exception as e:
            self.state = SessionState.ERROR
            self.error_message = str(e)
            return False
            
    async def research(self) -> bool:
        """Start the research process"""
        if self.state != SessionState.INITIALIZED:
            logger.error("Cannot start research - session not initialized")
            return False
            
        try:
            self.state = SessionState.RESEARCHING
            researcher = Researcher(
                api_key=self.research_input.settings.openai_api_key,
                breath=self.research_input.settings.max_depth
            )
            
            # Initialize first research step
            research_step = ResearchStep(step_number=1)
            if not research_step.initialize():
                raise Exception("Failed to initialize research step")
                
            # Generate queries for the first step
            queries = researcher.create_queries(
                self.research_input.query_topic
            )
            logger.info("Step 1 queries: {}", queries)
            
            # Add queries as jobs to the research step
            for query in queries:
                research_step.add_job(query)
                
            # Run the research step
            if not await research_step.run():
                raise Exception("Research step failed")
                
            # Get results
            step_data = research_step.get_results()
            logger.debug("Step data: {}", step_data)
            
            self.state = SessionState.COMPLETED
            return True
            
        except Exception as e:
            self.state = SessionState.ERROR
            self.error_message = str(e)
            logger.error("Research failed: {}", str(e))
            return False
            
    def get_status(self) -> dict:
        """Get the current status of the research session"""
        return {
            "state": self.state.value,
            "error": self.error_message if self.error_message else None,
            "has_results": bool(self.session_data and self.session_data.final_results)
        }

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    from input_config import ResearchInput, ResearchSettings
    
    # Load environment variables
    load_dotenv()
    
    # Create example research input with settings including OpenAI key
    research_input = ResearchInput(
        query_topic="Latest developments in artificial intelligence and their societal impact",
        settings=ResearchSettings(
            max_depth=1,
            search_timeout=300,
            max_results=50,
            include_academic_sources=True,
            language="en",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    )
    
    # Create and initialize session
    session = Session(research_input=research_input)
    
    print("Initializing research session...")
    if not session.initialize():
        print(f"Session initialization failed: {session.error_message}")
        exit(1)
    
    import asyncio
    print("\nStarting research process...")
    if not asyncio.run(session.research()):
        print(f"Research process failed: {session.error_message}")
        exit(1)
    
    print("\nResearch completed successfully!")
