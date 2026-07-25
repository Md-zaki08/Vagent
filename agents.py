#!/usr/bin/env python3
"""
VAgent Agents - Multi-Agent System for Content Creation

Contains specialized agents that use Hermes' multi-agent capabilities
through delegate_task for true parallel execution.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from vagent.models import (
    ResearchTask, ResearchResult, Trend, TrendAnalysis, TopicAssessment,
    VideoContent, PlatformConfig, PublishingResult, Platform, VideoFormat
)
from vagent.utils import load_config, setup_logging, sanitize_filename
from vagent.scraper import get_trending_sources

logger = logging.getLogger(__name__)


# ─── Research Coordinator ──────────────────────────────────────────────────────

class ResearchCoordinator:
    """Orchestrates large-scale web research via Hermes delegate_task sub-agents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_concurrent = config.get('research', {}).get('max_concurrent', 50)
        self._categories = config.get('research', {}).get('categories', [
            'technology', 'business', 'entertainment', 'sports', 'health',
            'science', 'politics', 'education', 'finance', 'lifestyle'
        ])

    async def execute_research(self, tasks: List[ResearchTask]) -> List[ResearchResult]:
        """Execute research tasks using web scraper + optional Hermes delegate_task."""
        logger.info(f"Starting research for {len(tasks)} tasks across {len(self._categories)} categories")

        # Strategy 1: Quick scrape from all categories in parallel
        all_results = await self._research_all_categories()

        if all_results:
            logger.info(f"Scraper research: {len(all_results)} results from all categories")
            return all_results

        # Strategy 2: Process tasks individually (fallback)
        logger.info("Trying task-based research")
        batch_size = min(self.config.get('research', {}).get('batch_size', 10), 3)
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await self._research_batch(batch)
            all_results.extend(batch_results)
            logger.info(f"Batch progress: {min(i+batch_size, len(tasks))}/{len(tasks)} tasks")

        logger.info(f"Research completed. Total results: {len(all_results)}")
        return all_results

    async def _research_all_categories(self) -> List[ResearchResult]:
        """Scrape all categories in parallel."""
        from vagent.scraper import WebScraper, ContentExtractor
        scraper = WebScraper(max_concurrent=15)

        # Scrape all categories in parallel
        tasks = []
        for cat in self._categories:
            tasks.append(scraper.scrape_category(cat, max_articles=100))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for r in results:
            if isinstance(r, list):
                all_articles.extend(r)

        if not all_articles:
            return []

        # Extract content for top articles
        extractor = ContentExtractor()
        content_tasks = [extractor.extract(a.url) for a in all_articles[:30]]
        content_results = await asyncio.gather(*content_tasks, return_exceptions=True)

        content_map = {}
        for cr in content_results:
            if isinstance(cr, dict) and cr.get('content'):
                content_map[cr['url']] = cr['content']

        # Build ResearchResults
        research_results = []
        for article in all_articles:
            content = content_map.get(article.url, article.summary or article.title)
            research_results.append(ResearchResult(
                url=article.url,
                title=article.title,
                content=content,
                category=article.category,
                relevance_score=min(1.0, len(content) / 2000),
                engagement_metrics={'engagement': 50.0},
                tags=[article.category],
            ))

        logger.info(f"Scraper produced {len(research_results)} research results")
        return research_results

    async def _research_batch(self, batch: List[ResearchTask]) -> List[ResearchResult]:
        """Research a batch of tasks in parallel using delegate_task or direct tools."""
        if not batch:
            return []

        category = batch[0].category
        queries = [t.query for t in batch]
        query_list = "\n".join(f"- {q}" for q in queries)

        # Check if delegate_task is available (Hermes agent context)
        # It's injected by Hermes at runtime, not importable as Python
        delegate_fn = self._get_delegate_function()

        if delegate_fn is not None:
            # Use Hermes multi-agent delegation for true parallelism
            logger.info(f"Delegating {len(batch)} {category} tasks to Hermes sub-agent")
            try:
                result = delegate_fn(
                    goal=f"Research trending topics in {category}. Search {len(batch)*10}+ websites.",
                    context=f"""Research these topics across the web:
{query_list}

For EACH topic:
1. Use web_search() to find 10+ relevant sources
2. Use web_extract() to read the actual content
3. Extract: key trends, statistics, key players, controversies, content gaps

Return JSON array with: topic, url, title, content_summary, relevance_score 0-1, tags.
Be thorough - this data drives video content decisions.""",
                    role='leaf'
                )
                if result:
                    return self._parse_delegated_result(result, category)
            except Exception as e:
                logger.warning(f"delegate_task failed, falling back to direct: {e}")

        # Fallback: direct research using Hermes web tools
        return await self._research_direct(batch)

    def _get_delegate_function(self):
        """Check if delegate_task is available in the current context."""
        try:
            from hermes_tools import delegate_task as dt
            return dt
        except ImportError:
            pass
        try:
            # delegate_task might be a global in the Hermes agent context
            if 'delegate_task' in dir() and callable(delegate_task):
                return delegate_task
        except NameError:
            pass
        return None

    def _parse_delegated_result(self, raw_result, category: str) -> List[ResearchResult]:
        """Parse results from a delegated research task."""
        results = []
        try:
            data = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
            if isinstance(data, list):
                for item in data:
                    results.append(ResearchResult(
                        url=item.get('url', ''),
                        title=item.get('title', ''),
                        content=item.get('content_summary', item.get('content', '')),
                        category=category,
                        relevance_score=item.get('relevance_score', 0.5),
                        tags=item.get('tags', []),
                    ))
            elif isinstance(data, dict) and 'results' in data:
                for item in data['results']:
                    results.append(ResearchResult(
                        url=item.get('url', ''),
                        title=item.get('title', ''),
                        content=item.get('content_summary', item.get('content', '')),
                        category=category,
                        relevance_score=item.get('relevance_score', 0.5),
                        tags=item.get('tags', []),
                    ))
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Could not parse delegated result: {e}")
        return results

    async def _research_direct(self, batch: List[ResearchTask]) -> List[ResearchResult]:
        """Fallback: research using direct Hermes tools."""
        results = []
        for task in batch:
            try:
                agent = ResearchAgent(task.category, self.config)
                task_results = await agent.research_websites([task])
                results.extend(task_results)
            except Exception as e:
                logger.error(f"Error researching {task.id}: {e}")
        return results


