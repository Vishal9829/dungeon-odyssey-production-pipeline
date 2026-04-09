"""
Configuration management for Dungeon Odyssey Pipeline v4.1
Tier 1 & Tier 2 upgrades included
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Config:
    """Master configuration class"""
    
    # ─────────────────────────────────────────────────────────────────────────
    # PATHS
    # ─────────────────────────────────────────────────────────────────────────
    BASE_PATH: str = '/content/drive/MyDrive/manhua_pipeline/Dungeon Odyssey/tiles_gutter_final_v2'
    OUTPUT_DIR: str = '/content/drive/MyDrive/manhua_pipeline/Dungeon Odyssey/pipeline_output_v4_1'
    AUDIO_DIR: str = None  # Set from OUTPUT_DIR
    VIDEO_DIR: str = None
    ASSETS_DIR: str = None
    
    # Output files
    MASTER_JSON: str = None
    METADATA_JSON: str = None
    AUDIO_MANIFEST: str = None
    VIDEO_MANIFEST: str = None
    YOUTUBE_METADATA: str = None
    CHAPTER_MARKERS: str = None
    TTS_SCRIPT: str = None
    THUMBNAIL: str = None
    
    # ─────────────────────────────────────────────────────────────────────────
    # API CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    GEMINI_MODEL: str = 'gemini-2.0-flash'
    NVIDIA_MODEL: str = 'meta/llama-3.2-90b-vision-instruct'
    
    # ─────────────────────────────────────────────────────────────────────────
    # TTS CONFIGURATION (Kokoro)
    # ─────────────────────────────────────────────────────────────────────────
    TTS_VOICE: str = 'af_bella'  # Male deep voice
    TTS_SPEED_BASE: float = 0.95
    TTS_SAMPLE_RATE: int = 24000
    
    # Tier 1: Adaptive speed based on importance
    TTS_SPEED_BY_IMPORTANCE: Dict[str, float] = field(default_factory=lambda: {
        'low': 1.05,      # Faster for unimportant scenes
        'medium': 0.95,   # Normal
        'high': 0.85,     # Slower for dramatic effect
        'climactic': 0.75 # Very slow for climactic moments
    })
    
    # ─────────────────────────────────────────────────────────────────────────
    # VIDEO CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    VIDEO_FPS: int = 30
    VIDEO_RESOLUTION: tuple = (1920, 1080)
    VIDEO_BITRATE: str = '8000k'
    VIDEO_CODEC: str = 'libx264'
    VIDEO_PRESET: str = 'medium'  # fast, medium, slow
    
    # ─────────────────────────────────────────────────────────────────────────
    # TEXT OVERLAY CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    NARRATION_FONT_SIZE: int = 48
    SUBTITLE_FONT_SIZE: int = 36
    CHAPTER_FONT_SIZE: int = 72
    FONT_COLOR: str = 'white'
    FONT_BG_COLOR: str = 'black'
    FONT_PATH: str = None  # Will be set from ASSETS_DIR
    
    # ─────────────────────────────────────────────────────────────────────────
    # AUDIO CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    BGM_VOLUME: float = 0.3       # Background music at 30%
    NARRATION_VOLUME: float = 1.0 # Narration at 100%
    SFX_VOLUME: float = 0.4       # Sound effects at 40%
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: PAUSE TIMING CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    TTS_PAUSE_CONFIG: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        'action': {'before_ms': 200, 'after_ms': 300},
        'dialogue': {'before_ms': 400, 'after_ms': 800},
        'establishing': {'before_ms': 300, 'after_ms': 400},
        'reaction': {'before_ms': 350, 'after_ms': 500},
        'transition': {'before_ms': 150, 'after_ms': 200},
        'climactic': {'before_ms': 600, 'after_ms': 1000}
    })
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: DURATION CONFIGURATION (Adaptive)
    # ─────────────────────────────────────────────────────────────────────────
    MIN_TILE_DURATION: float = 2.0
    MAX_TILE_DURATION: float = 7.0
    TEXT_HEAVY_DURATION: float = 2.0  # Merge with adjacent tiles
    
    # Importance-based duration multipliers
    DURATION_BY_IMPORTANCE: Dict[int, float] = field(default_factory=lambda: {
        1: 2.5, 2: 2.5, 3: 3.0,
        4: 3.5, 5: 4.0, 6: 4.5,
        7: 5.5, 8: 6.0, 9: 6.5, 10: 7.0
    })
    
    # Scene-type duration multipliers
    DURATION_BY_SCENE: Dict[str, float] = field(default_factory=lambda: {
        'action': 1.2,        # 20% longer
        'climactic': 1.3,     # 30% longer
        'dialogue': 1.0,      # Normal
        'establishing': 0.9,  # 10% shorter
        'transition': 0.7,    # Quick cuts
        'reaction': 1.0       # Normal
    })
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: SFX CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    SFX_ENABLED: bool = True
    SFX_MAP: Dict[str, List[str]] = field(default_factory=lambda: {
        'action': ['sword_clash.wav', 'explosion.wav', 'magic_cast.wav'],
        'dialogue': ['whoosh.wav'],
        'establishing': ['ambient_dungeon.wav', 'wind.wav'],
        'reaction': ['gasp.wav'],
        'transition': ['transition.wav'],
        'climactic': ['dramatic_swell.wav', 'thunder.wav']
    })
    SFX_DURATION_MS: Dict[str, int] = field(default_factory=lambda: {
        'sword_clash': 800,
        'explosion': 1500,
        'magic_cast': 1000,
        'whoosh': 500,
        'ambient_dungeon': 3000,
        'wind': 2000,
        'gasp': 600,
        'transition': 1000,
        'dramatic_swell': 2000,
        'thunder': 1200
    })
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: COLOR GRADING PROFILES
    # ─────────────────────────────────────────────────────────────────────────
    COLOR_GRADES: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'epic': {'brightness': 1.1, 'contrast': 1.2, 'saturation': 1.3, 'warmth': 1.05},
        'dark': {'brightness': 0.85, 'contrast': 1.1, 'saturation': 0.9, 'warmth': 0.95},
        'emotional': {'brightness': 1.05, 'contrast': 1.15, 'saturation': 1.5, 'warmth': 1.1},
        'tense': {'brightness': 0.9, 'contrast': 1.3, 'saturation': 0.8, 'warmth': 0.9},
        'dramatic': {'brightness': 1.0, 'contrast': 1.25, 'saturation': 1.2, 'warmth': 1.0},
        'mysterious': {'brightness': 0.8, 'contrast': 1.1, 'saturation': 0.95, 'warmth': 0.85}
    })
    
    EMOTION_COLOR_MAP: Dict[str, str] = field(default_factory=lambda: {
        'epic': 'epic',
        'dramatic': 'dramatic',
        'dark': 'dark',
        'emotional': 'emotional',
        'tense': 'tense',
        'mysterious': 'mysterious',
        'neutral': 'dramatic'
    })
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 2: VFX CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    VFX_ENABLED: bool = True
    VFX_FADE_DURATION: float = 0.5
    VFX_TRANSITION_TYPE: str = 'crossfadeblack'
    
    VFX_BY_IMPORTANCE: Dict[str, Dict] = field(default_factory=lambda: {
        'high': {
            'type': 'zoom',
            'zoom_factor': 1.15,
            'color_grade': 'epic',
            'fade_in': 0.3,
            'fade_out': 0.3
        },
        'medium': {
            'type': 'fade',
            'fade_in': 0.2,
            'fade_out': 0.2,
            'color_grade': 'dramatic'
        },
        'low': {
            'type': 'vignette',
            'color_grade': 'neutral',
            'fade_in': 0.1,
            'fade_out': 0.1
        }
    })
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 2: CHAPTER MARKERS CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    CHAPTERS_ENABLED: bool = True
    CHAPTER_MARKER_DURATION: float = 3.0
    CHAPTER_FADE_DURATION: float = 0.5
    CHAPTER_BG_COLOR: tuple = (0, 0, 0)  # Black background
    CHAPTER_TEXT_COLOR: str = 'white'
    
    # Auto-detect chapters by importance threshold
    CHAPTER_IMPORTANCE_THRESHOLD: int = 8
    CHAPTER_TEMPLATES: List[str] = field(default_factory=lambda: [
        "JINWOO'S AWAKENING",
        "THE NAGA LABYRINTH",
        "FIRST CONQUEST",
        "ALLIES & ENEMIES",
        "RISING POWER",
        "INTER-LABYRINTH POLITICS",
        "THE GREAT WAR",
        "FINAL CONFRONTATION",
        "AFTERMATH & LEGACY"
    ])
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 2: THUMBNAIL GENERATION
    # ─────────────────────────────────────────────────────────────────────────
    THUMBNAIL_ENABLED: bool = True
    THUMBNAIL_SIZE: tuple = (1280, 720)
    THUMBNAIL_TEXT: str = "DUNGEON ODYSSEY"
    THUMBNAIL_FONT_SIZE: int = 120
    THUMBNAIL_TEXT_COLOR: str = 'white'
    THUMBNAIL_BG_OVERLAY_ALPHA: float = 0.4  # Darkening overlay
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 2: YOUTUBE METADATA CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    YOUTUBE_TITLE_TEMPLATE: str = "DUNGEON ODYSSEY FULL RECAP — Epic Strategy Manhwa [{duration}min]"
    YOUTUBE_DESCRIPTION_TEMPLATE: str = """
