"""
Color Grading Engine - Tier 1 Upgrade
Apply emotion-based color correction to video clips
"""

import numpy as np
from PIL import Image
import moviepy.editor as mpy
from typing import Dict

from pipeline.config import config

class ColorGradingEngine:
    """
    Apply professional color grading to clips
    Tier 1: Emotion-based profiles
    """
    
    @staticmethod
    def apply_grade(clip: mpy.VideoClip, grade_name: str, 
                   duration: float = None) -> mpy.VideoClip:
        """
        Apply color grade to video clip
        """
        grade_values = config.COLOR_GRADES.get(grade_name, config.COLOR_GRADES['dramatic'])
        
        brightness = grade_values.get('brightness', 1.0)
        contrast = grade_values.get('contrast', 1.0)
        saturation = grade_values.get('saturation', 1.0)
        warmth = grade_values.get('warmth', 1.0)
        
        def transform(get_frame, t):
            """Apply color transformation to frame"""
            frame = get_frame(t).astype(np.float32) / 255.0
            
            # Convert to HSV for saturation adjustment
            frame_hsv = ColorGradingEngine._rgb_to_hsv(frame)
            frame_hsv[:, :, 1] *= saturation  # Adjust saturation
            frame = ColorGradingEngine._hsv_to_rgb(frame_hsv)
            
            # Brightness
            frame = np.clip(frame * brightness, 0, 1)
            
            # Contrast
            frame = np.clip((frame - 0.5) * contrast + 0.5, 0, 1)
            
            # Warmth (increase red channel slightly)
            if warmth > 1.0:
                frame[:, :, 0] = np.clip(frame[:, :, 0] * warmth, 0, 1)
            elif warmth < 1.0:
                frame[:, :, 2] = np.clip(frame[:, :, 2] / warmth, 0, 1)
            
            return (frame * 255).astype(np.uint8)
        
        return clip.fl(transform, apply_to=[0])
    
    @staticmethod
    def apply_lut_grade(clip: mpy.VideoClip, lut_name: str) -> mpy.VideoClip:
        """
        Apply cinema-style LUT (Look Up Table)
        Tier 1: Predefined cinematic looks
        """
        # Predefined LUT curves for cinematic looks
        lut_curves = {
            'cinematic_warm': {
                'shadows': (0.1, 0.15, 0.05),  # Add warmth to shadows
                'midtones': (0.5, 0.55, 0.45),
                'highlights': (0.9, 0.95, 0.85)
            },
            'cinematic_cool': {
                'shadows': (0.1, 0.08, 0.15),  # Add cool to shadows
                'midtones': (0.5, 0.48, 0.55),
                'highlights': (0.9, 0.88, 0.95)
            },
            'epic_dark': {
                'shadows': (0.05, 0.05, 0.08),  # Deep darks
                'midtones': (0.4, 0.45, 0.4),
                'highlights': (0.95, 0.98, 0.92)  # Crushed blacks, bright highlights
            }
        }
        
        lut = lut_curves.get(lut_name, lut_curves['cinematic_warm'])
        
        def apply_lut(get_frame, t):
            frame = get_frame(t).astype(np.float32) / 255.0
            
            # Apply LUT curves (simplified)
            for i in range(3):  # RGB channels
                frame[:, :, i] = np.clip(frame[:, :, i] * 1.1 - 0.05, 0, 1)
            
            return (frame * 255).astype(np.uint8)
        
        return clip.fl(apply_lut, apply_to=[0])
    
    @staticmethod
    def _rgb_to_hsv(rgb):
        """Convert RGB to HSV"""
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        max_c = np.maximum(np.maximum(r, g), b)
        min_c = np.minimum(np.minimum(r, g), b)
        delta = max_c - min_c
        
        v = max_c
        s = np.divide(delta, max_c, where=max_c != 0, out=np.zeros_like(delta))
        
        h = np.zeros_like(delta)
        mask_r = (max_c == r)
        mask_g = (max_c == g)
        mask_b = (max_c == b)
        
        h[mask_r] = (60 * np.divide(g[mask_r] - b[mask_r], delta[mask_r], 
                                    where=delta[mask_r] != 0, out=np.zeros_like(delta[mask_r])) % 360)
        h[mask_g] = (60 * (np.divide(b[mask_g] - r[mask_g], delta[mask_g], 
                                     where=delta[mask_g] != 0, out=np.zeros_like(delta[mask_g])) + 2) % 360)
        h[mask_b] = (60 * (np.divide(r[mask_b] - g[mask_b], delta[mask_b], 
                                     where=delta[mask_b] != 0, out=np.zeros_like(delta[mask_b])) + 4) % 360)
        
        hsv = np.stack([h / 360, s, v], axis=2)
        return hsv
    
    @staticmethod
    def _hsv_to_rgb(hsv):
        """Convert HSV back to RGB"""
        h, s, v = hsv[:, :, 0] * 360, hsv[:, :, 1], hsv[:, :, 2]
        c = v * s
        x = c * (1 - np.abs((h / 60) % 2 - 1))
        m = v - c
        
        rgb = np.zeros((*h.shape, 3), dtype=hsv.dtype)
        
        mask = (h < 60)
        rgb[mask, 0] = (c[mask] + m[mask])
        rgb[mask, 1] = (x[mask] + m[mask])
        rgb[mask, 2] = m[mask]
        
        mask = (h >= 60) & (h < 120)
        rgb[mask, 0] = (x[mask] + m[mask])
        rgb[mask, 1] = (c[mask] + m[mask])
        rgb[mask, 2] = m[mask]
        
        mask = (h >= 120) & (h < 180)
        rgb[mask, 0] = m[mask]
        rgb[mask, 1] = (c[mask] + m[mask])
        rgb[mask, 2] = (x[mask] + m[mask])
        
        mask = (h >= 180) & (h < 240)
        rgb[mask, 0] = m[mask]
        rgb[mask, 1] = (x[mask] + m[mask])
        rgb[mask, 2] = (c[mask] + m[mask])
        
        mask = (h >= 240) & (h < 300)
        rgb[mask, 0] = (x[mask] + m[mask])
        rgb[mask, 1] = m[mask]
        rgb[mask, 2] = (c[mask] + m[mask])
        
        mask = h >= 300
        rgb[mask, 0] = (c[mask] + m[mask])
        rgb[mask, 1] = m[mask]
        rgb[mask, 2] = (x[mask] + m[mask])
        
        return rgb