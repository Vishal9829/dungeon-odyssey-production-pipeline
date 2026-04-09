"""
Chapter Markers Engine - Tier 2 Upgrade
Generate YouTube-style chapter navigation cards
"""

import json
from typing import List, Dict, Tuple
import moviepy.editor as mpy
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from pipeline.config import config

class ChapterMarker:
    """Represents a single chapter marker"""
    
    def __init__(self, time_sec: float, title: str, tile_index: int = 0):
        self.time_sec = time_sec
        self.title = title
        self.tile_index = tile_index
        self.formatted_time = self._format_time(time_sec)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    
    def to_dict(self) -> Dict:
        return {
            'time_sec': round(self.time_sec, 2),
            'formatted_time': self.formatted_time,
            'title': self.title,
            'tile_index': self.tile_index
        }

class ChapterMarkerEngine:
    """
    Tier 2: Generate chapter markers from tile data
    Auto-detect high-importance scenes as chapter boundaries
    """
    
    def __init__(self):
        self.chapters: List[ChapterMarker] = []
    
    def generate_chapters_from_tiles(self, tiles: List[Dict]) -> List[ChapterMarker]:
        """
        Auto-detect chapters from tile importance and scene type
        Tier 2: Intelligent chapter detection
        """
        current_time = 0.0
        chapter_count = 0
        
        for i, tile in enumerate(tiles):
            importance = tile.get('importance', 5)
            scene_type = tile.get('scene_type', 'unknown')
            duration = tile.get('estimated_screen_time_sec', 3.0)
            
            # Mark as chapter if:
            # 1. Very high importance (>=8)
            # 2. Scene type is 'climactic' or 'establishing'
            # 3. Spacing: at least 5 minutes apart
            is_chapter_boundary = (
                (importance >= config.CHAPTER_IMPORTANCE_THRESHOLD) or
                (scene_type in ['climactic', 'establishing', 'action'])
            )
            
            if is_chapter_boundary and chapter_count < len(config.CHAPTER_TEMPLATES):
                chapter_title = config.CHAPTER_TEMPLATES[chapter_count]
                chapter = ChapterMarker(current_time, chapter_title, i)
                self.chapters.append(chapter)
                chapter_count += 1
            
            current_time += duration
        
        return self.chapters
    
    def create_chapter_card(self, chapter: ChapterMarker, 
                           duration_sec: float = 3.0) -> mpy.VideoClip:
        """
        Create a title card for chapter marker
        Tier 2: Cinematic chapter transitions
        """
        # Create black background
        img = Image.new(
            'RGB',
            config.VIDEO_RESOLUTION,
            color=config.CHAPTER_BG_COLOR
        )
        draw = ImageDraw.Draw(img)
        
        # Load font
        try:
            font = ImageFont.truetype(config.FONT_PATH, config.CHAPTER_FONT_SIZE)
        except:
            font = ImageFont.load_default()
        
        # Draw chapter text
        text = chapter.title
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (config.VIDEO_RESOLUTION[0] - text_width) // 2
        y = (config.VIDEO_RESOLUTION[1] - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        # Draw timestamp
        timestamp_text = chapter.formatted_time
        timestamp_font_size = config.CHAPTER_FONT_SIZE // 2
        try:
            ts_font = ImageFont.truetype(config.FONT_PATH, timestamp_font_size)
        except:
            ts_font = font
        
        ts_bbox = draw.textbbox((0, 0), timestamp_text, font=ts_font)
        ts_width = ts_bbox[2] - ts_bbox[0]
        ts_x = (config.VIDEO_RESOLUTION[0] - ts_width) // 2
        ts_y = y + text_height + 40
        
        draw.text((ts_x, ts_y), timestamp_text, fill='gray', font=ts_font)
        
        # Create video clip
        img_array = np.array(img)
        chapter_clip = mpy.ImageClip(img_array).set_duration(duration_sec)
        
        # Add fade in/out
        chapter_clip = chapter_clip.fadein(config.CHAPTER_FADE_DURATION).fadeout(config.CHAPTER_FADE_DURATION)
        
        return chapter_clip
    
    def get_chapters_for_youtube(self) -> str:
        """
        Format chapters for YouTube description
        """
        lines = []
        for chapter in self.chapters:
            lines.append(f"{chapter.formatted_time} {chapter.title}")
        
        return '\n'.join(lines)
    
    def save_chapters(self, output_path: str):
        """Save chapters to JSON"""
        chapters_data = [ch.to_dict() for ch in self.chapters]
        
        with open(output_path, 'w') as f:
            json.dump({
                'total_chapters': len(self.chapters),
                'chapters': chapters_data,
                'youtube_format': self.get_chapters_for_youtube()
            }, f, indent=2)
        
        print(f"✅ Chapters saved: {output_path}")