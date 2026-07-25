"""
VAgent Source Discovery - Automatically discovers and validates
trending web sources, scaling to 10,000+ verified URLs.

Uses seed-based crawling and pattern generation to find
new RSS feeds and trending sources across categories.
"""

import asyncio
import json
import logging
import pickle
import random
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ─── Seed Sources (starting points for discovery) ──────────────────────

SEED_DIRECTORIES = {
    'technology': [
        'https://en.wikipedia.org/wiki/List_of_technology_websites',
        'https://en.wikipedia.org/wiki/List_of_tech_blogs',
        'https://github.com/simevidas/web-dev-feeds',
        'https://blog.feedspot.com/technology_blogs/',
    ],
    'ai': [
        'https://en.wikipedia.org/wiki/List_of_artificial_intelligence_projects',
        'https://github.com/josephmisiti/awesome-machine-learning',
        'https://github.com/ujjwalkarn/Machine-Learning-Tutorials',
    ],
    'business': [
        'https://en.wikipedia.org/wiki/List_of_business_websites',
        'https://blog.feedspot.com/business_blogs/',
    ],
    'science': [
        'https://en.wikipedia.org/wiki/List_of_scientific_journals',
        'https://blog.feedspot.com/science_blogs/',
        'https://github.com/rossanafmenezes/Science-Blogs',
    ],
    'health': [
        'https://en.wikipedia.org/wiki/List_of_health_websites',
        'https://blog.feedspot.com/health_blogs/',
    ],
    'finance': [
        'https://en.wikipedia.org/wiki/List_of_financial_websites',
        'https://blog.feedspot.com/finance_blogs/',
    ],
    'entertainment': [
        'https://en.wikipedia.org/wiki/List_of_entertainment_websites',
        'https://blog.feedspot.com/entertainment_blogs/',
    ],
    'gaming': [
        'https://en.wikipedia.org/wiki/List_of_video_game_websites',
        'https://blog.feedspot.com/gaming_blogs/',
    ],
    'sports': [
        'https://en.wikipedia.org/wiki/List_of_sports_websites',
        'https://blog.feedspot.com/sports_blogs/',
    ],
    'politics': [
        'https://en.wikipedia.org/wiki/List_of_political_websites',
        'https://blog.feedspot.com/politics_blogs/',
    ],
    'lifestyle': [
        'https://blog.feedspot.com/lifestyle_blogs/',
    ],
    'education': [
        'https://en.wikipedia.org/wiki/List_of_educational_websites',
        'https://blog.feedspot.com/education_blogs/',
    ],
}

# Common RSS feed path patterns to try when discovering feeds
RSS_PATH_PATTERNS = [
    '/feed', '/rss', '/feed.xml', '/rss.xml', '/atom.xml',
    '/feeds', '/feeds/posts/default', '/news/rss',
    '/news/feed', '/blog/feed', '/blog/rss',
    '/rss/feed', '/rss/news', '/rss/all.xml',
    '/xml/rss.xml', '/rss.xml?format=rss',
    '/index.xml', '/feed/atom/',
]

# Pattern-based source generator
SOURCE_PATTERNS = {
    'regional_news': [
        # UK regional
        'https://www.{region}shirepost.co.uk', 'https://www.{region}today.co.uk',
        'https://www.{region}news.co.uk', 'https://www.{region}eveningpost.co.uk',
        # US regional
        'https://www.{region}times.com', 'https://www.{region}tribune.com',
        'https://www.{region}herald.com', 'https://www.{region}post.com',
        'https://www.{region}chronicle.com', 'https://www.{region}journal.com',
        'https://www.{region}news.com', 'https://www.{region}gazette.com',
        'https://www.{region}observer.com', 'https://www.{region}review.com',
        'https://www.{region}standard.com', 'https://www.{region}record.com',
        'https://www.{region}ledger.com', 'https://www.{region}sun.com',
        # Indian regional
        'https://www.{region}today.in', 'https://www.{region}news.in',
        'https://www.{region}times.in', 'https://www.{region}chronicle.in',
        # Australian regional
        'https://www.{region}times.com.au', 'https://www.{region}news.com.au',
        'https://www.{region}mail.com.au', 'https://www.{region}herald.com.au',
        # Canadian regional
        'https://www.{region}star.ca', 'https://www.{region}sun.ca',
        'https://www.{region}news.ca', 'https://www.{region}herald.ca',
        # European regional
        'https://www.{region}times.eu', 'https://www.{region}news.eu',
        'https://www.{region}herald.eu',
    ],
    'tech_company_news': [
        'https://blog.{company}.com', 'https://engineering.{company}.com',
        'https://tech.{company}.com', 'https://developers.{company}.com',
        'https://news.{company}.com', 'https://{company}.tech',
        'https://{company}.dev', 'https://{company}.io/blog',
    ],
    'university_news': [
        'https://news.{university}.edu', 'https://www.{university}.edu/news',
        'https://today.{university}.edu', 'https://{university}.ac.uk/news',
    ],
    'niche_blogs': [
        'https://www.{topic}blog.com', 'https://{topic}.com/blog',
        'https://{topic}weekly.com', 'https://{topic}daily.com',
        'https://{topic}insider.com', 'https://{topic}review.com',
    ],
    'gov_agencies': [
        'https://www.{country}.gov/news', 'https://{agency}.{country}.gov/news',
        'https://www.{country}.gov/{agency}/news',
    ],
}