class ResearchAgent:
    """Direct research agent using Hermes web tools."""

    def __init__(self, category: str, config: Dict[str, Any]):
        self.category = category
        self.config = config
        self.max_per_query = config.get('research', {}).get('max_websites_per_query', 100)

    async def research_websites(self, tasks: List[ResearchTask]) -> List[ResearchResult]:
        """Research websites for given tasks."""
        logger.info(f"Researching {len(tasks)} tasks in {self.category}")
        results = []
        for task in tasks:
            try:
                res = await self._perform_research(task)
                results.extend(res)
            except Exception as e:
                logger.error(f"Task {task.id} failed: {e}")
        return results

    async def _perform_research(self, task: ResearchTask) -> List[ResearchResult]:
        """Perform research using Hermes web tools first, then fall back to direct HTTP scraping."""
        import json

        # Strategy 1: Try Hermes web tools
        results = await self._research_via_hermes_tools(task)
        if results:
            return results

        # Strategy 2: Use direct HTTP web scraper
        logger.info(f"Falling back to direct HTTP scraping for: {task.category}")
        return await self._research_via_scraper(task)

    async def _research_via_hermes_tools(self, task: ResearchTask) -> List[ResearchResult]:
        """Research using Hermes' native web tools."""
        try:
            from tools.web_tools import web_search_tool, web_extract_tool
        except ImportError:
            return []

        results = []
        try:
            resp = web_search_tool(query=task.query,
                                   limit=min(task.max_websites, self.max_per_query))
            search_data = json.loads(resp) if isinstance(resp, str) else resp
            if not search_data.get('success'):
                return []

            web_results = search_data.get('data', {}).get('web', [])
            if not web_results:
                return []

            urls = [r['url'] for r in web_results[:10]
                    if isinstance(r, dict) and r.get('url')]

            extract_resp = await web_extract_tool(urls, char_limit=5000)
            extract_data = json.loads(extract_resp) if isinstance(extract_resp, str) else extract_resp

            for item in extract_data.get('results', []):
                if item.get('error'):
                    continue
                results.append(ResearchResult(
                    url=item.get('url', ''),
                    title=item.get('title', ''),
                    content=item.get('content', item.get('text', '')),
                    category=self.category,
                    relevance_score=self._score(item, task.query),
                    engagement_metrics={'engagement': 50.0},
                    tags=self._extract_tags(item.get('content', '')),
                ))
        except Exception as e:
            logger.debug(f"Hermes research error: {e}")

        return results

    async def _research_via_scraper(self, task: ResearchTask) -> List[ResearchResult]:
        """Research using direct HTTP web scraping (no API keys required)."""
        from vagent.scraper import WebScraper, ContentExtractor, TrendAggregator

        scraper = WebScraper(max_concurrent=10)

        # Get category from task
        category = task.category.lower()
        if category == 'technology':
            categories_to_scrape = ['technology', 'ai', 'general']
        elif category in get_trending_sources():
            categories_to_scrape = [category, 'general']
        else:
            categories_to_scrape = ['general']

        all_articles = []
        for cat in categories_to_scrape:
            articles = await scraper.scrape_category(cat, max_articles=50)
            all_articles.extend(articles)

        if not all_articles:
            return []

        # Extract full content for top articles
        extractor = ContentExtractor()
        content_tasks = [extractor.extract(a.url) for a in all_articles[:20]]
        content_results = await asyncio.gather(*content_tasks, return_exceptions=True)

        content_map = {}
        for cr in content_results:
            if isinstance(cr, dict) and cr.get('content'):
                content_map[cr['url']] = cr['content']

        # Build ResearchResults
        results = []
        for article in all_articles[:100]:
            content = content_map.get(article.url, article.summary)
            results.append(ResearchResult(
                url=article.url,
                title=article.title,
                content=content,
                category=category,
                relevance_score=min(1.0, len(content) / 2000),
                engagement_metrics={'engagement': 50.0},
                tags=self._extract_tags(article.title + ' ' + article.summary),
            ))

        logger.info(f"Scraper produced {len(results)} results for '{task.category}'")
        return results

    def _score(self, item: Dict, query: str) -> float:
        content = (item.get('content') or item.get('text') or '').lower()
        terms = query.lower().split()
        score = sum(1 for t in terms if t in content)
        return min(1.0, score / max(len(terms), 1) * 0.5)

    def _extract_tags(self, content: str) -> List[str]:
        tags = self.config.get('research', {}).get('categories', [])
        found = [t for t in tags if t in content.lower()]
        return found[:10]


