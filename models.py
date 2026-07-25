#!/usr/bin/env python3
"""
VAgent Data Models

Defines the data structures used throughout the VAgent system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ResearchPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class VideoFormat(Enum):
    SHORT_FORM = "short_form"  # TikTok, Reels, Shorts
    MEDIUM_FORM = "medium_form"  # YouTube, regular videos
    LONG_FORM = "long_form"  # Educational, documentaries
    LIVE_STREAM = "live_stream"


class Platform(Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    TWITCH = "twitch"
    X_TWITTER = "x_twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM_REELS = "instagram_reels"
    TWITCH_CLIP = "twitch_clip"


@dataclass
class ResearchTask:
    """Represents a web research task."""
    id: str
    category: str
    query: str
    max_websites: int = 100
    priority: ResearchPriority = ResearchPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"
    results: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'query': self.query,
            'max_websites': self.max_websites,
            'priority': self.priority.value,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'results': self.results
        }


@dataclass
class ResearchResult:
    """Represents a single research result from a website."""
    url: str
    title: str
    content: str
    category: str
    relevance_score: float
    publish_date: Optional[datetime] = None
    engagement_metrics: Dict[str, Any] = field(default_factory=dict)
    sentiment_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'relevance_score': self.relevance_score,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'engagement_metrics': self.engagement_metrics,
            'sentiment_score': self.sentiment_score,
            'tags': self.tags
        }


@dataclass
class Trend:
    """Represents a trending topic."""
    topic: str
    category: str
    trend_score: float
    growth_rate: float
    search_volume: int
    engagement_score: float
    related_topics: List[str] = field(default_factory=list)
    content_examples: List[str] = field(default_factory=list)
    predicted_trajectory: str = "rising"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'topic': self.topic,
            'category': self.category,
            'trend_score': self.trend_score,
            'growth_rate': self.growth_rate,
            'search_volume': self.search_volume,
            'engagement_score': self.engagement_score,
            'related_topics': self.related_topics,
            'content_examples': self.content_examples,
            'predicted_trajectory': self.predicted_trajectory
        }


@dataclass
class TrendAnalysis:
    """Complete trend analysis results."""
    timestamp: datetime = field(default_factory=datetime.now)
    trends: List[Trend] = field(default_factory=list)
    top_categories: Dict[str, float] = field(default_factory=dict)
    market_insights: Dict[str, Any] = field(default_factory=dict)
    confidence_level: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'trends': [trend.to_dict() for trend in self.trends],
            'top_categories': self.top_categories,
            'market_insights': self.market_insights,
            'confidence_level': self.confidence_level
        }


@dataclass
class TopicAssessment:
    """Assessment of a topic for video content potential."""
    topic: str
    category: str
    attention_potential: float  # 0-1 scale
    competition_level: float  # 0-1 scale
    audience_size: int
    content_gap_score: float  # 0-1 scale
    monetization_potential: float  # 0-1 scale
    viral_probability: float  # 0-1 scale
    key_points: List[str] = field(default_factory=list)
    target_audience: List[str] = field(default_factory=list)
    content_hooks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'topic': self.topic,
            'category': self.category,
            'attention_potential': self.attention_potential,
            'competition_level': self.competition_level,
            'audience_size': self.audience_size,
            'content_gap_score': self.content_gap_score,
            'monetization_potential': self.monetization_potential,
            'viral_probability': self.viral_probability,
            'key_points': self.key_points,
            'target_audience': self.target_audience,
            'content_hooks': self.content_hooks
        }


@dataclass
class VideoContent:
    """Represents a video content plan."""
    id: str
    topic: str
    title: str
    description: str
    format: VideoFormat
    target_platforms: List[Platform]
    duration: int  # seconds
    assessment: TopicAssessment
    script_outline: List[str] = field(default_factory=list)
    visual_elements: List[str] = field(default_factory=list)
    audio_elements: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    call_to_action: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "planning"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'topic': self.topic,
            'title': self.title,
            'description': self.description,
            'format': self.format.value,
            'target_platforms': [platform.value for platform in self.target_platforms],
            'duration': self.duration,
            'assessment': self.assessment.to_dict(),
            'script_outline': self.script_outline,
            'visual_elements': self.visual_elements,
            'audio_elements': self.audio_elements,
            'hooks': self.hooks,
            'call_to_action': self.call_to_action,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'status': self.status
        }


@dataclass
class PlatformConfig:
    """Configuration for publishing platforms."""
    platform: Platform
    account_credentials: Dict[str, Any] = field(default_factory=dict)
    publishing_guidelines: Dict[str, Any] = field(default_factory=dict)
    optimal_posting_times: List[str] = field(default_factory=list)
    content_requirements: Dict[str, Any] = field(default_factory=dict)
    audience_demographics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'platform': self.platform.value,
            'account_credentials': self.account_credentials,
            'publishing_guidelines': self.publishing_guidelines,
            'optimal_posting_times': self.optimal_posting_times,
            'content_requirements': self.content_requirements,
            'audience_demographics': self.audience_demographics
        }


@dataclass
class PublishingResult:
    """Result of video publishing to a platform."""
    video_id: str
    platform: Platform
    status: str  # "published", "failed", "pending"
    publish_url: Optional[str] = None
    publish_timestamp: Optional[datetime] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'video_id': self.video_id,
            'platform': self.platform.value,
            'status': self.status,
            'publish_url': self.publish_url,
            'publish_timestamp': self.publish_timestamp.isoformat() if self.publish_timestamp else None,
            'views': self.views,
            'likes': self.likes,
            'comments': self.comments,
            'shares': self.shares,
            'error_message': self.error_message
        }