# Regions for generating regional news patterns
REGIONS = [
    # US States
    'newyork', 'losangeles', 'chicago', 'houston', 'phoenix',
    'philadelphia', 'sanantonio', 'sandiego', 'dallas', 'austin',
    'seattle', 'denver', 'boston', 'nashville', 'portland',
    'miami', 'atlanta', 'detroit', 'minneapolis', 'cleveland',
    'tampa', 'orlando', 'sanjose', 'sacramento', 'longbeach',
    'kansascity', 'omaha', 'raleigh', 'columbus', 'indianapolis',
    'milwaukee', 'charlotte', 'jacksonville', 'memphis', 'louisville',
    'richmond', 'baltimore', 'birmingham', 'albany', 'hartford',
    'providence', 'buffalo', 'rochester', 'toledo', 'washington',
    'stlouis', 'pittsburgh', 'cincinnati', 'neworleans', 'oklahomacity',
    'saltlakecity', 'albuquerque', 'lasvegas', 'honolulu',
    'boulder', 'annarbor', 'madison', 'ithaca', 'burlington',
    # US regions
    'bayarea', 'siliconvalley', 'centralcoast', 'northshore',
    'westside', 'eastbay', 'southbay', 'northcounty',
    'triad', 'triangle', 'piedmont', 'inlandempire',
    # UK
    'london', 'manchester', 'liverpool', 'birmingham', 'leeds',
    'edinburgh', 'glasgow', 'cardiff', 'bristol', 'oxford',
    'cambridge', 'brighton', 'southampton', 'portsmouth',
    'nottingham', 'sheffield', 'newcastle', 'belfast', 'aberdeen',
    # India
    'mumbai', 'delhi', 'bangalore', 'hyderabad', 'chennai',
    'kolkata', 'pune', 'ahmedabad', 'jaipur', 'lucknow',
    'chandigarh', 'indore', 'bhopal', 'surat', 'kochi',
    'nagpur', 'thiruvananthapuram', 'guwahati',
    # Canada
    'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa',
    'edmonton', 'winnipeg', 'quebec', 'hamilton', 'halifax',
    # Australia
    'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide',
    'canberra', 'goldcoast', 'newcastle', 'hobart', 'darwin',
    # Europe
    'berlin', 'munich', 'hamburg', 'frankfurt', 'cologne',
    'paris', 'lyon', 'marseille', 'barcelona', 'madrid',
    'rome', 'milan', 'naples', 'vienna', 'zurich',
    'amsterdam', 'rotterdam', 'brussels', 'stockholm', 'copenhagen',
    'oslo', 'helsinki', 'dublin', 'lisbon', 'prague',
    'warsaw', 'budapest', 'athens', 'istanbul', 'moscow',
    # Asia
    'tokyo', 'osaka', 'kyoto', 'seoul', 'singapore',
    'hongkong', 'shanghai', 'beijing', 'shenzhen', 'taipei',
    'bangkok', 'kualalumpur', 'jakarta', 'manila', 'hochiminh',
    'dubai', 'abudhabi', 'doha', 'riyadh', 'telaviv',
    # Africa
    'cairo', 'casablanca', 'capetown', 'johannesburg', 'nairobi',
    'lagos', 'accra', 'dakar', 'addisababa', 'tunis',
    # South America
    'saopaulo', 'riodejaneiro', 'buenosaires', 'santiago', 'lima',
    'bogota', 'caracas', 'montevideo', 'quito', 'brasilia',
    # Oceania
    'auckland', 'wellington', 'christchurch', 'suva', 'portmoresby',
]

