#!/usr/bin/env python3
"""
VAgent Utilities - Core helper functions.

Common utilities and helper functions for the VAgent system.
Uses vutil prefix to avoid shadowing Hermes' utils.py.
"""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "default.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        config = create_default_config()
        save_config(config, config_path)
        return config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() in ('.yaml', '.yml'):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        config = merge_with_env_vars(config)
        return config

    except Exception as e:
        logging.error(f"Error loading config from {config_path}: {e}")
        return create_default_config()


def create_default_config() -> Dict[str, Any]:
    """Create default configuration."""
    return {
        'research': {
            'max_concurrent': 50,
            'batch_size': 10,
            'max_websites_per_query': 100,
            'categories': [
                'technology', 'business', 'entertainment', 'sports', 'health',
                'science', 'politics', 'education', 'finance', 'lifestyle'
            ],
        },
        'trend_analysis': {
            'min_trend_score': 0.3,
            'min_growth_rate': 0.2,
            'max_trends': 100,
            'confidence_threshold': 0.7
        },
        'content_strategy': {
            'min_attention_potential': 0.3,
            'min_content_gap': 0.2,
            'min_monetization': 0.1,
            'videos_per_topic': 10
        },
        'video_production': {
            'formats': ['short_form', 'medium_form', 'long_form'],
            'default_durations': {'short_form': 30, 'medium_form': 180, 'long_form': 600},
            'max_videos_per_topic': 10
        },
        'publishing': {
            'platforms': ['youtube', 'tiktok', 'instagram', 'linkedin'],
            'auto_publish': True,
            'max_retries': 3
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'vagent.log'
        },
        'storage': {
            'results_dir': 'vagent_results',
            'cache_dir': 'vagent_cache',
            'max_cache_size_mb': 1000
        }
    }


def merge_with_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge configuration with environment variables."""
    env_mappings = {
        'VAGENT_RESEARCH_MAX_CONCURRENT': ('research', 'max_concurrent', int),
        'VAGENT_RESEARCH_BATCH_SIZE': ('research', 'batch_size', int),
        'VAGENT_LOG_LEVEL': ('logging', 'level', str),
    }
    for env_var, (section, key, type_func) in env_mappings.items():
        if env_var in os.environ:
            config.setdefault(section, {})
            config[section][key] = type_func(os.environ[env_var])
    return config


def save_config(config: Dict[str, Any], config_path: Path):
    """Save configuration to file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        if config_path.suffix.lower() in ('.yaml', '.yml'):
            yaml.dump(config, f, default_flow_style=False, indent=2)
        else:
            json.dump(config, f, indent=2, ensure_ascii=False, default=str)


def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration."""
    log_config = config.get('logging', {})
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        handlers=[
            logging.FileHandler(log_config.get('file', 'vagent.log')),
            logging.StreamHandler()
        ]
    )


def ensure_directories(config: Dict[str, Any]):
    """Ensure required directories exist."""
    storage = config.get('storage', {})
    for d in [storage.get('results_dir', 'vagent_results'), storage.get('cache_dir', 'vagent_cache')]:
        Path(d).mkdir(parents=True, exist_ok=True)


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration structure and values."""
    required = ['research', 'trend_analysis', 'content_strategy', 'video_production', 'publishing']
    for s in required:
        if s not in config:
            logging.error(f"Missing required configuration section: {s}")
            return False
    return True


def format_duration(seconds: int) -> str:
    """Format seconds to human readable."""
    if seconds < 60:
        return f"{seconds}s"
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s: parts.append(f"{s}s")
    return ' '.join(parts) if parts else "0s"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem."""
    invalid = '<>:"/\\|?*'
    for c in invalid:
        filename = filename.replace(c, '_')
    if len(filename) > 255:
        ext = Path(filename).suffix
        filename = Path(filename).stem[:255 - len(ext)] + ext
    return filename.strip('. ')
