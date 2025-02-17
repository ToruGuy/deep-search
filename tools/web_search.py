from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
import requests
import time
import os
import sys
from enum import Enum
from dotenv import load_dotenv
from loguru import logger

class Freshness(str, Enum):
    PAST_DAY = "pd"
    PAST_WEEK = "pw"
    PAST_MONTH = "pm"
    PAST_YEAR = "py"
    ANY = None

class SafeSearch(str, Enum):
    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"

class ResultType(str, Enum):
    DISCUSSIONS = "discussions"
    FAQ = "faq"
    INFOBOX = "infobox"
    NEWS = "news"
    QUERY = "query"
    SUMMARIZER = "summarizer"
    VIDEOS = "videos"
    WEB = "web"
    LOCATIONS = "locations"

class Units(str, Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"

@dataclass
class SearchOptions:
    """Configuration for Brave Search API"""
    # Required
    query: str
    
    # Optional parameters with defaults
    count: int = 20
    offset: int = 0
    country: str = "US"
    search_lang: str = "en"
    ui_lang: str = "en-US"
    safesearch: SafeSearch = SafeSearch.OFF
    freshness: Optional[Freshness] = None
    text_decorations: bool = True
    spellcheck: bool = True
    result_filter: Optional[List[ResultType]] = None
    goggles: Optional[str] = None
    units: Optional[Units] = None
    extra_snippets: bool = True
    summary: bool = False

    def to_api_params(self) -> Dict[str, Any]:
        """Convert options to API parameters"""
        params = {
            'q': self.query,
            'count': min(self.count, 20),  # API max limit is 20
            'offset': min(self.offset, 9),  # API max limit is 9
            'country': self.country,
            'search_lang': self.search_lang,
            'ui_lang': self.ui_lang,
            'safesearch': self.safesearch,
            'text_decorations': self.text_decorations,
            'spellcheck': self.spellcheck,
            'extra_snippets': self.extra_snippets,
            'summary': self.summary
        }
        
        # Add optional parameters only if they are set
        if self.freshness:
            params['freshness'] = self.freshness
        if self.result_filter:
            params['result_filter'] = ','.join([rf.value for rf in self.result_filter])
        if self.goggles:
            params['goggles'] = self.goggles
        if self.units:
            params['units'] = self.units
            
        return params

@dataclass
class BraveSearchResult:
    """Represents a single search result from any result type"""
    title: str
    url: str
    description: str
    result_type: ResultType
    page_age: Optional[str] = None
    extra_snippets: Optional[List[str]] = None
    source_type: Optional[str] = None
    summary: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None  # Store additional type-specific data

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format"""
        return {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "result_type": self.result_type.value,
            "page_age": self.page_age,
            "extra_snippets": self.extra_snippets,
            "source_type": self.source_type,
            "summary": self.summary,
            "meta": self.meta
        }

class BraveSearchResponse:
    """Represents the complete search response"""
    def __init__(self, data: Dict[str, Any]):
        self.query: Dict[str, Any] = data.get('query', {})
        self.results: List[BraveSearchResult] = []
        self._parse_results(data)
        
    def _parse_results(self, data: Dict[str, Any]) -> None:
        """Parse different types of results from the response"""
        result_types = {
            'web': ResultType.WEB,
            'news': ResultType.NEWS,
            'discussions': ResultType.DISCUSSIONS,
            'videos': ResultType.VIDEOS,
            'faq': ResultType.FAQ,
            'locations': ResultType.LOCATIONS
        }
        
        for result_key, result_type in result_types.items():
            if result_key in data:
                results = data[result_key].get('results', [])
                for result in results:
                    self.results.append(BraveSearchResult(
                        title=result['title'],
                        url=result['url'],
                        description=result.get('description', ''),
                        result_type=result_type,
                        page_age=result.get('page_age'),
                        extra_snippets=result.get('extra_snippets'),
                        source_type=result.get('source_type') or result.get('type'),
                        summary=result.get('summary'),
                        meta=result  # Store full result data for type-specific processing
                    ))

class BraveSearchClient:
    """Client for interacting with Brave Search API"""
    
    def __init__(self, api_key: str):
        """Initialize BraveSearchClient with required API key.
        
        Args:
            api_key (str): Brave Search API key
            
        Raises:
            ValueError: If api_key is not provided
        """
        if not api_key:
            raise ValueError("Brave Search API key must be provided")
            
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        self.last_request_time = 0
        self.min_request_interval = 1.1  # 1.1 seconds to be safe
        
    async def _delay(self, seconds: float) -> None:
        """Delay execution for specified number of seconds"""
        logger.debug(f"Delaying execution for {seconds} seconds")
        time.sleep(seconds)
        
    async def _wait_for_rate_limit(self) -> None:
        """Ensure we don't exceed rate limits"""
        now = time.time()
        time_since_last_request = now - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            logger.debug(f"Waiting for rate limit: {wait_time} seconds")
            await self._delay(wait_time)
            
        self.last_request_time = time.time()
        
    async def search(
        self, 
        options: SearchOptions
    ) -> BraveSearchResponse:
        """
        Perform a web search using Brave Search API
        
        Args:
            options: SearchOptions for customizing the search
            
        Returns:
            BraveSearchResponse object
            
        Raises:
            requests.RequestException: If the API request fails
        """
        logger.info(f"Performing search for query: {options.query}")
        
        try:
            await self._wait_for_rate_limit()
            
            params = options.to_api_params()
            
            logger.debug(f"Making API request to Brave Search with params: {params}")
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            logger.debug("Successfully received response from Brave Search API")
            
            return BraveSearchResponse(data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to perform search: {str(e)}")
            if e.response is not None and e.response.status_code == 429:
                logger.warning("Rate limit exceeded, waiting before retry")
                await self._delay(5)  # Wait 5 seconds before retry
                return await self.search(options)
            raise


def print_result(result: BraveSearchResult):
    """Print all available information for a search result"""
    print("\n" + "="*80)
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Type: {result.result_type.value}")
    print(f"Description: {result.description}")
    
    if result.page_age:
        print(f"Page Age: {result.page_age}")
    if result.source_type:
        print(f"Source Type: {result.source_type}")
    if result.summary:
        print(f"Summary: {result.summary}")
    if result.extra_snippets:
        print("\nExtra Snippets:")
        for snippet in result.extra_snippets:
            print(f"  - {snippet}")
    if result.meta:
        print("\nAdditional Metadata:")
        for key, value in result.meta.items():
            if key not in ['title', 'url', 'description', 'page_age', 'source_type', 'summary', 'extra_snippets']:
                print(f"  {key}: {value}")


async def test_search():
    """Test the BraveSearchClient with various configurations"""
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv('BRAVE_API_KEY')
    if not api_key:
        logger.error("API key not found in environment variables")
        raise ValueError("API key must be provided or set in BRAVE_API_KEY environment variable")
    
    client = BraveSearchClient(api_key)
    
    # Test basic web search
    print("\nBASIC WEB SEARCH")
    print("="*80)
    options = SearchOptions(
        query="Python programming best practices",
        result_filter=[ResultType.WEB],
        count=3,
        extra_snippets=True,
        summary=True
    )
    response = await client.search(options)
    print(f"Query Info:")
    print(f"  Original Query: {response.query.get('original_query', 'N/A')}")
    print(f"  Altered Query: {response.query.get('altered_query', 'N/A')}")
    print(f"\nFound {len(response.results)} results:")
    for result in response.results:
        print_result(result)
    
    # Test news search with advanced options
    print("\n\nNEWS SEARCH WITH ADVANCED OPTIONS")
    print("="*80)
    options = SearchOptions(
        query="AI developments",
        count=3,
        freshness=Freshness.PAST_MONTH,
        result_filter=[ResultType.NEWS],
        safesearch=SafeSearch.OFF,
        units=Units.METRIC,
        extra_snippets=True,
        summary=True
    )
    response = await client.search(options)
    print(f"Query Info:")
    print(f"  Original Query: {response.query.get('original_query', 'N/A')}")
    print(f"  Altered Query: {response.query.get('altered_query', 'N/A')}")
    print(f"\nFound {len(response.results)} results:")
    for result in response.results:
        print_result(result)

    # Test mixed search with multiple result types
    print("\n\nMIXED SEARCH")
    print("="*80)
    options = SearchOptions(
        query="Climate change solutions 2024",
        count=5,
        result_filter=[ResultType.WEB, ResultType.NEWS, ResultType.DISCUSSIONS],
        freshness=Freshness.PAST_YEAR,
        extra_snippets=True,
        summary=True
    )
    response = await client.search(options)
    print(f"Query Info:")
    print(f"  Original Query: {response.query.get('original_query', 'N/A')}")
    print(f"  Altered Query: {response.query.get('altered_query', 'N/A')}")
    
    # Group and count results by type
    result_types = {}
    for result in response.results:
        type_name = result.result_type.value
        if type_name not in result_types:
            result_types[type_name] = 0
        result_types[type_name] += 1
    
    print("\nResults by type:")
    for type_name, count in result_types.items():
        print(f"- {type_name}: {count} results")
        
    print(f"\nDetailed results ({len(response.results)} total):")
    for result in response.results:
        print_result(result)


if __name__ == "__main__":
    import asyncio
    from pprint import pprint
    
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Run the test
    asyncio.run(test_search())
