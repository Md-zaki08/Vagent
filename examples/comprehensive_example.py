#!/usr/bin/env python3
"""
VAgent Example - Comprehensive Demo

This script demonstrates the complete VAgent pipeline with a realistic example.
It shows how to research trending topics, analyze them, create video content,
and publish to multiple platforms.
"""

import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime

# Import VAgent components
from vagent.core import VAgentOrchestrator
from vagent.models import ResearchTask, Trend, VideoContent
from vagent.utils import setup_logging, load_config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def example_research_phase():
    """Demonstrate the research phase with realistic example."""
    logger.info("🔍 Starting Research Phase Example")
    
    # Initialize orchestrator
    orchestrator = VAgentOrchestrator()
    
    # Create realistic research tasks
    research_tasks = [
        ResearchTask(
            id="tech_trends_2024",
            category="technology",
            query="latest AI trends 2024 machine learning breakthrough",
            max_websites=200,
            priority=3
        ),
        ResearchTask(
            id="business_innovation",
            category="business", 
            query="startup innovations fintech disruption 2024",
            max_websites=150,
            priority=2
        ),
        ResearchTask(
            id="health_tech",
            category="health",
            query="digital health telemedicine AI healthcare 2024",
            max_websites=180,
            priority=2
        ),
        ResearchTask(
            id="sustainable_tech",
            category="technology",
            query="sustainable technology green energy innovation 2024",
            max_websites=120,
            priority=1
        )
    ]
    
    logger.info(f"Created {len(research_tasks)} research tasks")
    
    # Execute research (using smaller numbers for demo)
    research_results = await orchestrator.research_coordinator.execute_research(research_tasks)
    
    logger.info(f"Research completed! Found {len(research_results)} results")
    
    # Save research results
    output_file = Path("example_research_results.json")
    with open(output_file, 'w') as f:
        json.dump([result.to_dict() for result in research_results], f, indent=2, default=str)
    
    logger.info(f"Research results saved to {output_file}")
    return research_results


