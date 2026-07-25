<div align="center">
  <h1>VAgent</h1>
  <p><strong>Multi-Agent Video Content Creation System</strong></p>
  <p>Automated web research at scale → trend analysis → AI video production → multi-platform publishing</p>
  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
    <img src="https://img.shields.io/badge/status-Architecture%20ready-brightgreen" alt="Status">
  </p>
</div>

---

## What is VAgent?

VAgent is a **multi-agent AI system** that automates the entire content creation pipeline — from discovering trending topics across the web to publishing professionally styled videos. It uses **5 specialized agents** running concurrently to:

1. **Research** 10,000+ trending web sources across 22 categories
2. **Identify** the top trending topics with NLP-powered trend analysis
3. **Strategize** which topics will perform best as video content
4. **Produce** professionally formatted video content with hooks, scripts, and attention engineering
5. **Publish** to YouTube, TikTok, Instagram, LinkedIn, Twitter, and Facebook

## Architecture

```
                    ┌─────────────────────────┐
                    │   VAgent Orchestrator    │
                    │  (Pipeline Coordinator)  │
                    └────┬──────┬──────┬───────┘
                         │      │      │
              ┌──────────┘      │      └──────────┐
              ▼                 ▼                  ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │  Research    │  │    Trend     │  │   Content    │
     │  Coordinator │──▶   Analysis   │──▶   Strategy   │
     │  (Web Scrape)│  │   (NLP)      │  │   (Scoring)  │
     └──────────────┘  └──────────────┘  └──────┬───────┘
                                                │
                                                ▼
                                      ┌──────────────┐
                                      │    Video     │
                                      │  Production  │
                                      │  (Render +   │
                                      │   Scripts)   │
                                      └──────┬───────┘
                                             │
                                             ▼
                                      ┌──────────────┐
                                      │  Publishing  │
                                      │  (6 Platforms)│
                                      └──────────────┘
```

### The 5 Agents

| Agent | Role | Runs |
|---|---|---|
| **ResearchCoordinator** | Scrapes trending sources via HTTP (RSS feeds, HTML parsing) | `asyncio.gather` concurrent |
| **TrendAnalysisAgent** | NLP topic extraction, frequency analysis, category clustering | Sync + parallel |
| **ContentStrategyAgent** | Scores topics by attention/viral/monetization potential | Selects top candidates |
| **VideoProductionAgent** | Generates hooks, scripts, platform-optimized formats, renders frames | Parallel per topic |
| **PublishingAgent** | Platform-specific formatting for 6 social channels | Simulated (keys needed) |

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/vagent.git
cd vagent

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline
python main.py --websites 1000 --trends 50 --videos 10
```

### Minimal Test

```bash
# Run with tiny batch to verify installation
python -c "
import asyncio
from vagent.core import VAgentOrchestrator

async def test():
    o = VAgentOrchestrator()
    results = await o.run_full_pipeline(
        research_websites=10,
        top_trends=5,
        videos_per_topic=2
    )
    print(f'✓ {len(results[\"research_results\"])} articles researched')
    print(f'✓ {len(results[\"trend_analysis\"].trends)} trends identified')
    print(f'✓ {len(results[\"selected_topics\"])} topics selected')
    print(f'✓ {len(results[\"video_contents\"])} videos produced')

