"""Tile-level OCR + narration processing."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from pipeline.config import config


class TileProcessor:
    def __init__(self, ocr_engine, narration_engine, all_clients: List[Dict], state_lock) -> None:
        self.ocr_engine = ocr_engine
        self.narration_engine = narration_engine
        self.all_clients = all_clients
        self.state_lock = state_lock

    def _quick_visual_context(self, tile_path: str) -> str:
        img = cv2.imread(tile_path)
        if img is None:
            return "Unknown visual context."
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        edges = cv2.Canny(gray, 100, 200)
        edge_density = float(np.mean(edges > 0))
        mood = "dark" if brightness < 85 else "bright" if brightness > 170 else "balanced"
        pace = "high action" if edge_density > 0.12 else "low action"
        return f"{mood} tone, {pace} panel, edge_density={edge_density:.3f}"

    @staticmethod
    def _guess_scene_type(ocr_result: Dict) -> str:
        if ocr_result.get("has_text"):
            return "dialogue"
        return "action"

    @staticmethod
    def _duration_from_importance(importance: int, scene_type: str, is_text_heavy: bool) -> float:
        if is_text_heavy:
            return config.TEXT_HEAVY_DURATION
        base = config.DURATION_BY_IMPORTANCE.get(max(1, min(10, int(importance))), 4.0)
        multiplier = config.DURATION_BY_SCENE.get(scene_type, 1.0)
        duration = base * multiplier
        return round(max(config.MIN_TILE_DURATION, min(config.MAX_TILE_DURATION, duration)), 2)

    def process(self, tile_info: Tuple[int, str]) -> Optional[Dict]:
        task_idx, tile_path = tile_info
        tile_name = os.path.basename(tile_path)

        client_info = self.all_clients[task_idx % len(self.all_clients)]
        model = client_info["model"]
        client = client_info["client"]
        client_type = client_info["type"]

        gemini_client = client if client_type == "gemini" else None
        ocr_data = self.ocr_engine.hybrid_extract(
            tile_path,
            gemini_client=gemini_client,
            gemini_model=config.GEMINI_MODEL,
        )
        scene_type = self._guess_scene_type(ocr_data)
        visual_context = self._quick_visual_context(tile_path)

        narr = self.narration_engine.generate_narration(
            ocr_data=ocr_data,
            visual_context=visual_context,
            scene_type=scene_type,
            client=client,
            model=model,
        )
        if not narr:
            return None

        importance = int(narr.get("importance", 5))
        confirmed_scene = narr.get("confirmed_scene_type", scene_type) or scene_type
        duration = self._duration_from_importance(
            importance=importance,
            scene_type=confirmed_scene,
            is_text_heavy=bool(ocr_data.get("has_text")),
        )

        return {
            "tile": tile_name,
            "tile_path": tile_path,
            "order": task_idx,
            "ocr": {
                "extracted_text": ocr_data.get("extracted_text", ""),
                "confidence": ocr_data.get("ocr_confidence", 0.0),
                "has_text": ocr_data.get("has_text", False),
            },
            "scene_type": confirmed_scene,
            "narration": narr.get("narration", ""),
            "importance": importance,
            "emotion": narr.get("emotion", "dramatic"),
            "narration_style": narr.get("emotion", "dramatic"),
            "tts_speed": float(narr.get("tts_speed", config.TTS_SPEED_BASE)),
            "tts_pause_before_ms": int(narr.get("tts_pause_before_ms", 300)),
            "tts_pause_after_ms": int(narr.get("tts_pause_after_ms", 300)),
            "color_grade": narr.get("color_grade", config.COLOR_GRADES["dramatic"]),
            "estimated_screen_time_sec": duration,
            "is_text_heavy": bool(ocr_data.get("has_text", False)),
            "api_used": client_type,
        }

