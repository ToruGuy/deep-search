from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class ResearchSettings:
    max_depth: int = 3
    search_timeout: int = 300  # in seconds
    max_results: int = 50
    include_web_content: bool = True
    include_news: bool = True
    include_discussions: bool = True
    language: str = "en"
    openai_api_key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to a dictionary."""
        return {
            "max_depth": self.max_depth,
            "search_timeout": self.search_timeout,
            "max_results": self.max_results,
            "include_web_content": self.include_web_content,
            "language": self.language,
            "openai_api_key": self.openai_api_key
        }
    
@dataclass
class ResearchInput:
    query_topic: str
    settings: ResearchSettings = field(default_factory=ResearchSettings)
    
    def validate(self) -> bool:
        """Validate the research input parameters."""
        if not self.query_topic or not isinstance(self.query_topic, str):
            return False
        if not isinstance(self.settings, ResearchSettings):
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert the research input to a dictionary."""
        return {
            "query_topic": self.query_topic,
            "settings": self.settings.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchInput':
        """Create a ResearchInput instance from a dictionary."""
        settings = ResearchSettings(**data.get('settings', {}))
        return cls(
            query_topic=data['query_topic'],
            settings=settings
        )