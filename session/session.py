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
from session.research_session_configs import ResearchSession, ResearchResults

class SessionState(Enum):
    NONE = "none"
    INITIALIZED = "initialized"
    RESEARCHING = "researching"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class Session:
    research_input: ResearchInput
    settings: ResearchSettings
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
                
            self.session_data = ResearchSession(
                input_config=self.research_input,
                research_settings=self.settings
            )
            self.state = SessionState.INITIALIZED
            return True
        except Exception as e:
            self.state = SessionState.ERROR
            self.error_message = str(e)
            return False
            
    def research(self) -> bool:
        """Start the research process"""
        if self.state != SessionState.INITIALIZED:
            self.error_message = f"Cannot start research in state: {self.state}"
            return False
            
        try:
            self.state = SessionState.RESEARCHING
            # Research implementation
            return True
        except Exception as e:
            self.state = SessionState.ERROR
            self.error_message = str(e)
            return False
            
    def get_results(self) -> Optional[ResearchResults]:
        """Get the research results if available"""
        if self.session_data and self.session_data.final_results:
            return self.session_data.final_results
        return None
        
    def get_state(self) -> dict:
        """Get current session state information"""
        return {
            "state": self.state.value,
            "error": self.error_message if self.error_message else None,
            "has_results": bool(self.session_data and self.session_data.final_results)
        }