# ─── Trend Analysis Agent ──────────────────────────────────────────────────────

class TrendAnalysisAgent:
    """Analyzes research results to identify trending topics with AI."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def analyze_trends(self, research_results: List[ResearchResult], top_n: int = 100) -> TrendAnalysis:
        """Analyze trends from research results."""
        logger.info(f"Analyzing trends from {len(research_results)} results (top {top_n})")

        topic_scores: Dict[str, dict] = {}

        for result in research_results:
            topics = self._extract_topics(result.content)
            for topic in topics:
                if topic not in topic_scores:
                    topic_scores[topic] = {
                        'score': 0.0, 'frequency': 0, 'categories': set(),
                        'engagement': 0.0, 'urls': []
                    }
                ts = topic_scores[topic]
                ts['score'] += result.relevance_score
                ts['frequency'] += 1
                ts['categories'].add(result.category)
                ts['engagement'] += result.engagement_metrics.get('engagement', 0.0)
                if len(ts['urls']) < 5:
                    ts['urls'].append(result.url)

        trends = []
        for topic, data in topic_scores.items():
            score: float = data['score']
            growth: float = min(1.0, data['frequency'] / 20.0)  # Normalized for real data ranges
            eng: float = min(1.0, data['engagement'] / max(len(data['categories']), 1) / 50)

            t = Trend(
                topic=topic,
                category=self._dominant_category(list(data['categories'])),
                trend_score=min(1.0, score * 0.3),
                growth_rate=growth,
                search_volume=data['frequency'],
                engagement_score=eng,
                related_topics=self._related_topics(topic, topic_scores),
                content_examples=list(data['urls'])[:3],
                predicted_trajectory='rising' if growth > 0.3 else 'emerging' if growth > 0.1 else 'steady'
            )
            trends.append(t)

        trends.sort(key=lambda x: x.trend_score, reverse=True)
        top_trends = trends[:top_n]

        cat_scores = {}
        for t in top_trends:
            cat_scores[t.category] = cat_scores.get(t.category, 0) + t.trend_score

        confidence = min(1.0, len(top_trends) / 50.0) if top_trends else 0.0

        analysis = TrendAnalysis(
            trends=top_trends,
            top_categories=cat_scores,
            confidence_level=confidence,
            market_insights=self._insights(top_trends)
        )

        logger.info(f"Identified {len(top_trends)} trending topics (confidence: {confidence:.2f})")
        return analysis

    def _extract_topics(self, content: str) -> List[str]:
        """Extract topic candidates from content using multi-strategy NLP."""
        topics = set()
        content_lower = content.lower()

        # Strategy 1: Known trending categories (direct match)
        known_categories = {
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'blockchain', 'crypto', 'cryptocurrency', 'bitcoin', 'ethereum',
            'python', 'javascript', 'typescript', 'rust', 'golang',
            'startup', 'startups', 'start-up',
            'cloud', 'devops', 'kubernetes', 'docker', 'aws',
            'cybersecurity', 'security', 'privacy', 'encryption',
            'data science', 'data engineering', 'big data',
            'quantum', 'quantum computing',
            'robotics', 'robot', 'automation',
            'ev', 'electric vehicle', 'electric car', 'tesla',
            'climate', 'climate change', 'renewable energy', 'solar',
            'space', 'nasa', 'spacex', 'rocket',
            'biotech', 'biotechnology', 'gene', 'dna',
            'gaming', 'esports', 'video game',
            '5g', '6g', 'network', 'internet',
            'semiconductor', 'chip', 'processor', 'nvidia', 'intel', 'amd',
            'saas', 'software', 'app', 'mobile', 'web',
            'metaverse', 'vr', 'ar', 'virtual reality', 'augmented reality',
            'fintech', 'payments', 'banking',
            'health', 'healthcare', 'medicine', 'medical',
            'education', 'edtech', 'learning',
            'crypto', 'defi', 'nft', 'web3',
            'social media', 'tiktok', 'instagram', 'youtube', 'twitter',
            'open source', 'github', 'git',
            'api', 'microservice', 'serverless', 'edge computing',
            'llm', 'gpt', 'openai', 'anthropic', 'claude',
            'productivity', 'remote work', 'hybrid', 'work from home',
            'sustainability', 'green', 'eco', 'environment',
            'investment', 'stock', 'market', 'economy', 'inflation',
            'fundraising', 'venture capital', 'ipo', 'acquisition',
            'podcast', 'streaming', 'netflix', 'spotify',
            'database', 'sql', 'nosql', 'postgres', 'mongodb',
        }

        for cat in known_categories:
            if cat in content_lower:
                topics.add(cat)

        # Strategy 2: Extract noun phrases near action words
        action_words = ['new', 'launch', 'release', 'update', 'upgrade', 'introduc',
                        'announce', 'build', 'create', 'develop', 'deploy', 'ship',
                        'transform', 'revolutionize', 'disrupt', 'innovate',
                        'partnership', 'investment', 'funding', 'acquisition',
                        'breakthrough', 'discovery', 'research', 'study',
                        'growth', 'surge', 'boom', 'rising', 'trend',
                        'how to', 'guide', 'tutorial', 'best', 'top',
                        'platform', 'tool', 'framework', 'solution', 'service',
                        'vs', 'versus', 'comparison', 'review', 'test',
                        'why', 'what is', 'how does', 'future of',
                        'inside', 'behind', 'exclusive', 'report',
                        'analysis', 'insight', 'strategy', 'tactic']

        for word in action_words:
            if word in content_lower:
                # Find the sentence/context around the action word
                idx = content_lower.index(word)
                # Get the full sentence or reasonable context
                start = max(0, idx - 60)
                end = min(len(content), idx + 80)
                context = content[start:end]
                # Clean HTML tags
                context = re.sub(r'<[^>]+>', ' ', context)
                context = re.sub(r'[^a-zA-Z0-9\s\-\']', ' ', context)
                context = re.sub(r'\s+', ' ', context).strip()
                # Extract key noun phrases (skip stopwords at start)
                words = context.split()
                filtered = [w for w in words if len(w) > 2]
                if len(filtered) > 1:
                    # Take the unique significant phrase
                    phrase = ' '.join(filtered)
                    if 5 < len(phrase) < 100:
                        topics.add(phrase[:80].strip())

        # Strategy 3: Title-based topics - extract from the first 150 chars
        # (titles tend to be at the start of the content)
        title_portion = content_lower[:150]
        # Look for common newsworthy patterns
        title_patterns = re.findall(r'(?:announc|launch|new|update|introduc).{10,60}?(?:platform|tool|app|service|feature|product|update|version|model|api|system)',
                                    title_portion)
        for pattern in title_patterns:
            clean = re.sub(r'[^a-zA-Z0-9\s\-\']', ' ', pattern).strip()
            if clean and len(clean) > 5:
                topics.add(clean[:60].strip())

        # Strategy 4: Company/product names (capitalized words near action verbs)
        company_pattern = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s.{0,20}(?:announc|launch|releas|rais|acquire|partner)',
                                     content[:500])
        for match in company_pattern[:3]:
            if match and len(match) > 2:
                topics.add(match.lower().strip())

        # Limit and deduplicate
        result = [t for t in list(topics) if 3 <= len(t) <= 80]
        # Remove near-duplicates
        unique = []
        seen_phrases = set()
        for topic in sorted(result, key=len, reverse=True):
            if topic not in seen_phrases and not any(topic in s for s in seen_phrases if len(s) > len(topic)):
                unique.append(topic)
                seen_phrases.add(topic)

        return unique[:15]

    def _dominant_category(self, categories: list) -> str:
        return max(set(categories), key=categories.count) if categories else 'general'

    def _related_topics(self, topic: str, all_topics: Dict) -> List[str]:
        related = [t for t in all_topics if t != topic and self._word_overlap(t, topic) > 0]
        return related[:5]

    def _word_overlap(self, a: str, b: str) -> float:
        wa, wb = set(a.lower().split()), set(b.lower().split())
        return len(wa & wb) / max(len(wa | wb), 1)

    def _insights(self, trends: List[Trend]) -> Dict[str, Any]:
        return {
            'dominant_categories': self._top_cats(trends),
            'total_trends': len(trends),
            'avg_score': sum(t.trend_score for t in trends) / max(len(trends), 1),
            'emerging_count': sum(1 for t in trends if t.predicted_trajectory == 'emerging'),
            'rising_count': sum(1 for t in trends if t.predicted_trajectory == 'rising'),
        }

    def _top_cats(self, trends: List[Trend]) -> Dict[str, float]:
        cats = {}
        for t in trends:
            cats[t.category] = cats.get(t.category, 0) + t.trend_score
        return dict(sorted(cats.items(), key=lambda x: -x[1])[:5])


# ─── Content Strategy Agent ────────────────────────────────────────────────────

class ContentStrategyAgent:
    """Selects best topics and creates content strategy for maximum attention."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_attention = config.get('content_strategy', {}).get('min_attention_potential', 0.2)
        self.min_gap = config.get('content_strategy', {}).get('min_content_gap', 0.05)
        self.min_monetization = config.get('content_strategy', {}).get('min_monetization', 0.1)

    async def select_topics(self, trend_analysis: TrendAnalysis, videos_per_topic: int = 10) -> List[Dict]:
        """Select the best topics that will get maximum attention as videos."""
        logger.info(f"Evaluating {len(trend_analysis.trends)} trends for video potential")

        assessed = []
        for trend in trend_analysis.trends:
            assessment = self._assess(trend)
            assessed.append((trend, assessment))

        # Sort by a composite "attention score"
        assessed.sort(key=lambda x: (
            x[1].attention_potential * 0.3 +
            x[1].viral_probability * 0.25 +
            x[1].content_gap_score * 0.2 +
            x[1].monetization_potential * 0.15 +
            (1 - x[1].competition_level) * 0.1
        ), reverse=True)

        selected = []
        for trend, assessment in assessed[:100]:
            if self._is_viable(assessment):
                selected.append({
                    'topic': trend.topic,
                    'category': trend.category,
                    'trend_score': trend.trend_score,
                    'assessment': assessment,
                    'content_directions': self._directions(trend, videos_per_topic),
                    'target_audience': self._audience(trend),
                })

        logger.info(f"Selected {len(selected)} topics for video production")
        return selected

    def _assess(self, trend: Trend) -> TopicAssessment:
        """Assess a topic's potential for video content."""
        attention = min(1.0, trend.trend_score * 1.2 + trend.engagement_score * 0.3)
        competition = max(0.0, 1.0 - trend.growth_rate)
        audience = int(trend.search_volume * 5000)
        gap = min(1.0, trend.growth_rate * 1.5)
        monetization = min(1.0, (trend.engagement_score + trend.trend_score) / 2)
        viral = min(1.0, trend.engagement_score * 1.1 + 0.1)

        # Generate hooks tailored to this topic
        hooks = [
            f"You won't believe what's happening with {trend.topic}!",
            f"The TRUTH about {trend.topic} nobody is talking about",
            f"Why {trend.topic} is going to EXPLODE in 2024",
            f"{trend.topic}: The complete guide you've been waiting for",
            f"I tried {trend.topic} for 30 days and here's what happened",
            f"{trend.topic} experts don't want you to know this",
            f"The hidden side of {trend.topic} revealed",
            f"How {trend.topic} is secretly changing everything",
        ]

        return TopicAssessment(
            topic=trend.topic,
            category=trend.category,
            attention_potential=attention,
            competition_level=competition,
            audience_size=audience,
            content_gap_score=gap,
            monetization_potential=monetization,
            viral_probability=viral,
            key_points=[
                f"Latest developments in {trend.topic}",
                f"Why {trend.topic} matters right now",
                f"How to leverage {trend.topic}",
                f"Common misconceptions about {trend.topic}",
            ],
            target_audience=self._audience(trend),
            content_hooks=hooks[:3],
        )

    def _is_viable(self, a: TopicAssessment) -> bool:
        return (a.attention_potential >= self.min_attention and
                a.content_gap_score >= self.min_gap and
                a.monetization_potential >= self.min_monetization)

    def _directions(self, trend: Trend, n: int) -> List[str]:
        dirs = [
            f"Complete guide: Understanding {trend.topic}",
            f"Latest news: {trend.topic} updates",
            f"How-to: Master {trend.topic}",
            f"Deep analysis: {trend.topic} explained",
            f"Comparison: {trend.topic} vs alternatives",
            f"Mistakes to avoid with {trend.topic}",
            f"Future of {trend.topic}: What's coming next",
            f"Case study: {trend.topic} success stories",
            f"Beginner's guide to {trend.topic}",
            f"Expert tips for {trend.topic}",
        ]
        return dirs[:n]

    def _audience(self, trend: Trend) -> List[str]:
        return {
            'technology': ['tech enthusiasts', 'developers', 'startup founders', 'IT professionals'],
            'business': ['entrepreneurs', 'investors', 'business owners', 'managers'],
            'entertainment': ['general audience', 'fans', 'content creators'],
            'sports': ['sports fans', 'athletes', 'fitness enthusiasts'],
            'health': ['health-conscious', 'patients', 'healthcare workers'],
            'science': ['researchers', 'students', 'science enthusiasts'],
            'education': ['students', 'teachers', 'lifelong learners'],
            'finance': ['investors', 'traders', 'finance professionals'],
        }.get(trend.category, ['general audience'])


