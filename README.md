# Deep Search

A powerful tool for conducting in-depth web research on specified topics. Deep Search leverages Brave Search for web queries, Firecrawl for web content extraction, and OpenAI for summarization and analysis.

## Features

- Multi-step research process with configurable depth
- Web search integration with Brave Search API
- Content extraction from web pages using Firecrawl
- AI-powered analysis and summarization using OpenAI
- Customizable research parameters and settings

## Architecture
<img width="941" alt="image" src="https://github.com/user-attachments/assets/8ba419e6-094a-46d8-9b09-22cd2298d879" />
<img width="425" alt="image" src="https://github.com/user-attachments/assets/55c75049-082c-494a-965e-51fb378dd297" />

## Installation

### Prerequisites

- Python 3.8+
- Brave Search API key
- Firecrawl API key
- OpenAI API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/deep-search.git
   cd deep-search
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the provided `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Add your API keys to the `.env` file:
   ```
   BRAVE_API_KEY=your_brave_api_key_here
   FIRECRAWL_API_KEY=your_firecrawl_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

The easiest way to use Deep Search is with the included `main.py` script, which runs a research session on a specified topic.

### Running the Tool

Simply run the main.py script:

```bash
python main.py
```

The script will:
1. Load your API keys from the .env file
2. Configure a research session on the topic "Impact of artificial intelligence on healthcare in 2025"
3. Run the research process
4. Display the results, including a main report, key learnings, and areas for further exploration

### Customizing the Research Topic

To research a different topic, edit the `research_topic` variable in `main.py`:

```python
# Define research topic - change this to your desired research topic
research_topic = "Your research topic here"
```

### Customizing Research Settings

You can also customize the research settings in `main.py` by modifying the `ResearchSettings` parameters:

```python
settings = ResearchSettings(
    max_depth=3,             # Number of research steps
    search_timeout=300,      # Timeout in seconds
    max_results=30,          # Maximum search results
    include_web_content=True,
    include_news=True,
    include_discussions=True,
    language="en"
)
```

## Project Structure

- `session/`: Core session management and research logic
  - `session.py`: Main session controller
  - `researcher.py`: Handles research logic and OpenAI integration
  - `job.py`: Manages research jobs and queries
  - `step.py`: Handles individual research steps
  - `evaluator.py`: Evaluates research quality
- `tools/`: External API integrations
  - `web_search.py`: Brave Search API client
  - `web_extract.py`: Firecrawl web extraction client
- `docs-ref/`: Reference documentation
- `input_config.py`: Configuration classes for research input
- `main.py`: Main script to run the research tool

## License

MIT License

Copyright (c) 2025 Deep Search Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