Complete animated recap of Dungeon Odyssey (Korean Manhwa) featuring:
✅ Full Story Summary (1-2 hours)
✅ Character Development Arcs
✅ Dungeon Management & Strategy
✅ Epic Battle Sequences
✅ AI-Narrated with Lore Accuracy

Watch as Kim Jinwoo rises from a dungeon baby to command the Naga Labyrinth!

⏱️ Timestamps:
{chapters}

📖 Story: Dungeon Odyssey / Records of Dungeon Travel
🎨 Source: Korean Webtoon
🎬 Production: AI-Enhanced Video Pipeline v4.1

#DungeonOdyssey #Manhwa #AnimeRecap
"""
    
    YOUTUBE_TAGS: List[str] = field(default_factory=lambda: [
        'dungeon odyssey',
        'manhwa recap',
        'korean webtoon',
        'dungeon management',
        'strategy anime',
        'kim jinwoo',
        'naga labyrinth',
        'full recap',
        'animated summary',
        'webtoon story'
    ])
    
    # ─────────────────────────────────────────────────────────────────────────
    # QUALITY CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    NARRATION_MIN_WORDS: int = 8
    NARRATION_MAX_WORDS: int = 14
    REPETITION_THRESHOLD: float = 0.7
    CONTEXT_WINDOW: int = 10
    
    # Target video duration (minutes)
    TARGET_DURATION_MIN: int = 60
    TARGET_DURATION_MAX: int = 90
    
    # OCR quality thresholds
    OCR_CONFIDENCE_THRESHOLD: float = 0.3
    TEXT_EXTRACTION_THRESHOLD: int = 20  # Min chars for text-heavy classification
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROCESSING CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    NUM_WORKERS: int = 4
    BATCH_SIZE: int = 50
    API_RATE_LIMIT_DELAY_SEC: float = 2.0
    
    def __post_init__(self):
        """Initialize derived paths"""
        self.AUDIO_DIR = os.path.join(self.OUTPUT_DIR, 'audio')
        self.VIDEO_DIR = os.path.join(self.OUTPUT_DIR, 'video')
        self.ASSETS_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')
        
        self.MASTER_JSON = os.path.join(self.OUTPUT_DIR, 'dungeon_odyssey_master_v4_1.json')
        self.METADATA_JSON = os.path.join(self.OUTPUT_DIR, 'pipeline_metadata_v4_1.json')
        self.AUDIO_MANIFEST = os.path.join(self.OUTPUT_DIR, 'audio_manifest.json')
        self.VIDEO_MANIFEST = os.path.join(self.OUTPUT_DIR, 'video_manifest.json')
        self.YOUTUBE_METADATA = os.path.join(self.OUTPUT_DIR, 'youtube_metadata.json')
        self.CHAPTER_MARKERS = os.path.join(self.OUTPUT_DIR, 'chapter_markers.json')
        self.TTS_SCRIPT = os.path.join(self.OUTPUT_DIR, 'tts_script.json')
        self.THUMBNAIL = os.path.join(self.OUTPUT_DIR, 'thumbnail.png')
        
        self.FONT_PATH = os.path.join(self.ASSETS_DIR, 'fonts', 'Arial-Bold.ttf')

# Create global instance
config = Config()