async def example_trend_analysis(research_results):
    """Demonstrate trend analysis with example data."""
    logger.info("📈 Starting Trend Analysis Example")
    
    # Analyze trends from research results
    trend_analysis = await orchestrator.trend_analyzer.analyze_trends(
        research_results, 
        top_n=20  # Analyze top 20 trends for demo
    )
    
    logger.info(f"Trend analysis completed! Found {len(trend_analysis.trends)} trends")
    
    # Print top trends
    logger.info("Top 5 trending topics:")
    for i, trend in enumerate(trend_analysis.trends[:5], 1):
        logger.info(f"{i}. {trend.topic} (Score: {trend.trend_score:.2f})")
    
    # Save trend analysis
    output_file = Path("example_trend_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(trend_analysis.to_dict(), f, indent=2, default=str)
    
    logger.info(f"Trend analysis saved to {output_file}")
    return trend_analysis


async def example_content_strategy(trend_analysis):
    """Demonstrate content strategy selection."""
    logger.info("🎯 Starting Content Strategy Example")
    
    # Select topics for video production
    selected_topics = await orchestrator.content_strategist.select_topics(
        trend_analysis,
        videos_per_topic=3  # Create 3 videos per topic for demo
    )
    
    logger.info(f"Selected {len(selected_topics)} topics for video production")
    
    # Print selected topics
    logger.info("Selected topics for video production:")
    for i, topic in enumerate(selected_topics[:5], 1):
        logger.info(f"{i}. {topic['topic']} (Attention: {topic['assessment']['attention_potential']:.2f})")
    
    # Save content strategy
    output_file = Path("example_content_strategy.json")
    with open(output_file, 'w') as f:
        json.dump(selected_topics, f, indent=2, default=str)
    
    logger.info(f"Content strategy saved to {output_file}")
    return selected_topics


async def example_video_production(selected_topics):
    """Demonstrate video production."""
    logger.info("🎬 Starting Video Production Example")
    
    # Create video content plans
    video_contents = await orchestrator.video_producer.create_videos(
        selected_topics,
        videos_per_topic=2  # Create 2 videos per topic for demo
    )
    
    logger.info(f"Created {len(video_contents)} video content plans")
    
    # Print sample video plans
    logger.info("Sample video plans:")
    for i, video in enumerate(video_contents[:3], 1):
        logger.info(f"{i}. {video.title} ({video.format.value}, {video.duration}s)")
        logger.info(f"   Hooks: {video.hooks}")
        logger.info(f"   Platforms: {[p.value for p in video.target_platforms]}")
    
    # Save video production results
    output_file = Path("example_video_production.json")
    with open(output_file, 'w') as f:
        json.dump([video.to_dict() for video in video_contents], f, indent=2, default=str)
    
    logger.info(f"Video production results saved to {output_file}")
    return video_contents


async def example_publishing(video_contents):
    """Demonstrate publishing to platforms."""
    logger.info("📤 Starting Publishing Example")
    
    # Define target platforms for demo
    target_platforms = ["youtube", "tiktok", "instagram"]
    
    # Simulate publishing (in production, this would use actual APIs)
    publishing_results = await orchestrator.publisher.publish_videos(
        video_contents,
        target_platforms
    )
    
    # Count successful publishes
    successful_publishes = [r for r in publishing_results if r.status == "published"]
    
    logger.info(f"Publishing completed! {len(successful_publishes)}/{len(publishing_results)} videos published")
    
    # Print publishing results
    logger.info("Publishing results:")
    for result in successful_publishes[:5]:
        logger.info(f"✅ {result.video_id} -> {result.platform.value}")
    
    # Save publishing results
    output_file = Path("example_publishing_results.json")
    with open(output_file, 'w') as f:
        json.dump([result.to_dict() for result in publishing_results], f, indent=2, default=str)
    
    logger.info(f"Publishing results saved to {output_file}")
    return publishing_results


async def example_full_pipeline():
    """Run the complete pipeline with example data."""
    logger.info("🚀 Starting Full VAgent Pipeline Example")
    
    # Initialize orchestrator
    orchestrator = VAgentOrchestrator()
    
    # Record start time
    start_time = datetime.now()
    
    try:
        # Run complete pipeline with smaller numbers for demo
        results = await orchestrator.run_full_pipeline(
            research_websites=1000,  # Reduced for demo
            top_trends=20,           # Reduced for demo
            videos_per_topic=2,      # Reduced for demo
            target_platforms=["youtube", "tiktok", "instagram"]
        )
        
        # Calculate duration
        duration = datetime.now() - start_time
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("VAGENT FULL PIPELINE - EXAMPLE RESULTS")
        logger.info("="*60)
        logger.info(f"Duration: {duration}")
        logger.info(f"Websites researched: {results.get('research_websites_analyzed', 'N/A')}")
        logger.info(f"Trends analyzed: {results.get('trends_analyzed', 'N/A')}")
        logger.info(f"Topics selected: {results.get('topics_selected', 'N/A')}")
        logger.info(f"Videos created: {results.get('videos_created', 'N/A')}")
        logger.info(f"Videos published: {results.get('videos_published', 'N/A')}")
        
        # Save complete results
        output_file = orchestrator.save_results(results, "example_full_pipeline.json")
        logger.info(f"Complete results saved to: {output_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


async def example_custom_configuration():
    """Example using custom configuration."""
    logger.info("⚙️ Starting Custom Configuration Example")
    
    # Create custom configuration
    custom_config = {
        'research': {
            'max_concurrent': 10,
            'batch_size': 5,
            'categories': ['technology', 'business']
        },
        'trend_analysis': {
            'max_trends': 10
        },
        'content_strategy': {
            'videos_per_topic': 2
        },
        'video_production': {
            'formats': ['short_form', 'medium_form']
        },
        'publishing': {
            'platforms': ['youtube', 'tiktok']
        }
    }
    
    # Save custom config
    config_file = Path("example_custom_config.yaml")
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(custom_config, f, default_flow_style=False)
    
    logger.info(f"Custom configuration saved to {config_file}")
    
    # Use custom configuration
    orchestrator = VAgentOrchestrator(str(config_file))
    
    # Run with custom settings
    results = await orchestrator.run_research_only(100)
    
    logger.info(f"Custom research completed! Found {len(results)} results")
    
    return results


async def main():
    """Main example function."""
    print("🎬 VAgent Example Suite")
    print("=" * 50)
    
    # Example 1: Individual phases
    print("\n1. Research Phase Example")
    research_results = await example_research_phase()
    
    print("\n2. Trend Analysis Example")
    trend_analysis = await example_trend_analysis(research_results)
    
    print("\n3. Content Strategy Example")
    selected_topics = await example_content_strategy(trend_analysis)
    
    print("\n4. Video Production Example")
    video_contents = await example_video_production(selected_topics)
    
    print("\n5. Publishing Example")
    publishing_results = await example_publishing(video_contents)
    
    # Example 2: Full pipeline
    print("\n6. Full Pipeline Example")
    full_results = await example_full_pipeline()
    
    # Example 3: Custom configuration
    print("\n7. Custom Configuration Example")
    custom_results = await example_custom_configuration()
    
    # Summary
    print("\n" + "="*60)
    print("VAGENT EXAMPLE SUITE - COMPLETED")
    print("="*60)
    print("All examples completed successfully!")
    print("Check the generated JSON files for detailed results:")
    print("- example_research_results.json")
    print("- example_trend_analysis.json")
    print("- example_content_strategy.json")
    print("- example_video_production.json")
    print("- example_publishing_results.json")
    print("- example_full_pipeline.json")
    print("- example_custom_config.yaml")


if __name__ == "__main__":
    # Run the example suite
    asyncio.run(main())