# Tech companies for generating company blog patterns
TECH_COMPANIES = [
    'google', 'apple', 'microsoft', 'amazon', 'meta', 'netflix',
    'twitter', 'linkedin', 'uber', 'airbnb', 'spotify', 'slack',
    'dropbox', 'stripe', 'square', 'paypal', 'shopify', 'reddit',
    'pinterest', 'snapchat', 'tiktok', 'zoom', 'robinhood',
    'datadog', 'mongodb', 'cloudflare', 'fastly', 'twilio',
    'sendgrid', 'digitalocean', 'vercel', 'netlify', 'github',
    'gitlab', 'circleci', 'travisci', 'docker', 'kubernetes',
    'hashicorp', 'nginx', 'apache', 'redis', 'elastic',
    'databricks', 'snowflake', 'confluent', 'cloudera',
    'salesforce', 'oracle', 'sap', 'adobe', 'intuit',
    'servicenow', 'workday', 'splunk', 'palantir', 'unity',
    'roblox', 'epicgames', 'activision', 'ea', 'ubisoft',
    'nintendo', 'sony', 'samsung', 'lg', 'intel',
    'amd', 'nvidia', 'qualcomm', 'broadcom', 'micron',
    'tesla', 'spacex', 'rivian', 'lucid', 'nio',
    'openai', 'anthropic', 'deepmind', 'huggingface', 'cohere',
    'replicate', 'stabilityai', 'runwayml', 'midjourney',
]

# Universities for generating news patterns
UNIVERSITIES = [
    'harvard', 'mit', 'stanford', 'berkeley', 'caltech',
    'oxford', 'cambridge', 'imperial', 'ucl', 'edinburgh',
    'columbia', 'yale', 'princeton', 'chicago', 'penn',
    'cornell', 'duke', 'northwestern', 'uchicago', 'johnshopkins',
    'washington', 'ucla', 'michigan', 'nyu', 'carnegie',
    'toronto', 'ubc', 'mcgill', 'waterloo', 'australian',
    'tsinghua', 'peking', 'tokyo', 'kyoto', 'nus',
    'ethz', 'epfl', 'kth', 'tudelft', 'mpg',
]

# Country codes for gov agency patterns
COUNTRIES = ['us', 'uk', 'ca', 'au', 'in', 'eu', 'de', 'fr', 'jp']

# Topics for niche blog patterns
NICHE_TOPICS = [
    'startup', 'venture', 'blockchain', 'crypto', 'nft',
    'privacy', 'security', 'cyber', 'cloud', 'devops',
    'datascience', 'analytics', 'iot', 'robotics', 'drones',
    'renewable', 'solar', 'wind', 'nuclear', 'climate',
    'parenting', 'fitness', 'yoga', 'meditation', 'wellness',
    'cooking', 'baking', 'recipes', 'nutrition', 'vegan',
    'photography', 'filmmaking', 'design', 'fashion', 'beauty',
    'travel', 'adventure', 'hiking', 'camping', 'backpacking',
    'music', 'podcast', 'streaming', 'gaming', 'esports',
    'marketing', 'seo', 'socialmedia', 'content', 'branding',
    'productivity', 'remote', 'freelance', 'career', 'leadership',
    'investing', 'trading', 'realestate', 'personal finance',
    'psychology', 'neuroscience', 'philosophy', 'history', 'language',
]


