#!/usr/bin/env python3
"""
VAgent Core Orchestrator

Coordinates multiple agents for comprehensive web research and video production.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from vagent.agents import ResearchCoordinator, TrendAnalysisAgent, ContentStrategyAgent
from vagent.agents import VideoProductionAgent, PublishingAgent
from vagent.models import ResearchTask, TrendAnalysis, VideoContent, PlatformConfig
from vagent.utils import load_config, setup_logging

logger = logging.getLogger(__name__)


class VAgentOrchestrator:
    """
    Main orchestrator for the VAgent multi-agent system.
    
    Coordinates research, trend analysis, content strategy, video production,
    and publishing across multiple agents.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the orchestrator with configuration."""
        self.config = load_config(config_path)
        setup_logging(self.config)
        
        # Initialize agents
        self.research_coordinator = ResearchCoordinator(self.config)
        self.trend_analyzer = TrendAnalysisAgent(self.config)
        self.content_strategist = ContentStrategyAgent(self.config)
        self.video_producer = VideoProductionAgent(self.config)
        self.publisher = PublishingAgent(self.config)
        
        # State tracking
        self.research_results = []
        self.trend_analysis = None
        self.selected_topics = []
        self.video_contents = []
        self.publishing_results = []
        
        logger.info("VAgent Orchestrator initialized successfully")
    
    async def run_full_pipeline(self, 
                              research_websites: int = 10000,
                              top_trends: int = 100,
                              videos_per_topic: int = 10,
                              target_platforms: List[str] = None) -> Dict[str, Any]:
        """
        Run the complete pipeline from web research to video publishing.
        
        Args:
            research_websites: Number of websites to research
            top_trends: Number of trending topics to analyze
            videos_per_topic: Number of videos to create per topic
            target_platforms: List of platforms to publish to
            
        Returns:
            Dictionary containing all results from the pipeline
        """
        logger.info(f"Starting VAgent pipeline with {research_websites} websites")
        
        # Phase 1: Web Research
        logger.info("Phase 1: Web Research")
        research_tasks = await self._create_research_tasks(research_websites)
        self.research_results = await self.research_coordinator.execute_research(research_tasks)
        
        # Phase 2: Trend Analysis
        logger.info("Phase 2: Trend Analysis")
        self.trend_analysis = await self.trend_analyzer.analyze_trends(
            self.research_results, 
            top_trends
        )
        
        # Phase 3: Content Strategy
        logger.info("Phase 3: Content Strategy")
        self.selected_topics = await self.content_strategist.select_topics(
            self.trend_analysis,
            videos_per_topic
        )
        
        # Phase 4: Video Production
        logger.info("Phase 4: Video Production")
        self.video_contents = await self.video_producer.create_videos(
            self.selected_topics,
            videos_per_topic
        )
        
        # Phase 5: Publishing
        logger.info("Phase 5: Publishing")
        if target_platforms is None:
            target_platforms = self.config.get('publishing', {}).get('platforms', ['youtube'])
            
        self.publishing_results = await self.publisher.publish_videos(
            self.video_contents,
            target_platforms
        )
        
        # Compile results
        results = {
            'research_websites_analyzed': research_websites,
            'trends_analyzed': len(self.trend_analysis.trends),
            'topics_selected': len(self.selected_topics),
            'videos_created': len(self.video_contents),
            'videos_published': len(self.publishing_results),
            'research_results': self.research_results,
            'trend_analysis': self.trend_analysis,
            'selected_topics': self.selected_topics,
            'video_contents': self.video_contents,
            'publishing_results': self.publishing_results,
            'pipeline_duration': str(datetime.now() - self.start_time) if hasattr(self, 'start_time') else None
        }
        
        logger.info("VAgent pipeline completed successfully")
        return results
    
    async def run_research_only(self, num_websites: int = 10000) -> List[Dict]:
        """Run only the research phase."""
        logger.info(f"Running research phase for {num_websites} websites")
        
        research_tasks = await self._create_research_tasks(num_websites)
        return await self.research_coordinator.execute_research(research_tasks)
    
    async def run_trend_analysis_only(self, research_results: List[Dict], top_n: int = 100) -> TrendAnalysis:
        """Run only the trend analysis phase."""
        logger.info(f"Analyzing trends for top {top_n} topics")
        return await self.trend_analyzer.analyze_trends(research_results, top_n)
    
    async def create_videos_only(self, topics: List[Dict], videos_per_topic: int = 10) -> List[VideoContent]:
        """Run only the video production phase."""
        logger.info(f"Creating {videos_per_topic} videos per topic for {len(topics)} topics")
        return await self.video_producer.create_videos(topics, videos_per_topic)

    async def render_all_videos(self, video_contents: List[VideoContent], output_dir: str = "videos") -> List[str]:
        """Render all video content to actual video files using FFmpeg."""
        logger.info(f"Rendering {len(video_contents)} videos to {output_dir}")
        rendered = []
        for video in video_contents:
            path = await self.video_producer.render_video(video, output_dir)
            if path:
                rendered.append(path)
        logger.info(f"Rendered {len(rendered)}/{len(video_contents)} videos")
        return rendered

    async def delegate_research(self, goal: str, context: str) -> Any:
        """Delegate a research task to a Hermes sub-agent."""
        try:
            from run_agent import AIAgent
            # Use the built-in Hermes AI agent for research
            agent = AIAgent()
            result = agent.chat(f"{goal}\n\nContext: {context}")
            return result
        except ImportError:
            logger.warning("AIAgent not available, using direct research")
            return None
    
    async def _create_research_tasks(self, num_websites: int) -> List[ResearchTask]:
        """Create research tasks for the specified number of websites."""
        # This would typically involve generating diverse search queries
        # and categorizing websites by topic
        
        # For now, create a simple distribution of research tasks
        categories = [
            'technology', 'business', 'entertainment', 'sports', 'health',
            'science', 'politics', 'education', 'finance', 'lifestyle'
        ]
        
        tasks = []
        websites_per_category = max(1, num_websites // len(categories))
        
        for category in categories:
            for i in range(websites_per_category):
                task = ResearchTask(
                    id=f"{category}_{i}",
                    category=category,
                    query=f"trending {category} news and updates",
                    max_websites=max(1, websites_per_category // 5),
                    priority=i % 3 + 1  # Priority 1-3
                )
                tasks.append(task)
        
        logger.info(f"Created {len(tasks)} research tasks")
        return tasks[:num_websites]  # Limit to requested number
    
    def save_results(self, results: Dict[str, Any], output_path: str = "vagent_results.json"):
        """Save pipeline results to a JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Results saved to {output_file}")
        return output_file