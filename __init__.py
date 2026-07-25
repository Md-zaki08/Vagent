"""
VAgent Multi-Agent System - Automated Content Creation Pipeline

A comprehensive multi-agent system for automated web research, trend analysis,
AI-powered video production, and multi-platform publishing.

Components:
  - VAgentOrchestrator: Main coordinator
  - ResearchCoordinator: Parallel web research via delegate_task
  - TrendAnalysisAgent: AI-powered trend identification
  - ContentStrategyAgent: Video topic selection & optimization
  - VideoProductionAgent: Professional video content planning + FFmpeg rendering
  - VideoEditor: FFmpeg/MoviePy video editing (title cards, subtitles, concat)
  - PublishingAgent: Multi-platform video publishing
"""

from vagent.core import VAgentOrchestrator
from vagent.agents import (
    ResearchCoordinator,
    ResearchAgent,
    TrendAnalysisAgent,
    ContentStrategyAgent,
    VideoProductionAgent,
    PublishingAgent,
    VideoEditor,
)
from vagent.models import (
    ResearchTask,
    ResearchResult,
    Trend,
    TrendAnalysis,
    TopicAssessment,
    VideoContent,
    PlatformConfig,
    PublishingResult,
    Platform,
    VideoFormat,
    ResearchPriority,
)
from vagent.utils import (
    load_config,
    setup_logging,
    validate_config,
    ensure_directories,
    format_duration,
    sanitize_filename,
)
from vagent.video import VideoFrameRenderer, ScriptGenerator
from vagent.source_discovery import SourceDiscovery

__all__ = [
    'VAgentOrchestrator',
    'ResearchCoordinator',
    'ResearchAgent',
    'TrendAnalysisAgent',
    'ContentStrategyAgent',
    'VideoProductionAgent',
    'PublishingAgent',
    'VideoEditor',
    'ResearchTask',
    'ResearchResult',
    'Trend',
    'TrendAnalysis',
    'TopicAssessment',
    'VideoContent',
    'PlatformConfig',
    'PublishingResult',
    'Platform',
    'VideoFormat',
    'ResearchPriority',
    'load_config',
    'setup_logging',
    'validate_config',
    'ensure_directories',
    'format_duration',
    'sanitize_filename',
]

__version__ = "1.0.0"
