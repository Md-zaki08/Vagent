"""
VAgent Video Renderer - Generates actual video frames and animations using Pillow.
Works without ffmpeg by creating animated GIFs and video frame sequences
that can be assembled into pro-grade videos.
"""

import asyncio
import logging
import math
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance

logger = logging.getLogger(__name__)

# Color palettes for hook-based styling
HOOK_PALETTES = {
    'curiosity': ['#FF6B35', '#F7C59F', '#004E89', '#1A659E', '#FFFFFF'],
    'urgency': ['#D90429', '#EF233C', '#2B2D42', '#8D99AE', '#EDF2F4'],
    'controversy': ['#FF0000', '#000000', '#FFFFFF', '#FF4444', '#333333'],
    'surprise': ['#7209B7', '#F72585', '#4CC9F0', '#4895EF', '#FFFFFF'],
    'value': ['#2D6A4F', '#52B788', '#95D5B2', '#1B4332', '#D8F3DC'],
    'default': ['#1A1A2E', '#16213E', '#0F3460', '#E94560', '#FFFFFF'],
}

FONT_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/TTF/DejaVuSans.ttf',
    '~/.fonts/DejaVuSans-Bold.ttf',
    '~/.fonts/DejaVuSans.ttf',
]


class VideoFrameRenderer:
    """Generates video frames using Pillow. Creates per-frame images and animated GIFs."""

    def __init__(self, output_dir: Optional[str] = None,
                 width: int = 1080, height: int = 1920):
        self.output_dir = Path(output_dir or tempfile.gettempdir()) / 'vagent_videos'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height
        self._load_fonts()

    def _load_fonts(self):
        """Load available fonts."""
        self.title_font = None
        self.body_font = None
        for fp in FONT_PATHS:
            fp = Path(fp).expanduser()
            if fp.exists():
                try:
                    self.title_font = ImageFont.truetype(str(fp), 72) if 'Bold' in fp.name else self.title_font
                    self.body_font = ImageFont.truetype(str(fp), 36) if 'Bold' not in fp.name else self.body_font
                except Exception:
                    continue
        if not self.title_font:
            self.title_font = ImageFont.load_default()
        if not self.body_font:
            self.body_font = ImageFont.load_default()

    def render_hook_frame(self, hook_text: str, style: str = 'curiosity',
                          category: str = '') -> Image.Image:
        """Render a single attention-grabbing hook frame.

        Production-quality frame with gradient background, bold text,
        decorative elements, and visual flair matching the hook's style.
        """
        colors = HOOK_PALETTES.get(style, HOOK_PALETTES['default'])
        # Parse hex to RGB
        colors_rgb = []
        for c in colors:
            if isinstance(c, str) and c.startswith('#'):
                colors_rgb.append(tuple(int(c[i:i+2], 16) for i in (1, 3, 5)))
            else:
                colors_rgb.append(c)
        colors = colors_rgb

        img = Image.new('RGB', (self.width, self.height), colors[0])
        draw = ImageDraw.Draw(img)

        # Gradient overlay
        for y in range(self.height):
            ratio = y / self.height
            r = int(colors[0][0] * (1 - ratio * 0.5))
            g = int(colors[1][1] * ratio * 0.3)
            b = int(colors[2][2] * ratio * 0.2)
            draw.line([(0, y), (self.width, y)], fill=(min(r, 255), min(g, 255), min(b, 255)))

        # Decorative top bar
        bar_color = colors[3]
        draw.rectangle([0, 80, self.width, 100], fill=bar_color)

        # Category badge (if provided)
        if category:
            cat_x = self.width // 2 - 100
            draw.rounded_rectangle(
                [cat_x, 120, cat_x + 200, 165],
                radius=20, fill=colors[2]
            )
            draw.text((cat_x + 100, 142), category.upper(), fill=colors[4],
                      font=self.body_font, anchor='mm')

        # Main hook text - word wrap with large bold font
        max_w = self.width - 120
        words = hook_text.split()
        lines = []
        current = ''
        for w in words:
            test = current + ' ' + w if current else w
            bbox = draw.textbbox((0, 0), test, font=self.title_font)
            if bbox[2] - bbox[0] > max_w:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)

        y_start = 350
        line_h = 90
        for i, line in enumerate(lines[:5]):
            y = y_start + i * line_h
            # Shadow text
            draw.text((self.width // 2 + 3, y + 3), line, fill=(0, 0, 0, 128),
                      font=self.title_font, anchor='mm')
            # Main text
            draw.text((self.width // 2, y), line, fill=colors[4],
                      font=self.title_font, anchor='mm')

        # Bottom decorative elements
        draw.rounded_rectangle(
            [self.width // 4, self.height - 100, self.width * 3 // 4, self.height - 70],
            radius=15, fill=colors[3]
        )

        # Subscribe/CTA indicator
        cta_text = '▶  WATCH TILL THE END'
        draw.text((self.width // 2, self.height - 85), cta_text,
                  fill=colors[4], font=self.body_font, anchor='mm')

        return img

    def render_title_card(self, title: str, subtitle: str = '',
                          creator_name: str = 'VAgent AI') -> Image.Image:
        """Render a professional title card for YouTube/TikTok/Shorts."""
        colors = HOOK_PALETTES['default']
        # Parse hex to RGB
        colors_rgb = []
        for c in colors:
            if isinstance(c, str) and c.startswith('#'):
                colors_rgb.append(tuple(int(c[i:i+2], 16) for i in (1, 3, 5)))
            else:
                colors_rgb.append(c)
        colors = colors_rgb
        
        img = Image.new('RGB', (self.width, self.height), colors[0])
        draw = ImageDraw.Draw(img)

        # Dark gradient background
        for y in range(self.height):
            ratio = y / self.height
            fade = int(20 * ratio)
            r = min(255, colors[0][0] + fade)
            g = min(255, colors[1][0] + fade)
            b = min(255, colors[2][0] + fade)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Decorative side bar
        draw.rectangle([60, 0, 80, self.height], fill=colors[3])

        # Title
        max_w = self.width - 200
        words = title.split()
        lines, current = [], ''
        for w in words:
            test = current + ' ' + w if current else w
            bbox = draw.textbbox((0, 0), test, font=self.title_font)
            if bbox[2] - bbox[0] > max_w:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)

        y_start = 300
        line_h = 100
        for i, line in enumerate(lines[:6]):
            y = y_start + i * line_h
            draw.text((self.width // 2, y), line, fill=colors[4],
                      font=self.title_font, anchor='mm')

        # Subtitle
        if subtitle:
            draw.text((self.width // 2, y_start + len(lines[:6]) * line_h + 80),
                      subtitle, fill=colors[2], font=self.body_font, anchor='mm')

        # Channel/creator bar at bottom
        bar_y = self.height - 120
        draw.rounded_rectangle([100, bar_y, self.width - 100, bar_y + 50],
                               radius=25, fill=colors[3])
        draw.text((self.width // 2, bar_y + 25), f'@{creator_name}',
                  fill=colors[4], font=self.body_font, anchor='mm')

        return img

    def render_outro(self, cta: str = 'Like & Subscribe for more!',
                     creator_name: str = 'VAgent AI') -> Image.Image:
        """Render an end-screen / outro frame."""
        colors = HOOK_PALETTES['value']
        img = Image.new('RGB', (self.width, self.height), colors[0])
        draw = ImageDraw.Draw(img)

        # Green gradient
        for y in range(self.height):
            ratio = y / self.height
            r = int(45 * (1 - ratio))
            g = int(122 * (1 - ratio))
            b = int(79 * (1 - ratio))
            draw.line([(0, y), (self.width, y)], fill=(min(r, 255), min(g, 255), min(b, 255)))

        draw.ellipse([self.width // 4, 200, self.width * 3 // 4, 700],
                     fill=colors[3], outline=colors[4], width=8)

        draw.text((self.width // 2, 450), '✓', fill=colors[4],
                  font=self.title_font, anchor='mm')

        draw.text((self.width // 2, 850), cta, fill=colors[4],
                  font=self.title_font, anchor='mm')

        draw.text((self.width // 2, self.height - 150), f'@{creator_name}',
                  fill=colors[2], font=self.body_font, anchor='mm')

        return img

    def render_b_roll(self, text: str, image_path: Optional[str] = None) -> Image.Image:
        """Render an informational B-roll frame with optional image."""
        colors = HOOK_PALETTES['default']
        # Parse hex to RGB
        colors_rgb = []
        for c in colors:
            if isinstance(c, str) and c.startswith('#'):
                colors_rgb.append(tuple(int(c[i:i+2], 16) for i in (1, 3, 5)))
            else:
                colors_rgb.append(c)
        colors = colors_rgb
        
        img = Image.new('RGB', (self.width, self.height), colors[0])
        draw = ImageDraw.Draw(img)

        # Image zone
        if image_path and Path(image_path).exists():
            try:
                overlay = Image.open(image_path)
                overlay = overlay.resize((self.width - 200, 600))
                img.paste(overlay, (100, 200))
            except Exception:
                draw.rounded_rectangle([100, 200, self.width - 100, 800],
                                       radius=30, fill=colors[1])

        draw.rounded_rectangle([100, 200, self.width - 100, 800],
                               radius=30, fill=colors[1])

        # Text overlay
        draw.text((self.width // 2, 1000), text, fill=colors[4],
                  font=self.body_font, anchor='mm')

        return img

    def render_frame_sequence(self, hook_text: str, duration: int = 30,
                              style: str = 'curiosity', fps: int = 1) -> List[str]:
        """Render a sequence of video frames (1 per second) and return file paths."""
        paths = []
        for sec in range(min(duration, 60)):
            img = self.render_hook_frame(hook_text, style)
            path = str(self.output_dir / f'frame_{uuid.uuid4().hex[:8]}_{sec:03d}.png')
            img.save(path, 'PNG')
            paths.append(path)
        return paths

    def create_animated_preview(self, frames: List[Image.Image],
                                 filename: str = 'preview.gif',
                                 duration_ms: int = 2000) -> str:
        """Create an animated GIF from frames (for preview/approval)."""
        output_path = str(self.output_dir / filename)
        if frames:
            frames[0].save(
                output_path, 'GIF', save_all=True,
                append_images=frames[1:], duration=duration_ms, loop=0,
                optimize=True,
            )
            logger.info(f"Created animated preview: {output_path}")
        return output_path

    def render_full_video_sequence(self, title: str, hook: str, cta: str,
                                    frames_per_scene: int = 5) -> str:
        """Render a complete video scene sequence: title → hook → body → outro."""
        title_card = self.render_title_card(title)
        hook_frame = self.render_hook_frame(hook, style='curiosity')
        outro_frame = self.render_outro(cta)

        # Create the sequence with multiple copies for pacing
        frames = [title_card] * 2
        for _ in range(frames_per_scene):
            frames.append(hook_frame)
        frames.extend([outro_frame] * 3)

        return self.create_animated_preview(frames, f'{uuid.uuid4().hex[:12]}.gif',
                                             duration_ms=1500)

    def get_video_size(self) -> str:
        """Return the configured video resolution."""
        return f"{self.width}x{self.height}"


class ScriptGenerator:
    """Generates optimized video scripts with hooks, transitions, and CTAs."""

    def __init__(self):
        self.hook_templates = [
            # Curiosity hooks
            "You won't believe what {topic} just did!",
            "This is why everyone is talking about {topic}",
            "What they're NOT telling you about {topic}",
            "The {topic} everyone is ignoring (here's why)",
            "I tried {topic} for 24 hours and THIS happened",
            "{topic} experts hate this ONE trick",
            "The hidden truth about {topic}",
            "Why {topic} is more important than you think",
            "This {topic} revelation changes everything",
            "What happens when {topic} goes mainstream?",
            # Urgency hooks
            "⚠️ BREAKING: {topic} just changed forever",
            "URGENT: You need to know about {topic} NOW",
            "This {topic} news is going to shock you",
            "STOP scrolling! {topic} is happening RIGHT NOW",
            "The {topic} deadline nobody is talking about",
            # Authority hooks
            "I analyzed 1000 {topic} articles so you don't have to",
            "A {topic} expert explains what's REALLY happening",
            "The science behind {topic} (you won't believe #3)",
            "Everything you know about {topic} is WRONG",
            "Here's what {topic} insiders won't tell you",
        ]
        self.transition_templates = [
            "Here's where it gets interesting...",
            "But wait, there's more...",
            "Now here's the part that blew my mind...",
            "This is where most people get it wrong...",
            "Let me explain why this matters...",
            "And this is the crucial part...",
            "But here's what nobody is talking about...",
            "Now let me show you what really happened...",
            "Here's the key insight you need to understand...",
            "But the most surprising part is this...",
        ]
        self.cta_templates = [
            "If you found this valuable, smash that like button and subscribe for more {topic} insights!",
            "Subscribe now and turn on notifications so you never miss another {topic} update!",
            "Comment below: what's your take on {topic}? We read every comment!",
            "Share this with someone who needs to know about {topic}!",
            "Follow for daily {topic} updates that actually matter!",
        ]

    def generate_hook(self, topic: str, category: str = '') -> str:
        """Generate attention-grabbing hook."""
        import random
        template = random.choice(self.hook_templates)
        hook = template.format(topic=topic.title())
        # Add visual flourish
        prefixes = ['🔥 ', '⚡ ', '💥 ', '🚨 ', '💡 ', '⚠️ ', '🎯 ', '💎 ', '🔑 ', '📢 ']
        if random.random() > 0.5:
            hook = random.choice(prefixes) + hook
        return hook

    def generate_script(self, topic: str, title: str, hook: str,
                        key_points: List[str], duration: int = 60,
                        category: str = '') -> Dict:
        """Generate a full script outline with timing, transitions, and cues."""
        import random
        segments = [
            {"time": "0:00-0:05", "type": "hook", "content": hook,
             "visual": "Attention-grabbing visual with bold text overlay",
             "audio": "Energetic, fast-paced background music"},
        ]

        per_point_time = (duration - 10) / max(len(key_points), 1)
        current_time = 5
        for i, point in enumerate(key_points[:8]):
            start_mm = int(current_time // 60)
            start_ss = int(current_time % 60)
            end_time = current_time + per_point_time
            end_mm = int(end_time // 60)
            end_ss = int(end_time % 60)
            transition = random.choice(self.transition_templates)

            segments.append({
                "time": f"{start_mm}:{start_ss:02d}-{end_mm}:{end_ss:02d}",
                "type": "body",
                "content": point,
                "transition": transition if i > 0 else "",
                "visual": f"B-roll or infographic showing {point[:30]}",
                "audio": "Informative, steady background",
            })
            current_time = end_time

        # CTA / Outro
        end_time_val = max(5, duration - 10)
        cta = random.choice(self.cta_templates).format(topic=topic)
        cta_end_mm = int(end_time_val // 60)
        cta_end_ss = int(end_time_val % 60)
        dur_mm = int(duration // 60)
        dur_ss = int(duration % 60)
        segments.append({
            "time": f"{cta_end_mm}:{cta_end_ss:02d}-{dur_mm}:{dur_ss:02d}",
            "type": "outro",
            "content": cta,
            "visual": "End screen with subscribe button and channel info",
            "audio": "Fade-out music with high-energy finish",
        })

        return {
            "title": title,
            "seo_title": self._generate_seo_title(topic, hook),
            "description": self._generate_description(topic, key_points),
            "segments": segments,
            "total_duration": duration,
            "tags": self._generate_tags(topic, category),
        }

    def _generate_seo_title(self, topic: str, hook: str) -> str:
        return hook[:60] + ('...' if len(hook) > 60 else '')

    def _generate_description(self, topic: str, points: List[str]) -> str:
        desc = [f"In this video, we dive deep into {topic}.",
                "Here's what you'll learn:", ""]
        for p in points[:5]:
            desc.append(f"📌 {p}")
        desc += ["", "🔔 Subscribe for more updates!",
                 "💬 Comment your thoughts below!",
                 "👍 Like if you found this helpful!"]
        return '\n'.join(desc)

    def _generate_tags(self, topic: str, category: str) -> List[str]:
        tags = [topic, f"{topic} explained", f"{topic} 2026"]
        if category:
            tags.extend([category, f"{category} news", f"trending {category}"])
        tags.extend(["viral", "trending", "must watch", "blow your mind",
                      "you need to know", "insane", "unbelievable"])
        return tags[:15]