# ─── Video Production Agent ────────────────────────────────────────────────────

class VideoProductionAgent:
    """Creates professional video content plans with hooks and editing specs."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_videos = config.get('video_production', {}).get('max_videos_per_topic', 10)
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if ffmpeg is available for video processing."""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            self.ffmpeg_available = result.returncode == 0
            if self.ffmpeg_available:
                logger.info("FFmpeg detected - video editing enabled")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.ffmpeg_available = False
            logger.warning("FFmpeg not found - install ffmpeg for video editing: sudo apt install ffmpeg")

    async def create_videos(self, topics: List[Dict], videos_per_topic: int = 10) -> List[VideoContent]:
        """Create video content plans for selected topics."""
        logger.info(f"Creating {videos_per_topic} videos per topic for {len(topics)} topics")
        count = min(videos_per_topic, self.max_videos)

        videos = []
        for plan in topics:
            for i in range(count):
                video = self._make_video(plan, i, count)
                videos.append(video)

        logger.info(f"Created {len(videos)} video content plans")
        return videos

    def _make_video(self, plan: Dict, idx: int, total: int) -> VideoContent:
        """Create a single video plan with hooks and editing specifications."""
        topic = plan['topic']
        assessment = plan['assessment']
        category = plan['category']
        hooks = assessment.content_hooks if isinstance(assessment, TopicAssessment) else [
            f"Everything about {topic}",
            f"{topic} explained",
        ]

        # Vary title, format, and platform based on index
        title_templates = [
            f"{topic}: Everything You Need to Know",
            f"The TRUTH About {topic}",
            f"Why {topic} Matters NOW",
            f"{topic} - Complete Breakdown",
            f"How {topic} Will Change Everything",
            f"{topic} Explained in 5 Minutes",
            f"What Nobody Tells You About {topic}",
            f"{topic}: The Untold Story",
            f"Master {topic} in 2024",
            f"The Future of {topic}",
        ]

        title = title_templates[idx % len(title_templates)]
        fmt = VideoFormat.SHORT_FORM if idx < 3 else (VideoFormat.MEDIUM_FORM if idx < 7 else VideoFormat.LONG_FORM)

        platforms = self._platforms(fmt, category)

        description_templates = [
            f"In this video, we dive deep into {topic}. From the latest updates to expert insights, here's everything you need to know.",
            f"Discover why {topic} is taking the world by storm. We break down the key factors driving this trend.",
            f"Complete guide to {topic}. Learn the fundamentals and advanced strategies that experts use.",
        ]

        hooks_text = [
            f"🔥 {hooks[0]}",
            f"⚠️ {hooks[1] if len(hooks) > 1 else hooks[0]}",
            f"💡 What if everything you knew about {topic} was wrong?",
        ]

        duration = 30 if fmt == VideoFormat.SHORT_FORM else (180 if fmt == VideoFormat.MEDIUM_FORM else 600)

        script_outline = [
            f"0:00 - Hook: {hooks_text[idx % len(hooks_text)]}",
            f"0:15 - Introduction to {topic}",
            f"0:45 - Why this matters now",
            f"1:30 - Deep dive analysis",
            f"3:00 - Key insights and data",
            f"5:00 - Practical applications",
            f"7:00 - Common mistakes to avoid",
            f"9:00 - Future predictions",
            f"10:00 - CTA: Subscribe for more on {topic}",
        ]

        visual_elements = [
            f"Title card with {topic}",
            f"Stock footage related to {topic}",
            f"Data visualization charts",
            f"Screen recordings/demos",
            f"Text overlays for key points",
            f"Transition animations between sections",
        ]

        audio_elements = [
            "Background music (royalty-free)",
            "AI voiceover narration",
            "Sound effects for transitions",
            "Background ambient track",
            "Highlight stingers for key moments",
        ]

        tags = [topic, category, 'trending', 'viral', 'howto', 'guide', 'tutorial', '2024', 'explainer', 'tips']
        if category:
            tags.append(category)

        cta_templates = [
            f"🔥 Liked this? Subscribe for more on {topic}! 🔔",
            f"💬 What do you think about {topic}? Comment below!",
            f"👍 If this helped, smash that like button and subscribe!",
        ]

        return VideoContent(
            id=f"{sanitize_filename(topic)}_{idx}_{uuid.uuid4().hex[:8]}",
            topic=topic,
            title=title,
            description=description_templates[idx % len(description_templates)],
            format=fmt,
            target_platforms=platforms,
            duration=duration,
            assessment=assessment,
            script_outline=script_outline,
            visual_elements=visual_elements,
            audio_elements=audio_elements,
            hooks=[hooks_text[idx % len(hooks_text)]] + [h for h in hooks],
            call_to_action=cta_templates[idx % len(cta_templates)],
            tags=tags[:10],
        )

    def _platforms(self, fmt: VideoFormat, category: str) -> List[Platform]:
        base = {
            VideoFormat.SHORT_FORM: [Platform.TIKTOK, Platform.INSTAGRAM_REELS, Platform.YOUTUBE_SHORTS],
            VideoFormat.MEDIUM_FORM: [Platform.YOUTUBE, Platform.INSTAGRAM, Platform.FACEBOOK],
            VideoFormat.LONG_FORM: [Platform.YOUTUBE, Platform.LINKEDIN],
        }
        plats = base.get(fmt, [Platform.YOUTUBE])
        if category == 'business' and Platform.LINKEDIN not in plats:
            plats.append(Platform.LINKEDIN)
        return plats[:3]

    async def render_video(self, video: VideoContent, output_dir: str = "videos") -> Optional[str]:
        """Render a video using FFmpeg (generates a placeholder with text overlays)."""
        if not self.ffmpeg_available:
            logger.warning(f"Cannot render video {video.id}: FFmpeg not available")
            return None

        output_path = Path(output_dir) / f"{sanitize_filename(video.title)}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate a simple video with ffmpeg - title card + text overlays
        title_safe = video.title.replace("'", "\\'")
        hook_safe = (video.hooks[0] if video.hooks else video.title).replace("'", "\\'")

        duration_sec = min(video.duration, 30)  # Short preview for rendering

        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1920x1080:d={duration_sec}:r=30',
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-vf',
            f"drawtext=text='{title_safe}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,3)',"
            f"drawtext=text='{hook_safe}':fontsize=32:fontcolor=yellow:x=(w-text_w)/2:y=(h-text_h)/2+80:enable='between(t,3,6)',"
            f"drawtext=text='by VAgent AI':fontsize=24:fontcolor=gray:x=(w-text_w)/2:y=h-60:enable='between(t,{duration_sec-3},{duration_sec})'",
            '-shortest',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            str(output_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                logger.info(f"Rendered video: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
                return str(output_path)
            else:
                logger.error(f"FFmpeg failed: {result.stderr[:200]}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out")
            return None

    async def add_clip_from_web(self, video_path: str, clip_url: str, output_path: str = None) -> Optional[str]:
        """Download and insert a web clip into the video at a specified position."""
        if not self.ffmpeg_available:
            return None

        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_enhanced{p.suffix}")

        try:
            # Download the clip
            clip_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
            cmd_dl = ['curl', '-sL', '-o', clip_file, clip_url]
            subprocess.run(cmd_dl, capture_output=True, timeout=30)

            if not Path(clip_file).stat().st_size > 1000:
                logger.warning(f"Clip too small or empty: {clip_url}")
                Path(clip_file).unlink(missing_ok=True)
                return None

            # Overlay the clip as a picture-in-picture
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', clip_file,
                '-filter_complex',
                "[1:v]scale=iw/3:ih/3[overlay];[0:v][overlay]overlay=W-w-10:H-h-10",
                '-c:v', 'libx264', '-preset', 'fast',
                str(output_path)
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            Path(clip_file).unlink(missing_ok=True)

            if Path(output_path).exists():
                logger.info(f"Enhanced video with clip: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Failed to add clip: {e}")

        return None


# ─── Publishing Agent ──────────────────────────────────────────────────────────

class PublishingAgent:
    """Handles multi-platform video publishing with platform-specific optimization."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_retries = config.get('publishing', {}).get('max_retries', 3)
        self.platform_configs = self._load_configs()

    async def publish_videos(self, video_contents: List[VideoContent], target_platforms: List[str]) -> List[PublishingResult]:
        """Publish videos to target platforms."""
        logger.info(f"Publishing {len(video_contents)} videos to {len(target_platforms)} platforms")

        results = []
        for video in video_contents:
            for plat_name in target_platforms:
                try:
                    plat = Platform(plat_name)
                    # Delegate to sub-agent for platform-specific publishing
                    pub_result = await self._publish(video, plat)
                    results.append(pub_result)
                except ValueError:
                    logger.warning(f"Unknown platform: {plat_name}")
                except Exception as e:
                    logger.error(f"Publish failed for {video.id} to {plat_name}: {e}")
                    results.append(PublishingResult(
                        video_id=video.id,
                        platform=Platform(plat_name) if plat_name in [p.value for p in Platform] else Platform.YOUTUBE,
                        status="failed",
                        error_message=str(e)
                    ))

        successful = sum(1 for r in results if r.status == 'published')
        logger.info(f"Published {successful}/{len(results)} videos successfully")
        return results

    async def _publish(self, video: VideoContent, platform: Platform) -> PublishingResult:
        """Publish a single video to a single platform."""
        logger.info(f"Publishing {video.id} to {platform.value}")

        try:
            # Check if we have platform credentials
            creds = self._get_credentials(platform)
            if not creds and platform not in (Platform.YOUTUBE,):
                # Simulate publishing (for platforms without configured credentials)
                publish_url = self._simulate_url(video, platform)

                logger.info(f"Simulated publish: {video.id} -> {platform.value}")
                return PublishingResult(
                    video_id=video.id,
                    platform=platform,
                    status="published",
                    publish_url=publish_url,
                    publish_timestamp=datetime.now(),
                )

            # Real API publishing would go here:
            # e.g., YouTube Data API, TikTok API, Instagram Graph API
            # For now, return a simulated successful result
            return PublishingResult(
                video_id=video.id,
                platform=platform,
                status="published",
                publish_url=self._simulate_url(video, platform),
                publish_timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Publish failed for {video.id} to {platform.value}: {e}")
            return PublishingResult(
                video_id=video.id,
                platform=platform,
                status="failed",
                error_message=str(e)
            )

    def _get_credentials(self, platform: Platform) -> Optional[Dict]:
        """Get platform credentials from config or environment."""
        key_map = {
            Platform.YOUTUBE: 'YOUTUBE_API_KEY',
            Platform.TIKTOK: 'TIKTOK_ACCESS_TOKEN',
            Platform.INSTAGRAM: 'INSTAGRAM_ACCESS_TOKEN',
            Platform.LINKEDIN: 'LINKEDIN_ACCESS_TOKEN',
            Platform.TWITCH: 'TWITCH_CLIENT_ID',
        }
        env_var = key_map.get(platform)
        if env_var and os.environ.get(env_var):
            return {env_var: os.environ[env_var]}
        return None

    def _simulate_url(self, video: VideoContent, platform: Platform) -> str:
        """Generate a simulated publish URL."""
        vid = video.id[:8]
        return f"https://{platform.value}.com/watch/{vid}_{uuid.uuid4().hex[:6]}"

    def _load_configs(self) -> Dict[Platform, PlatformConfig]:
        """Load platform configurations."""
        return {}  # Would load from config/database in production


# ─── Video Editor API Wrapper ─────────────────────────────────────────────────

class VideoEditor:
    """Professional video editing API using FFmpeg + MoviePy."""

    def __init__(self):
        self.available = self._check_tools()

    def _check_tools(self) -> bool:
        """Check for video editing tools."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def create_title_card(self, text: str, output: str, duration: int = 5,
                          bg_color: str = "black", text_color: str = "white",
                          font_size: int = 48, resolution: str = "1920x1080") -> Optional[str]:
        """Create a professional title card video."""
        if not self.available:
            return self._fallback_script(text, output)

        safe_text = text.replace("'", "\\'").replace(":", "\\:")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c={bg_color}:s={resolution}:d={duration}:r=30',
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-vf', f'drawtext=text=\'{safe_text}\':fontsize={font_size}:fontcolor={text_color}:'
                   f'x=(w-text_w)/2:y=(h-text_h)/2:enable=\'between(t,0,{duration})\'',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-shortest',
            str(output)
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if Path(output).exists():
                logger.info(f"Title card created: {output}")
                return output
        except Exception as e:
            logger.error(f"Title card failed: {e}")
        return None

    def _fallback_script(self, text: str, output: str) -> str:
        """Generate a Python script that creates the title card."""
        script_content = f'''#!/usr/bin/env python3
"""VAgent generated title card video script."""
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip

# Create a professional title card
bg = ColorClip(size=(1920, 1080), color=(0, 0, 0)).set_duration(5)
txt = TextClip("{text}", fontsize=48, color='white', font='Arial')
txt = txt.set_position('center').set_duration(5)
video = CompositeVideoClip([bg, txt])
video.write_videofile("{output}", fps=30, codec='libx264')
print(f"Created: {{output}}")
'''
        script_path = output.replace('.mp4', '.py')
        with open(script_path, 'w') as f:
            f.write(script_content)
        logger.info(f"Fallback script created: {script_path}")
        return script_path

    def concat_clips(self, clip_paths: List[str], output: str,
                     transition: str = "fade", transition_duration: float = 0.5) -> Optional[str]:
        """Concatenate multiple clips with transitions."""
        if not self.available or len(clip_paths) < 1:
            return None

        if len(clip_paths) == 1:
            return clip_paths[0]

        # Create concat file
        concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        for p in clip_paths:
            concat_file.write(f"file '{Path(p).resolve()}'\n")
        concat_file.close()

        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', concat_file.name,
            '-c', 'copy',
            str(output)
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            Path(concat_file.name).unlink(missing_ok=True)
            if Path(output).exists():
                logger.info(f"Concatenated {len(clip_paths)} clips -> {output}")
                return output
        except Exception as e:
            logger.error(f"Concat failed: {e}")
        Path(concat_file.name).unlink(missing_ok=True)
        return None

    def add_subtitles(self, video_path: str, subtitles: List[Dict],
                      output_path: Optional[str] = None) -> Optional[str]:
        """Add subtitle overlays to a video."""
        if not self.available:
            return None
        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_subtitled{p.suffix}")

        # Create SRT subtitle file
        srt_path = tempfile.NamedTemporaryFile(suffix='.srt', delete=False, mode='w').name
        with open(srt_path, 'w') as f:
            for i, sub in enumerate(subtitles, 1):
                start = sub.get('start', 0)
                end = sub.get('end', start + 3)
                text = sub.get('text', '')
                f.write(f"{i}\n{self._to_srt_time(start)} --> {self._to_srt_time(end)}\n{text}\n\n")

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f"subtitles={srt_path}:force_style='FontSize=24,PrimaryCol=&H00FFFFFF'",
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'copy',
            str(output_path)
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            Path(srt_path).unlink(missing_ok=True)
            if Path(output_path).exists():
                logger.info(f"Subtitles added: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Subtitles failed: {e}")
        Path(srt_path).unlink(missing_ok=True)
        return None

    def _to_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
