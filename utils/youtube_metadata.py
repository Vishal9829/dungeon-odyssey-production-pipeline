"""
YouTube Metadata Generator - Tier 2 Upgrade
Generate SEO-optimized metadata for YouTube upload
"""

import json
from typing import Dict, List
from datetime import datetime

from pipeline.config import config

class YouTubeMetadataGenerator:
    """Generate YouTube-ready metadata"""
    
    @staticmethod
    def generate_metadata(metadata: Dict, chapters: List[Dict], 
                         duration_minutes: float) -> Dict:
        """
        Generate complete YouTube metadata
        Tier 2: SEO optimization
        """
        
        # Format chapter timestamps for description
        chapter_timestamps = ""
        if chapters:
            chapter_timestamps = "\n⏱️ TIMESTAMPS:\n"
            for ch in chapters:
                chapter_timestamps += f"{ch['formatted_time']} - {ch['title']}\n"
        
        # Generate title
        title = config.YOUTUBE_TITLE_TEMPLATE.format(
            duration=int(duration_minutes)
        )
        
        # Generate description
        description = config.YOUTUBE_DESCRIPTION_TEMPLATE.format(
            chapters=chapter_timestamps
        )
        
        # Additional metadata
        keywords = metadata.get('character_appearance', {})
        top_characters = ', '.join(
            list(keywords.keys())[:5]
        ) if keywords else "Jinwoo, Naga Army"
        
        return {
            'title': title,
            'description': description,
            'tags': config.YOUTUBE_TAGS,
            'keywords': top_characters,
            'category': 'Film & Animation',
            'language': 'en',
            'license': 'creativeCommon',
            'publicStatsViewable': True,
            'monetizationDetails': {
                'accessControlOwned': 'owned'
            },
            'madeForKids': False,
            'selfDeclaredMadeForKids': False,
            'chapters': chapters,
            'duration_minutes': int(duration_minutes),
            'thumbnail_notes': 'Use auto-generated thumbnail.png',
            'upload_recommendations': {
                'privacy': 'Public',
                'premiere': False,
                'notify_subscribers': True,
                'playlist': 'Dungeon Odyssey Series'
            },
            'seo_keywords': [
                'dungeon odyssey manhwa',
                'korean webtoon',
                'anime recap',
                'dungeon management',
                'full story summary',
                'kimjinwoo',
                'narrated recap'
            ],
            'metadata_generated_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def save_metadata(metadata: Dict, output_path: str):
        """Save metadata to JSON"""
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ YouTube metadata saved: {output_path}")
    
    @staticmethod
    def export_for_youtube_studio(metadata: Dict) -> str:
        """
        Export metadata in format ready for YouTube Studio paste
        """
        output = f"""
TITLE (max 100 chars):
{metadata['title'][:100]}

DESCRIPTION (max 5000 chars):
{metadata['description'][:5000]}

TAGS (comma-separated):
{', '.join(metadata['tags'][:10])}

CATEGORY:
{metadata['category']}

LANGUAGE:
{metadata['language']}

MADE FOR KIDS:
{str(metadata['madeForKids']).lower()}

CHAPTERS/TIMESTAMPS:
"""
        for ch in metadata['chapters']:
            output += f"{ch['formatted_time']} {ch['title']}\n"
        
        return output