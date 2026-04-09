"""Kokoro TTS integration for local narration rendering."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import soundfile as sf

from pipeline.config import config

try:
    from kokoro import Kokoro
except Exception:
    Kokoro = None  # type: ignore


class KokoroTTSEngine:
    """Generate WAV files from narration text."""

    def __init__(self) -> None:
        self.engine = None
        if Kokoro is not None:
            try:
                self.engine = Kokoro()
            except Exception:
                self.engine = None

    def _silence_fallback(self, out_path: str, duration_sec: float = 2.5) -> Tuple[str, float]:
        # Creates a tiny silent wav if Kokoro is unavailable.
        import numpy as np

        sr = config.TTS_SAMPLE_RATE
        samples = np.zeros(int(sr * duration_sec), dtype=np.float32)
        sf.write(out_path, samples, sr)
        return out_path, duration_sec

    def generate_audio(
        self,
        text: str,
        output_path: str,
        speed: float,
        pause_before_ms: int = 0,
        pause_after_ms: int = 0,
    ) -> Tuple[Optional[str], float]:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if self.engine is None:
                return self._silence_fallback(output_path, duration_sec=max(2.0, len(text.split()) * 0.35))

            # Kokoro API differs between versions. Try common signatures.
            audio = None
            sample_rate = config.TTS_SAMPLE_RATE
            try:
                audio = self.engine.create(
                    text=text,
                    voice=config.TTS_VOICE,
                    speed=speed,
                )
            except Exception:
                audio = self.engine.create(text, voice=config.TTS_VOICE, speed=speed)  # type: ignore

            if isinstance(audio, tuple):
                wav, sample_rate = audio
            else:
                wav = audio

            sf.write(output_path, wav, sample_rate)
            duration = float(len(wav) / sample_rate)
            duration += (pause_before_ms + pause_after_ms) / 1000.0
            return output_path, round(duration, 3)
        except Exception:
            return self._silence_fallback(output_path, duration_sec=max(2.0, len(text.split()) * 0.35))

    def batch_generate(self, narrations: List[Dict], output_dir: str) -> Dict[str, Dict]:
        manifest: Dict[str, Dict] = {}
        os.makedirs(output_dir, exist_ok=True)

        for idx, item in enumerate(narrations, start=1):
            tile = item["tile"]
            stem = Path(tile).stem
            out_file = os.path.join(output_dir, f"{idx:05d}_{stem}.wav")
            out_path, duration = self.generate_audio(
                text=item.get("narration", ""),
                output_path=out_file,
                speed=float(item.get("tts_speed", config.TTS_SPEED_BASE)),
                pause_before_ms=int(item.get("tts_pause_before_ms", 0)),
                pause_after_ms=int(item.get("tts_pause_after_ms", 0)),
            )
            if out_path:
                manifest[tile] = {
                    "audio_file": out_path,
                    "duration_sec": duration,
                    "text": item.get("narration", ""),
                    "scene_type": item.get("scene_type", "unknown"),
                }
        return manifest

