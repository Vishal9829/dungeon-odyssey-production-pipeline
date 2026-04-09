"""
╔══════════════════════════════════════════════════════════════════════════════╗
║      MOVIEPY COMPOSITION ENGINE — Dungeon Odyssey Video Renderer             ║
║                                                                              ║
║      Features:                                                              ║
║        • Image sequence to video conversion                                 ║
║        • Audio sync (narration + background music)                          ║
║        • VFX: fades, zooms, transitions                                     ║
║        • Text overlay (narration + OCR extracted dialogue)                  ║
║        • Chapter markers & timeline control                                 ║
║        • High-quality export (1080p/4K)                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess

import moviepy.editor as mpy
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont
import librosa
import soundfile as sf

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class MoviePyConfig:
    VIDEO_FPS = 30
    RESOLUTION = (1920, 1080)  # 1080p
    BITRATE = '8000k'
    CODEC = 'libx264'
    PRESET = 'medium'  # fast, medium, slow
    
    # Font settings
    NARRATION_FONT_SIZE = 48
    SUBTITLE_FONT_SIZE = 36
    FONT_COLOR = 'white'
    FONT_BG_COLOR = 'black'
    
    # Background music
    BGM_VOLUME = 0.3  # 30% volume for music
    NARRATION_VOLUME = 1.0
    
    # VFX
    FADE_DURATION = 0.5
    TRANSITION_TYPE = 'crossfadeblack'
    SFX_VOLUME = 0.22

# ─────────────────────────────────────────────────────────────────────────────
# TIMELINE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

class VideoTimeline:
    """Build frame-accurate video timeline"""
    
    def __init__(self, tile_results: List[Dict], audio_manifest: Dict):
        self.tiles = tile_results
        self.audio = audio_manifest
        self.timeline = []
        self.total_duration = 0.0
    
    def build(self) -> List[Dict]:
        """
        Build frame-accurate timeline
        Returns list of {tile_path, start_sec, duration_sec, audio_file, narration}
        """
        current_time = 0.0
        
        for tile in self.tiles:
            tile_file = tile['tile']
            duration = tile.get('estimated_screen_time_sec', 3.0)
            
            audio_info = self.audio.get(tile_file, {})
            audio_file = audio_info.get('audio_file')
            
            entry = {
                'tile': tile_file,
                'tile_path': tile.get('tile_path'),
                'start_sec': current_time,
                'duration_sec': duration,
                'end_sec': current_time + duration,
                'audio_file': audio_file,
                'audio_duration_sec': audio_info.get('duration_sec', duration),
                'narration': tile.get('narration', ''),
                'ocr_text': tile.get('ocr', {}).get('extracted_text', ''),
                'importance': tile.get('importance', 5),
                'scene_type': tile.get('scene_type', 'unknown')
            }
            
            self.timeline.append(entry)
            current_time += duration
        
        self.total_duration = current_time
        return self.timeline

# ─────────────────────────────────────────────────────────────────────────────
# VFX ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class VFXEngine:
    """Apply visual effects to video clips"""
    
    @staticmethod
    def apply_fade_in(clip: mpy.VideoClip, duration: float) -> mpy.VideoClip:
        """Fade in effect"""
        return clip.fadein(duration)
    
    @staticmethod
    def apply_fade_out(clip: mpy.VideoClip, duration: float) -> mpy.VideoClip:
        """Fade out effect"""
        return clip.fadeout(duration)
    
    @staticmethod
    def apply_zoom(clip: mpy.VideoClip, zoom_factor: float, duration: float) -> mpy.VideoClip:
        """Slow zoom effect"""
        def zoom_transform(get_frame, t):
            frame = get_frame(t)
            z = 1 + (zoom_factor - 1) * t / duration
            h, w = frame.shape[:2]
            new_h, new_w = int(h / z), int(w / z)
            y_start = (h - new_h) // 2
            x_start = (w - new_w) // 2
            cropped = frame[y_start:y_start+new_h, x_start:x_start+new_w]
            resized = np.array(Image.fromarray(cropped).resize((w, h)))
            return resized
        
        return clip.fl(zoom_transform, apply_to=[0])
    
    @staticmethod
    def apply_color_grade(clip: mpy.VideoClip, brightness: float = 1.0, 
                         contrast: float = 1.0, saturation: float = 1.0) -> mpy.VideoClip:
        """Color grading"""
        def color_transform(get_frame, t):
            frame = get_frame(t).astype(np.float32) / 255.0
            
            # Brightness
            frame = np.clip(frame * brightness, 0, 1)
            
            # Contrast
            frame = np.clip((frame - 0.5) * contrast + 0.5, 0, 1)
            
            return (frame * 255).astype(np.uint8)
        
        return clip.fl(color_transform, apply_to=[0])
    
    @staticmethod
    def apply_vignette(clip: mpy.VideoClip) -> mpy.VideoClip:
        """Vignette darkening effect"""
        h, w = MoviePyConfig.RESOLUTION
        
        # Create vignette mask
        x = np.linspace(-1, 1, w)
        y = np.linspace(-1, 1, h)
        X, Y = np.meshgrid(x, y)
        vignette = 1 - (X**2 + Y**2) / 2
        vignette = np.clip(vignette, 0.5, 1.0)
        
        def vignette_transform(get_frame, t):
            frame = get_frame(t).astype(np.float32)
            for c in range(3):
                frame[:, :, c] = frame[:, :, c] * vignette
            return np.clip(frame, 0, 255).astype(np.uint8)
        
        return clip.fl(vignette_transform, apply_to=[0])

# ─────────────────────────────────────────────────────────────────────────────
# TEXT OVERLAY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class TextOverlay:
    """Add narration & dialogue text overlays"""
    
    @staticmethod
    def create_narration_overlay(text: str, duration: float, 
                                position: str = 'bottom') -> mpy.TextClip:
        """
        Create narration text overlay
        position: 'top', 'bottom', 'center'
        """
        text_clip = mpy.TextClip(
            text,
            fontsize=MoviePyConfig.NARRATION_FONT_SIZE,
            color=MoviePyConfig.FONT_COLOR,
            font='Arial-Bold',
            method='caption',
            size=(1800, 300),
            align='center'
        ).set_duration(duration)
        
        # Position
        if position == 'bottom':
            text_clip = text_clip.set_position(('center', 'bottom'), relative=True)
        elif position == 'top':
            text_clip = text_clip.set_position(('center', 'top'), relative=True)
        else:
            text_clip = text_clip.set_position('center')
        
        return text_clip
    
    @staticmethod
    def create_dialogue_overlay(text: str, duration: float, 
                               speaker: str = '') -> mpy.TextClip:
        """
        Create dialogue text overlay (extracted from OCR)
        """
        full_text = f"{speaker}: {text}" if speaker else text
        
        text_clip = mpy.TextClip(
            full_text,
            fontsize=MoviePyConfig.SUBTITLE_FONT_SIZE,
            color=MoviePyConfig.FONT_COLOR,
            font='Arial',
            method='caption',
            size=(1800, 200),
            align='left'
        ).set_duration(duration)
        
        text_clip = text_clip.set_position((50, 100), relative=False)
        
        return text_clip
    
    @staticmethod
    def create_chapter_marker(chapter_name: str, duration: float = 3.0) -> mpy.TextClip:
        """Create chapter transition card"""
        text_clip = mpy.TextClip(
            chapter_name.upper(),
            fontsize=72,
            color='white',
            font='Arial-Bold',
            align='center'
        ).set_duration(duration)
        
        text_clip = text_clip.set_position('center')
        
        # Add fade in/out
        text_clip = text_clip.fadein(0.5).fadeout(0.5)
        
        return text_clip

# ─────────────────────────────────────────────────────────────────────────────
# AUDIO ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class AudioEngine:
    """
    Handle audio composition
    Mix narration + background music + sound effects
    """
    
    def __init__(self, bgm_path: Optional[str] = None, sfx_dir: Optional[str] = None):
        self.bgm_path = bgm_path
        self.sfx_dir = sfx_dir
        self.bgm_audio = None
        
        if bgm_path and os.path.exists(bgm_path):
            try:
                self.bgm_audio = mpy.AudioFileClip(bgm_path)
            except Exception as e:
                print(f"⚠️  Failed to load BGM: {e}")

        # Optional scene->sfx map (base names without extension).
        self.sfx_map = {
            "action": "sword_clash",
            "dialogue": "whoosh",
            "establishing": "ambient_dungeon",
            "reaction": "gasp",
            "transition": "transition",
            "climactic": "dramatic_swell",
        }

    @staticmethod
    def _resolve_audio_file(directory: str, base_name: str) -> Optional[str]:
        """Resolve audio file by trying common extensions in priority order."""
        exts = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]
        for ext in exts:
            candidate = os.path.join(directory, f"{base_name}{ext}")
            if os.path.exists(candidate):
                return candidate
        # fallback: any file starting with base_name.
        for name in os.listdir(directory):
            if name.lower().startswith(base_name.lower() + "."):
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return candidate

        # Keyword fallback for custom asset names.
        alias_keywords = {
            "sword_clash": ["sword-fight", "sword-slice", "sword", "clash", "fight"],
            "whoosh": ["swoosh", "whoosh", "swish", "transition"],
            "ambient_dungeon": ["cave-wind", "creepy-cave", "ambient", "cave", "wind", "dungeon"],
            "gasp": ["gasp"],
            "transition": ["transition", "camera-zoom", "zoom", "swoosh"],
            "dramatic_swell": ["dramatic-sting", "dramatic", "sting", "swell"],
        }
        keywords = alias_keywords.get(base_name, [base_name.replace("_", "-"), base_name])
        files = [n for n in os.listdir(directory) if os.path.isfile(os.path.join(directory, n))]
        lower_files = [(n, n.lower()) for n in files]
        for kw in keywords:
            kw_l = kw.lower()
            for original, lower in lower_files:
                if kw_l in lower:
                    return os.path.join(directory, original)
        return None
    
    def compose_audio(self, timeline: List[Dict], output_path: str) -> str:
        """
        Compose final audio track
        Narration + BGM looped
        """
        print("🎵 Composing audio track...")
        
        audio_segments = []
        current_time = 0.0
        
        for entry in timeline:
            audio_file = entry.get('audio_file')
            start_sec = entry.get('start_sec', 0)
            duration = entry.get('duration_sec', 3.0)
            
            # Load narration audio
            if audio_file and os.path.exists(audio_file):
                try:
                    narration = mpy.AudioFileClip(audio_file)
                    audio_segments.append({
                        'audio': narration,
                        'start': start_sec,
                        'duration': narration.duration
                    })
                except Exception as e:
                    print(f"⚠️  Failed to load audio {audio_file}: {e}")
        
        if not audio_segments:
            print("❌ No audio segments to compose")
            return None
        
        # Compose with MoviePy
        final_audio = self._compose_with_moviepy(audio_segments, timeline[-1]['end_sec'])
        
        if final_audio:
            final_audio.write_audiofile(output_path, fps=44100, verbose=False, logger=None)
            print(f"✅ Audio composed: {output_path}")
            return output_path
        
        return None
    
    def _compose_with_moviepy(self, audio_segments: List[Dict], 
                             total_duration: float) -> Optional[mpy.AudioFileClip]:
        """Compose audio clips with MoviePy"""
        try:
            # Create composite audio
            audio_clips = []
            
            for seg in audio_segments:
                audio = seg['audio']
                start = seg['start']
                audio_clip = audio.set_start(start)
                audio_clips.append(audio_clip)

            # Optional SFX clips placed at scene starts.
            if self.sfx_dir and os.path.isdir(self.sfx_dir):
                for entry in timeline:
                    scene = entry.get("scene_type", "transition")
                    sfx_base = self.sfx_map.get(scene)
                    if not sfx_base:
                        continue
                    sfx_path = self._resolve_audio_file(self.sfx_dir, sfx_base)
                    if not sfx_path:
                        continue
                    try:
                        sfx_clip = mpy.AudioFileClip(sfx_path).volumex(MoviePyConfig.SFX_VOLUME)
                        sfx_clip = sfx_clip.set_start(float(entry.get("start_sec", 0)))
                        audio_clips.append(sfx_clip)
                    except Exception:
                        pass
            
            # Add background music (looped)
            if self.bgm_audio:
                bgm_loop = self._loop_audio(self.bgm_audio, total_duration)
                bgm_loop = bgm_loop.volumex(MoviePyConfig.BGM_VOLUME)
                audio_clips.append(bgm_loop)
            
            # Composite
            composite = mpy.CompositeAudioClip(audio_clips)
            composite = composite.set_duration(total_duration)
            
            return composite
        
        except Exception as e:
            print(f"❌ Audio composition failed: {e}")
            return None
    
    @staticmethod
    def _loop_audio(audio: mpy.AudioFileClip, target_duration: float) -> mpy.AudioFileClip:
        """Loop audio to match target duration"""
        if audio.duration >= target_duration:
            return audio.subclipped(0, target_duration)
        
        loops = int(np.ceil(target_duration / audio.duration))
        looped = mpy.concatenate_audioclips([audio] * loops)
        return looped.subclipped(0, target_duration)

# ─────────────────────────────────────────────────────────────────────────────
# VIDEO COMPOSITOR
# ─────────────────────────────────────────────────────────────────────────────

class VideoCompositor:
    """
    Main video composition and rendering engine
    """
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.vfx = VFXEngine()
    
    def render_video(self, timeline: List[Dict], audio_file: str, 
                    output_path: str, include_vfx: bool = True,
                    export_options: Optional[Dict] = None) -> bool:
        """
        Render final video with all components
        """
        print(f"\n🎬 Rendering video: {output_path}")
        
        try:
            # Build image clips
            image_clips = []
            
            for i, entry in enumerate(timeline):
                tile_path = entry.get('tile_path')
                duration = entry.get('duration_sec', 3.0)
                importance = entry.get('importance', 5)
                
                if not os.path.exists(tile_path):
                    print(f"⚠️  Tile not found: {tile_path}")
                    continue
                
                # Load image
                img_clip = mpy.ImageClip(tile_path).set_duration(duration)
                
                # Apply VFX based on importance
                if include_vfx:
                    img_clip = self._apply_vfx_by_importance(img_clip, importance, duration)
                
                # Add narration overlay
                narration = entry.get('narration', '')
                if narration:
                    text_clip = TextOverlay.create_narration_overlay(
                        narration, duration, position='bottom'
                    )
                    img_clip = mpy.CompositeVideoClip([img_clip, text_clip])
                
                # Add dialogue overlay if available
                ocr_text = entry.get('ocr_text', '')
                if ocr_text and len(ocr_text) > 10:
                    dialogue_clip = TextOverlay.create_dialogue_overlay(
                        ocr_text[:100], duration
                    )
                    img_clip = mpy.CompositeVideoClip([img_clip, dialogue_clip])
                
                image_clips.append(img_clip)
                
                if (i + 1) % 50 == 0:
                    print(f"   Prepared {i + 1}/{len(timeline)} clips...")
            
            if not image_clips:
                print("❌ No image clips to render")
                return False
            
            # Concatenate clips
            print("🔗 Concatenating clips...")
            final_video = mpy.concatenate_videoclips(image_clips)
            
            # Set resolution and FPS
            opts = export_options or {}
            width = int(opts.get("width", MoviePyConfig.RESOLUTION[0]))
            fps = int(opts.get("fps", MoviePyConfig.VIDEO_FPS))
            codec = opts.get("codec", MoviePyConfig.CODEC)
            bitrate = opts.get("bitrate", MoviePyConfig.BITRATE)
            preset = opts.get("preset", MoviePyConfig.PRESET)

            final_video = final_video.resize(width=width).set_fps(fps)
            
            # Add audio
            if os.path.exists(audio_file):
                print("🎵 Adding audio...")
                audio_clip = mpy.AudioFileClip(audio_file)
                final_video = final_video.set_audio(audio_clip)
            
            # Export
            print(f"📹 Exporting to {output_path}...")
            final_video.write_videofile(
                output_path,
                fps=fps,
                codec=codec,
                bitrate=bitrate,
                preset=preset,
                verbose=False,
                logger=None
            )
            
            print(f"✅ Video rendered: {output_path}")
            return True
        
        except Exception as e:
            print(f"❌ Rendering failed: {e}")
            return False
    
    def _apply_vfx_by_importance(self, clip: mpy.VideoClip, 
                                 importance: int, duration: float) -> mpy.VideoClip:
        """Apply VFX based on tile importance"""
        
        if importance >= 8:
            # High importance: zoom + color grade
            clip = self.vfx.apply_zoom(clip, 1.1, duration)
            clip = self.vfx.apply_color_grade(clip, brightness=1.1, saturation=1.2)
        elif importance >= 5:
            # Medium importance: fade in/out
            clip = clip.fadein(0.3).fadeout(0.3)
        else:
            # Low importance: vignette
            clip = self.vfx.apply_vignette(clip)
        
        return clip

# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def render_dungeon_odyssey_video(
    master_json_path: str,
    audio_manifest_path: str,
    audio_dir: str,
    output_video_path: str,
    bgm_path: Optional[str] = None,
    sfx_dir: Optional[str] = None,
    export_options: Optional[Dict] = None,
) -> bool:
    """
    Main video rendering function
    """
    
    print("""
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║      MOVIEPY VIDEO RENDERER — Dungeon Odyssey                               ║
    ║      Converting processed tiles → final video                               ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Load data
    print("📂 Loading pipeline data...")
    with open(master_json_path, 'r') as f:
        tile_results = json.load(f)
    
    with open(audio_manifest_path, 'r') as f:
        audio_manifest = json.load(f)
    
    print(f"   ✅ Loaded {len(tile_results)} tiles")
    print(f"   ✅ Loaded {len(audio_manifest)} audio files")
    
    # Build timeline
    print("\n📍 Building video timeline...")
    timeline_builder = VideoTimeline(tile_results, audio_manifest)
    timeline = timeline_builder.build()
    print(f"   ✅ Timeline duration: {timeline_builder.total_duration / 60:.1f} minutes")
    
    # Compose audio
    print("\n🎵 Composing audio...")
    audio_engine = AudioEngine(bgm_path, sfx_dir=sfx_dir)
    output_dir = os.path.dirname(output_video_path)
    audio_output = os.path.join(output_dir, 'final_audio.wav')
    
    if audio_engine.compose_audio(timeline, audio_output):
        print(f"   ✅ Audio composed: {audio_output}")
    else:
        print("   ⚠️  Audio composition failed, continuing without audio...")
        audio_output = None
    
    # Render video
    print("\n🎬 Rendering final video...")
    compositor = VideoCompositor(output_dir)
    
    success = compositor.render_video(
        timeline,
        audio_output or '',
        output_video_path,
        include_vfx=True,
        export_options=export_options,
    )
    
    if success:
        # Get file size
        file_size_mb = os.path.getsize(output_video_path) / (1024 * 1024)
        print(f"\n✨ VIDEO COMPLETE!")
        print(f"   Output: {output_video_path}")
        print(f"   Size: {file_size_mb:.1f} MB")
        print(f"   Duration: {timeline_builder.total_duration / 60:.1f} minutes")
    
    return success

if __name__ == '__main__':
    # Example usage
    render_dungeon_odyssey_video(
        master_json_path='/content/drive/MyDrive/manhua_pipeline/Dungeon Odyssey/pipeline_output_v4/dungeon_odyssey_master_v4.json',
        audio_manifest_path='/content/drive/MyDrive/manhua_pipeline/Dungeon Odyssey/pipeline_output_v4/audio_manifest.json',
        audio_dir='/content/drive/MyDrive/manhua_pipeline/Dungeon Odyssey/pipeline_output_v4/audio',
        output_video_path='/content/drive/MyDrive/manhua_pipeline/Dungeon Odyssey/DUNGEON_ODYSSEY_FINAL_v4.0.mp4',
        bgm_path=None  # Optional: path to background music
    )