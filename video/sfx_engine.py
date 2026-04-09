"""
Sound Effects Engine - Tier 1 Upgrade
Maps scene types to contextual sound effects
"""

import os
from typing import Dict, List, Optional
from pydub import AudioSegment
from pydub.effects import normalize
import numpy as np

from pipeline.config import config

class SFXEngine:
    """
    Manage sound effects layering
    Tier 1: Scene-type mapped SFX
    """
    
    def __init__(self, sfx_dir: str = None):
        self.sfx_dir = sfx_dir or os.path.join(config.ASSETS_DIR, 'sfx')
        self.sfx_cache = {}
        self.enabled = config.SFX_ENABLED
    
    def get_sfx_for_scene(self, scene_type: str) -> Optional[List[str]]:
        """
        Get SFX recommendations for scene type
        """
        if not self.enabled:
            return None
        
        sfx_list = config.SFX_MAP.get(scene_type, [])
        return sfx_list
    
    def load_sfx(self, sfx_name: str) -> Optional[AudioSegment]:
        """
        Load SFX from file with caching
        """
        if sfx_name in self.sfx_cache:
            return self.sfx_cache[sfx_name]
        
        sfx_path = os.path.join(self.sfx_dir, sfx_name)
        
        if not os.path.exists(sfx_path):
            print(f"⚠️  SFX not found: {sfx_path}")
            return None
        
        try:
            audio = AudioSegment.from_wav(sfx_path)
            self.sfx_cache[sfx_name] = audio
            return audio
        except Exception as e:
            print(f"❌ Failed to load SFX {sfx_name}: {e}")
            return None
    
    def layer_sfx_on_narration(self, narration_audio: AudioSegment, 
                               scene_type: str, start_time_ms: int = 0) -> AudioSegment:
        """
        Layer SFX on top of narration audio
        Tier 1: Volume-reduced to 40%, placed at scene start
        """
        if not self.enabled:
            return narration_audio
        
        sfx_list = self.get_sfx_for_scene(scene_type)
        if not sfx_list:
            return narration_audio
        
        # Select first SFX for this scene type
        sfx_name = sfx_list[0]
        sfx_audio = self.load_sfx(sfx_name)
        
        if not sfx_audio:
            return narration_audio
        
        # Adjust volume to 40%
        sfx_audio = sfx_audio - 8  # dB reduction (approximately 40%)
        
        # Layer SFX at scene start
        result = narration_audio.overlay(sfx_audio, position=start_time_ms)
        
        return result
    
    def create_ambient_bed(self, duration_ms: int, scene_type: str) -> Optional[AudioSegment]:
        """
        Create ambient background for entire scene
        Tier 1: Use ambient SFX as bed under narration
        """
        if scene_type not in ['establishing', 'ambient', 'transition']:
            return None
        
        ambient_files = {
            'establishing': 'ambient_dungeon.wav',
            'ambient': 'ambient_dungeon.wav',
            'transition': 'transition.wav'
        }
        
        ambient_name = ambient_files.get(scene_type)
        if not ambient_name:
            return None
        
        ambient = self.load_sfx(ambient_name)
        if not ambient:
            return None
        
        # Loop ambient to match duration
        loops_needed = (duration_ms // len(ambient)) + 1
        looped = ambient * loops_needed
        
        # Trim to exact duration
        ambient_trimmed = looped[:duration_ms]
        
        # Reduce volume to 40%
        ambient_trimmed = ambient_trimmed - 8
        
        return ambient_trimmed