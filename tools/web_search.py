from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import requests
import time
import os
from dotenv import load_dotenv

@dataclass
class BraveSearchResult:
    title: str
    url: str
    description: str

class BraveSearchClient:
    """Client for interacting with Brave Search API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('BRAVE_API_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided or set in BRAVE_API_KEY environment variable")
            
        self.base_url = 'https://api.search.brave.com/res/v1/web/search'
        self.last_request_time = 0
        self.min_request_interval = 1.1  # 1.1 seconds to be safe
        
    async def _delay(self, seconds: float) -> None:
        """Delay execution for specified number of seconds"""
        time.sleep(seconds)
        
    async def _wait_for_rate_limit(self) -> None:
        """Ensure we don't exceed rate limits"""
        now = time.time()
        time_since_last_request = now - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            await self._delay(wait_time)
            
        self.last_request_time = time.time()
        
    async def search(self, query: str, count: int = 20) -> List[BraveSearchResult]:
        """
        Perform a web search using Brave Search API
        
        Args:
            query: Search query string
            count: Number of results to return (max 20)
            
        Returns:
            List of BraveSearchResult objects
            
        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            await self._wait_for_rate_limit()
            
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'X-Subscription-Token': self.api_key
            }
            
            params = {
                'q': query,
                'count': min(count, 20)  # Brave API max limit is 20
            }
            
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            return [
                BraveSearchResult(
                    title=result['title'],
                    url=result['url'],
                    description=result['description']
                )
                for result in data['web']['results']
            ]
            
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.status_code == 429:
                print('Rate limit exceeded, retrying after delay...')
                await self._delay(2)  # Wait 2 seconds on rate limit
                return await self.search(query, count)  # Retry the request
                
            print(f'Error performing Brave search: {str(e)}')
            raise


if __name__ == "__main__":
    import asyncio
    from pprint import pprint
    
    async def test_search():
        # Load environment variables
        load_dotenv()
        
        # Create client
        client = BraveSearchClient()
        
        # Test basic search
        print("\nTesting basic search...")
        results = await client.search("What is artificial intelligence?", count=5)
        print(f"Got {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            pprint(vars(result))
            
        # Test rate limiting
        print("\nTesting rate limiting...")
        print("Making two quick requests to test rate limiting...")
        results1 = await client.search("Python programming", count=3)
        results2 = await client.search("Machine learning", count=3)
        print(f"Successfully got {len(results1)} and {len(results2)} results")
        
        # Test error handling
        print("\nTesting error handling with invalid API key...")
        try:
            invalid_client = BraveSearchClient(api_key="invalid_key")
            await invalid_client.search("test")
        except Exception as e:
            print(f"Successfully caught error: {str(e)}")
            
    # Run the tests
    asyncio.run(test_search())
