#!/usr/bin/env python3
"""
VAgent - Multi-Agent Video Content Creation System

Main entry point.  Orchestrates the full pipeline:
  research → trend analysis → content strategy → video production → publishing
"""

import asyncio
import argparse
import logging
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Ensure hermes-agent root is on sys.path so `from vagent.*` works
_this_dir = Path(__file__).absolute().parent  # vagent/
_root_dir = _this_dir.parent                    # hermes-agent/
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from vagent.core import VAgentOrchestrator
from vagent.agents import VideoEditor
from vagent.utils import setup_logging

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description='VAgent - Multi-Agent Video Content Creation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Full pipeline (research 10k sites → 100 trends → 1000 videos → publish)
  python main.py --websites 10000 --trends 100 --videos-per-topic 10

  # Research only
  python main.py --phase research --websites 100 --output-dir /tmp/vagent

  # Trend analysis on existing data
  python main.py --phase trends --input research_results.json

  # Video production from existing topics
  python main.py --phase produce --topics topics.json --videos-per-topic 10

  # Render videos with FFmpeg
  python main.py --phase render --input video_plans.json --output-dir videos

  # Publish videos
  python main.py --phase publish --input videos.json --platforms youtube,tiktok

  # Quick dry-run test
  python main.py --phase test

  # Install dependencies
  python main.py --install
        """
    )

    parser.add_argument('--websites', type=int, default=10000,
                        help='Number of websites to research')
    parser.add_argument('--trends', type=int, default=100,
                        help='Number of trending topics to identify')
    parser.add_argument('--videos-per-topic', type=int, default=10,
                        help='Number of videos per topic')
    parser.add_argument('--platforms', type=str, default='youtube,tiktok,instagram,linkedin',
                        help='Comma-separated target platforms')
    parser.add_argument('--phase', type=str, default='full',
                        choices=['full', 'research', 'trends', 'strategy', 'produce',
                                 'render', 'publish', 'test', 'all'],
                        help='Pipeline phase to run')
    parser.add_argument('--output-dir', type=str, default='vagent_results',
                        help='Output directory for results')
    parser.add_argument('--input', type=str, default=None,
                        help='Input JSON file (for partial pipeline runs)')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to custom config file')
    parser.add_argument('--install', action='store_true',
                        help='Print installation instructions and exit')
    parser.add_argument('--version', action='version',
                        version='VAgent 1.0.0')

    return parser.parse_args()


async def main():
    args = parse_args()

    if args.install:
        print_install_instructions()
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize orchestrator
    orchestrator = VAgentOrchestrator(config_path=args.config)
    orchestrator.start_time = datetime.now()

    if args.phase == 'research' or args.phase in ('full', 'all'):
        logger.info(f"=== PHASE: Research ({args.websites} websites) ===")
        research_results = await orchestrator.run_research_only(args.websites)
        save_json(output_dir / 'research_results.json', {"results": [r.to_dict() for r in research_results]})
        logger.info(f"Research complete: {len(research_results)} results")

    if args.phase == 'trends' or args.phase in ('full', 'all'):
        logger.info(f"=== PHASE: Trend Analysis (top {args.trends} trends) ===")
        if args.input and (args.phase == 'trends' or not hasattr(orchestrator, 'research_results') or not orchestrator.research_results):
            data = load_json(Path(args.input))
            research_results = [ResearchResult.from_dict(r) for r in data.get('results', [])]
        else:
            research_results = getattr(orchestrator, 'research_results', [])

        analysis = await orchestrator.run_trend_analysis_only(research_results, args.trends)
        save_json(output_dir / 'trend_analysis.json', analysis.to_dict())
        logger.info(f"Trend analysis: {len(analysis.trends)} trends (confidence: {analysis.confidence_level:.2f})")

    if args.phase == 'strategy' or args.phase in ('full', 'all'):
        logger.info(f"=== PHASE: Content Strategy ===")
        analysis_data = load_json(output_dir / 'trend_analysis.json')
        analysis = TrendAnalysis.from_dict(analysis_data)
        topics = await orchestrator.content_strategist.select_topics(analysis, args.videos_per_topic)
        save_json(output_dir / 'selected_topics.json', {"topics": topics})
        logger.info(f"Content strategy: {len(topics)} topics selected")

    if args.phase in ('produce', 'render') or args.phase in ('full', 'all'):
        logger.info(f"=== PHASE: Video Production ({args.videos_per_topic} videos/topic) ===")
        topics_data = load_json(output_dir / 'selected_topics.json')
        topics = topics_data.get('topics', [])
        videos = await orchestrator.create_videos_only(topics, args.videos_per_topic)
        save_json(output_dir / 'video_plans.json', {"videos": [v.to_dict() for v in videos]})
        logger.info(f"Video production: {len(videos)} videos planned")

    if args.phase == 'render' or args.phase in ('full', 'all'):
        logger.info(f"=== PHASE: Video Rendering ===")
        videos_data = load_json(output_dir / 'video_plans.json')
        from vagent.models import VideoContent
        videos = [VideoContent.from_dict(v) for v in videos_data.get('videos', [])]
        rendered = await orchestrator.render_all_videos(videos, str(output_dir / 'rendered_videos'))
        save_json(output_dir / 'rendered_videos.json', {"paths": rendered})
        logger.info(f"Rendering: {len(rendered)}/{len(videos)} videos rendered")

    if args.phase == 'publish' or args.phase in ('full', 'all'):
        logger.info(f"=== PHASE: Publishing ({args.platforms}) ===")
        platforms = [p.strip() for p in args.platforms.split(',')]
        videos_data = load_json(output_dir / 'video_plans.json')
        from vagent.models import VideoContent
        videos = [VideoContent.from_dict(v) for v in videos_data.get('videos', [])]
        results = await orchestrator.publisher.publish_videos(videos, platforms)
        logger.info(f"Publishing: {sum(1 for r in results if r.status == 'published')}/{len(results)} published")

    if args.phase == 'test':
        logger.info("=== PHASE: System Test ===")
        await run_diagnostics()

    # Print summary
    duration = datetime.now() - orchestrator.start_time
    print(f"\n{'='*50}")
    print(f"VAgent Pipeline Complete ({duration.total_seconds():.1f}s)")
    print(f"Results saved to: {output_dir.resolve()}")
    print(f"{'='*50}")


async def run_diagnostics():
    """Run system diagnostics to verify all components."""
    print("VAgent System Diagnostics\n")

    # Check Python version
    print(f"Python: {sys.version}")

    # Check core modules
    tests = [
        ("vagent.core", "VAgentOrchestrator"),
        ("vagent.agents", "ResearchCoordinator, TrendAnalysisAgent, ContentStrategyAgent"),
        ("vagent.agents", "VideoProductionAgent, PublishingAgent, VideoEditor"),
        ("vagent.models", "ResearchTask, TrendAnalysis, VideoContent"),
        ("vagent.utils", "load_config, setup_logging"),
    ]
    for module, names in tests:
        try:
            __import__(module)
            print(f"  ✓ {module} ({names})")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")

    # Check FFmpeg
    import subprocess
    try:
        r = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        print(f"  ✓ FFmpeg: {r.stdout.split(chr(10))[0] if r.returncode == 0 else 'not found'}")
    except:
        print("  ⚠ FFmpeg: not installed (install: sudo apt install ffmpeg)")

    # Check Hermes tools
    try:
        from tools.web_tools import web_search_tool
        print(f"  ✓ Hermes web tools available")
    except ImportError as e:
        print(f"  ⚠ Hermes web tools: {e}")

    print("\nSystem diagnostics complete.")


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"Saved: {path}")


def load_json(path: Path) -> dict:
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return {}
    with open(path) as f:
        return json.load(f)


def print_install_instructions():
    print("""
VAgent Installation
====================

1. Core dependencies:
   pip install -r vagent/requirements.txt

2. Video editing (recommended):
   sudo apt install ffmpeg
   pip install moviepy opencv-python pillow numpy

3. Run:
   python vagent/main.py --help

4. Quick test:
   python vagent/main.py --phase test

5. Full pipeline (dry-run with 100 websites):
   python vagent/main.py --websites 100 --trends 10 --videos-per-topic 3
""")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nVAgent interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"VAgent failed: {e}")
        sys.exit(1)