asyncio.run(test())
"
```

## Pipeline Details

### Phase 1: Web Research (12,000+ sources)
- Scrapes **1,007 manually curated + 11,000+ pattern-generated sources** across 22 categories
- Sources: RSS feeds, HTML scraping with BeautifulSoup
- Categories: technology, ai, business, science, health, finance, entertainment, gaming, sports, politics, lifestyle, education, crypto, design, fashion, food, travel, space, history, environment, general
- **47,190 pattern-generated** source URLs from regional news, tech companies, universities, and niche blogs
- HTTP concurrent scraper with rate limiting, exponential backoff, and content deduplication

### Phase 2: Trend Analysis (100 topics)
- Multi-strategy NLP topic extraction:
  - Known category matching (150+ trending keywords)
  - Action-word context extraction (launch, breakthrough, partnership, etc.)
  - Title pattern recognition
  - Company/product name extraction
- Frequency-based scoring with engagement weight
- Category clustering and cross-topic relationship mapping

### Phase 3: Content Strategy (attention scoring)
- Each topic scored on 5 dimensions:
  - **Attention Potential** — will viewers care?
  - **Viral Probability** — will it spread?
  - **Content Gap Score** — is the topic underserved?
  - **Monetization Potential** — can it generate value?
  - **Competition Level** — how saturated is it?
- Composite scoring formula for optimal selection

### Phase 4: Video Production (professional output)
- **Hook Generation** — 5 styles (curiosity, urgency, controversy, surprise, value)
- **Script Generation** — timed segments with intros, body, CTAs
- **Frame Rendering** (Pillow, no ffmpeg required):
  - 1080×1920 vertical video frames
  - Gradient backgrounds with professional color palettes
  - Bold typography with title cards, hook overlays, and end cards
  - Animated GIF previews
- **Platform Format Optimization** — TikTok Shorts (15-60s), YouTube (1-5m), educational (10m+)
- **Media Retrieval** — stock clip/image fetching from Pexels, Pixabay, Unsplash

### Phase 5: Publishing (6 platforms)
- YouTube, TikTok, Instagram Reels, LinkedIn, Twitter/X, Facebook
- Platform-specific format adjustments (aspect ratios, durations, descriptions)
- Auto-generated tags and hashtags for discoverability

## Requirements

- **Python 3.10+**
- **Dependencies**: httpx, beautifulsoup4, lxml, feedparser, Pillow, PyYAML

### Optional
- **ffmpeg**: For actual video file encoding (GPU-accelerated rendering)
  ```bash
  sudo apt install ffmpeg  # Linux
  brew install ffmpeg       # macOS
  ```
- **API Keys**: For real publishing:
  - YouTube Data API v3
  - TikTok Business API
  - Instagram Graph API

## Project Structure

```
vagent/
├── __init__.py          # Package exports
├── agents.py            # Agent implementations (5 agents)
├── core.py              # VAgentOrchestrator pipeline coordinator
├── main.py              # CLI entry point
├── scraper.py           # Web scraper (12k+ sources, RSS + HTML)
├── source_discovery.py  # Pattern-based source discovery (47k URLs)
├── media.py             # Media retrieval (stock clips, images)
├── video.py             # Video renderer + script generator
├── models.py            # Data models (Trend, VideoContent, etc.)
├── utils.py             # Config, logging, helpers
├── config/
│   └── default.yaml     # Pipeline configuration
├── tests/
│   └── test_basic.py    # 9 unit tests
├── examples/
│   └── comprehensive_example.py
├── requirements.txt
├── setup.py
├── README.md
├── LICENSE
└── .gitignore
```

## Configuration

Edit `config/default.yaml` to tune:

```yaml
research:
  max_concurrent: 50           # Parallel HTTP requests
  max_articles_per_category: 100

trend_analysis:
  top_n: 100                   # Number of trending topics
  confidence_threshold: 0.7    # Minimum confidence

content_strategy:
  min_attention_potential: 0.15
  min_content_gap: 0.05
  videos_per_topic: 10

video_production:
  default_durations:
    short_form: 30             # TikTok/Reels
    medium_form: 180           # YouTube
    long_form: 600             # Educational

publishing:
  platforms:
    - youtube
    - tiktok
    - instagram
    - linkedin
```

## Tests

```bash
python tests/test_basic.py
```

All 9 tests pass:
- ✅ Configuration Loading
- ✅ Orchestrator Initialization
- ✅ Research Tasks
- ✅ Trend Analysis
- ✅ Content Strategy
- ✅ Video Production
- ✅ Publishing
- ✅ Full Pipeline
- ✅ File Operations

## Performance

| Metric | Value |
|---|---|
| Source discovery | 47,190 patterns in 0.04s |
| Source expansion | 12,586 sources in 0.26s |
| Article scraping | 1,000 articles in ~30s (50 concurrent) |
| Trend analysis | 100 topics in 0.1s |
| Frame rendering | 1080×1920 in 0.5s |
| Script generation | 50 scripts in 0.3s |

## License

MIT

---

<p align="center">Built with ❤️ by Zaki</p>