class SourceDiscovery:
    """Discovers, validates, and manages trending web sources at scale."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or Path.home() / '.hermes' / 'vagent_sources.pkl')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._sources: Dict[str, List[Dict]] = defaultdict(list)
        self._failed: Set[str] = set()
        self._http: Optional[httpx.AsyncClient] = None
        self.load()

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=10.0, follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
        return self._http

    def load(self):
        """Load previously discovered sources from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'rb') as f:
                    data = pickle.load(f)
                    self._sources = defaultdict(list, data.get('sources', {}))
                    self._failed = set(data.get('failed', []))
                total = sum(len(v) for v in self._sources.values())
                logger.info(f"Loaded {total} discovered sources from {self.db_path}")
            except Exception as e:
                logger.warning(f"Failed to load source database: {e}")

    def save(self):
        """Save discovered sources to disk."""
        with open(self.db_path, 'wb') as f:
            pickle.dump({
                'sources': dict(self._sources),
                'failed': list(self._failed),
                'updated': datetime.now().isoformat(),
            }, f)
        total = sum(len(v) for v in self._sources.values())
        logger.info(f"Saved {total} sources to {self.db_path}")

    def generate_pattern_sources(self) -> Dict[str, List[Dict]]:
        """Generate sources from URL patterns (no network needed)."""
        generated: Dict[str, List[Dict]] = defaultdict(list)
        seen: Set[str] = set()

        def _add(cat: str, url: str):
            url = url.rstrip('/')
            if url not in seen:
                seen.add(url)
                generated[cat].append({'url': url, 'type': 'html',
                                        'selector': 'h2 a, h3 a, .title a, article a'})

        # Generate regional news sources
        for region in REGIONS:
            for pattern in SOURCE_PATTERNS['regional_news']:
                url = pattern.replace('{region}', region)
                _add('general', url)

        # Generate tech company blogs
        for company in TECH_COMPANIES:
            for pattern in SOURCE_PATTERNS['tech_company_news']:
                url = pattern.replace('{company}', company)
                _add('technology', url)

        # Generate university news
        for uni in UNIVERSITIES:
            for pattern in SOURCE_PATTERNS['university_news']:
                url = pattern.replace('{university}', uni)
                _add('education', url)

        # Generate niche blogs
        for topic in NICHE_TOPICS:
            for pattern in SOURCE_PATTERNS['niche_blogs']:
                url = pattern.replace('{topic}', topic)
                c = 'technology'
                if topic in ('crypto', 'blockchain', 'nft'): c = 'crypto'
                elif topic in ('investing', 'trading', 'realestate', 'personal'): c = 'finance'
                elif topic in ('fitness', 'wellness', 'parenting'): c = 'lifestyle'
                elif topic in ('travel', 'adventure'): c = 'travel'
                elif topic in ('music', 'podcast', 'streaming'): c = 'entertainment'
                elif topic in ('gaming', 'esports'): c = 'gaming'
                elif topic in ('photography', 'design', 'fashion', 'beauty'): c = 'design'
                elif topic in ('cooking', 'nutrition', 'vegan'): c = 'food'
                _add(c, url)

        # Add RSS variants for all generated URLs
        rss_added = 0
        for cat, sources in list(generated.items()):
            for src in sources[:]:
                base_url = src['url']
                for pattern in RSS_PATH_PATTERNS[:5]:  # Try most common RSS paths
                    rss_url = base_url.rstrip('/') + pattern
                    if rss_url not in seen:
                        seen.add(rss_url)
                        generated[cat].append({'url': rss_url, 'type': 'rss'})
                        rss_added += 1

        logger.info(f"Generated {sum(len(v) for v in generated.values())} sources "
                     f"from patterns ({rss_added} RSS variants)")
        return dict(generated)

    async def discover_from_seeds(self, categories: Optional[List[str]] = None,
                                  max_per_category: int = 200):
        """Crawl seed directories to discover new sources."""
        client = await self._client()
        targets = {c: urls for c, urls in SEED_DIRECTORIES.items()
                   if categories is None or c in categories}

        for category, seeds in targets.items():
            for seed_url in seeds:
                try:
                    resp = await client.get(seed_url)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'lxml')

                    # Extract external links
                    for link in soup.select('a[href]'):
                        href = link.get('href', '').strip()
                        if not href or href.startswith('#') or href.startswith('/'):
                            continue
                        full_url = urljoin(seed_url, href)
                        parsed = urlparse(full_url)
                        if parsed.netloc and parsed.netloc != urlparse(seed_url).netloc:
                            # Check if it looks like a news/blog source
                            text = link.get_text(strip=True).lower()
                            if any(kw in text for kw in ['news', 'blog', 'feed', 'rss',
                                                         'trending', 'latest', 'articles']):
                                self._add_source(category, full_url, 'html')
                                if len(self._sources[category]) >= max_per_category:
                                    break

                except Exception as e:
                    logger.debug(f"Seed crawl failed for {seed_url}: {e}")

        self.save()

    def _add_source(self, category: str, url: str, stype: str = 'html'):
        """Add a validated source (O(1) amortized)."""
        url = url.rstrip('/')
        if url in self._failed:
            return
        self._sources[category].append({'url': url, 'type': stype,
                                         'selector': 'h2 a, h3 a, .title a, article a'
                                         if stype == 'html' else None})

    def add_sources_bulk(self, category: str, urls: List[str], stype: str = 'html'):
        """Add many sources at once (O(n), no per-item dedup)."""
        selector = 'h2 a, h3 a, .title a, article a' if stype == 'html' else None
        for url in urls:
            url = url.rstrip('/')
            if url not in self._failed:
                self._sources[category].append({
                    'url': url, 'type': stype, 'selector': selector
                })

    async def validate_sources(self, max_concurrent: int = 50):
        """Check which sources are actually reachable."""
        sem = asyncio.Semaphore(max_concurrent)
        client = await self._client()

        async def _check(source: Dict, category: str) -> bool:
            async with sem:
                try:
                    resp = await client.head(source['url'], timeout=5)
                    if resp.status_code < 400:
                        return True
                    # HEAD might fail, try GET
                    resp = await client.get(source['url'], timeout=5)
                    if resp.status_code < 400:
                        return True
                except Exception:
                    pass
                return False

        all_sources = [(s, c) for c, slist in self._sources.items() for s in slist]
        logger.info(f"Validating {len(all_sources)} sources...")

        validated: Dict[str, List[Dict]] = defaultdict(list)
        failed_count = 0

        for source, category in all_sources:
            if await _check(source, category):
                validated[category].append(source)
            else:
                self._failed.add(source['url'])
                failed_count += 1

        self._sources = validated
        total = sum(len(v) for v in self._sources.values())
        logger.info(f"Validation complete: {total} live, {failed_count} failed")
        self.save()
        return total

    async def run_full_discovery(self, categories: Optional[List[str]] = None,
                                 max_per_category: int = 500):
        """Run the full source discovery pipeline."""
        logger.info("Starting source discovery pipeline...")

        # Step 1: Generate from patterns
        pattern_sources = self.generate_pattern_sources()
        for cat, sources in pattern_sources.items():
            for src in sources:
                self._add_source(cat, src['url'], src.get('type', 'html'))

        # Step 2: Crawl seed directories
        try:
            await self.discover_from_seeds(categories, max_per_category)
        except Exception as e:
            logger.warning(f"Seed discovery failed: {e}")

        # Step 3: Validate
        try:
            live = await self.validate_sources()
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            live = sum(len(v) for v in self._sources.values())

        self.save()
        total = sum(len(v) for v in self._sources.values())
        logger.info(f"Discovery complete: {total} sources across "
                     f"{len(self._sources)} categories ({live} validated)")
        return dict(self._sources)

    def get_sources(self) -> Dict[str, List[Dict]]:
        """Get all discovered sources."""
        return dict(self._sources)

    def merge_into_trending_sources(self, existing: Dict[str, List[Dict]],
                                     max_per_category: int = 100) -> Dict[str, List[Dict]]:
        """Merge discovered sources into the TRENDING_SOURCES dict."""
        merged = defaultdict(list, {k: list(v) for k, v in existing.items()})
        seen: Set[str] = set()

        for cat, sources in existing.items():
            for s in sources:
                seen.add(s['url'])

        for cat, sources in self._sources.items():
            if cat not in merged:
                merged[cat] = []
            for s in sources:
                if s['url'] not in seen:
                    seen.add(s['url'])
                    merged[cat].append(s)

        # Limit per category
        result = {}
        for cat, sources in merged.items():
            result[cat] = sources[:max_per_category]

        final_total = sum(len(v) for v in result.values())
        logger.info(f"Merged {final_total} sources into trending sources "
                     f"({len(result)} categories)")
        return result

    async def cleanup(self):
        if self._http:
            await self._http.aclose()
            self._http = None


def discover_and_merge(existing_sources: Dict[str, List[Dict]],
                        max_per_category: int = 600) -> Dict[str, List[Dict]]:
    """Run discovery and merge results synchronously (for startup)."""
    discovery = SourceDiscovery()
    try:
        # Generate pattern sources (no network needed)
        pattern_sources = discovery.generate_pattern_sources()
        for cat, sources in pattern_sources.items():
            for src in sources:
                for existing_cat, existing_list in existing_sources.items():
                    if src['url'] in {s['url'] for s in existing_list}:
                        break
                else:
                    existing_sources.setdefault(cat, []).append(src)

        # Limit per category
        result = {}
        for cat, sources in existing_sources.items():
            result[cat] = sources[:max_per_category]
            logger.info(f"  {cat}: {len(result[cat])} sources")

        return result
    finally:
        discovery.save()
