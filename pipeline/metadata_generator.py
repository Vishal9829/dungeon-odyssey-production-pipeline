"""Metadata aggregation for pipeline outputs."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from pipeline.config import config


def generate_metadata(tiles: List[Dict], audio_manifest: Dict[str, Dict]) -> Dict:
    durations = [float(t.get("estimated_screen_time_sec", 3.0)) for t in tiles]
    total_sec = float(sum(durations))
    total_min = total_sec / 60.0

    scene_distribution: Dict[str, int] = {}
    character_appearance: Dict[str, int] = {"Narrator": len(tiles)}
    importance_vals = []
    ocr_confidences = []

    for item in tiles:
        scene = item.get("scene_type", "unknown")
        scene_distribution[scene] = scene_distribution.get(scene, 0) + 1
        importance_vals.append(int(item.get("importance", 5)))
        conf = float(item.get("ocr", {}).get("confidence", 0.0))
        if conf > 0:
            ocr_confidences.append(conf)

    return {
        "project": "Dungeon Odyssey Recap - Production v4.1",
        "total_tiles": len(tiles),
        "total_duration_sec": round(total_sec, 2),
        "total_duration_min": round(total_min, 2),
        "target_range_min": f"{config.TARGET_DURATION_MIN}-{config.TARGET_DURATION_MAX}",
        "within_target": config.TARGET_DURATION_MIN <= total_min <= config.TARGET_DURATION_MAX,
        "scene_distribution": dict(sorted(scene_distribution.items())),
        "character_appearance": character_appearance,
        "tts_script_entries": len(audio_manifest),
        "tts_total_audio_duration_sec": round(
            float(sum(v.get("duration_sec", 0.0) for v in audio_manifest.values())), 2
        ),
        "quality_metrics": {
            "avg_importance": round(float(np.mean(importance_vals)), 2) if importance_vals else 0.0,
            "text_heavy_tiles": len([t for t in tiles if t.get("is_text_heavy")]),
            "avg_ocr_confidence": round(float(np.mean(ocr_confidences)), 2) if ocr_confidences else 0.0,
        },
    }

