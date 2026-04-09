"""Main pipeline execution entrypoint."""

import json
import os
import threading
import time
from math import ceil

from openai import OpenAI

from pipeline.config import config
from pipeline.ocr_engine import OCREngine
from pipeline.narration_engine import NarrationEngine
from pipeline.tts_engine import KokoroTTSEngine
from pipeline.tile_processor import TileProcessor
from pipeline.batch_processor import BatchProcessor
from pipeline.metadata_generator import generate_metadata

from video.chapter_markers import ChapterMarkerEngine
from utils.youtube_metadata import YouTubeMetadataGenerator
from utils.analytics import TimelineAnalytics

def init_directories():
    """Initialize all output directories."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    os.makedirs(config.VIDEO_DIR, exist_ok=True)
    print("Directories initialized")


def _load_gemini_client():
    try:
        from google import genai
        return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception:
        return None


def load_api_clients():
    """Load available API clients from environment variables."""
    all_clients = []
    
    g_key = os.getenv("GEMINI_API_KEY")
    if g_key:
        gem_client = _load_gemini_client()
        if gem_client is not None:
            all_clients.append({
                "type": "gemini",
                "client": gem_client,
                "model": config.GEMINI_MODEL,
            })
            print("  Gemini API loaded")
    
    # NVIDIA NIM
    for i in range(1, 6):
        nv_key = os.getenv(f"NIM_API_KEY_{i}")
        if not nv_key:
            nv_key = os.getenv(f"NVIDIA_KEY_{i}")
        if not nv_key and i == 1:
            nv_key = os.getenv("NIM_API_KEY")
        if not nv_key and i == 1:
            nv_key = os.getenv("NVIDIA_API_KEY")
        if nv_key:
            all_clients.append({
                "type": "nvidia",
                "client": OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=nv_key,
                ),
                "model": config.NVIDIA_MODEL,
            })
            print(f"  NVIDIA NIM key {i} loaded")
    
    if not all_clients:
        raise RuntimeError("No API keys found in environment variables.")
    
    return all_clients


def discover_tiles():
    """Discover all tile images."""
    tiles = sorted(
        [
            os.path.join(root, f)
            for root, _, files in os.walk(config.BASE_PATH)
            for f in files
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
    )
    
    print(f"   Found {len(tiles)} tiles")
    return tiles


def _resolve_test_mode(
    all_tiles,
    test_mode: bool,
    test_target_minutes: float,
    test_max_tiles: int | None,
):
    """Reduce tile list for quick 2-minute test runs."""
    if not test_mode:
        return all_tiles

    if test_max_tiles is None:
        # Use conservative 4s average tile duration for quick estimation.
        estimated_tiles = ceil((test_target_minutes * 60) / 4.0)
        test_max_tiles = max(1, estimated_tiles)

    limited = all_tiles[: test_max_tiles]
    print(
        f"Test mode enabled: target~{test_target_minutes} min, "
        f"processing first {len(limited)} tiles."
    )
    return limited


def main(test_mode: bool = False, test_target_minutes: float = 2.0, test_max_tiles: int | None = None):
    """Main pipeline execution.

    Args:
        test_mode: If True, process only a small subset for fast validation.
        test_target_minutes: Approximate target duration for test run.
        test_max_tiles: Optional hard cap for tiles in test mode.
    """
    print("Dungeon Odyssey production pipeline v4.1")
    start_time = time.time()
    
    # Initialize
    print("\nInitializing...")
    init_directories()
    
    # Load APIs
    print("\nLoading API credentials...")
    all_clients = load_api_clients()
    
    # Discover tiles
    print("\nDiscovering tiles...")
    all_tiles = discover_tiles()
    if not all_tiles:
        raise RuntimeError(f"No image tiles found in: {config.BASE_PATH}")
    all_tiles = _resolve_test_mode(
        all_tiles=all_tiles,
        test_mode=test_mode,
        test_target_minutes=test_target_minutes,
        test_max_tiles=test_max_tiles,
    )
    
    # Initialize engines
    print("\nInitializing engines...")
    ocr_engine = OCREngine()
    narration_engine = NarrationEngine()
    tts_engine = KokoroTTSEngine()
    chapter_engine = ChapterMarkerEngine()
    
    state_lock = threading.Lock()
    processor = TileProcessor(ocr_engine, narration_engine, all_clients, state_lock)
    batch_processor = BatchProcessor(num_workers=max(1, len(all_clients)))
    
    # Process tiles
    print("\n" + "=" * 80)
    print("PHASE 1: OCR + NARRATION + TIER 1 UPGRADES")
    print("=" * 80)
    
    tile_info = [(i, t) for i, t in enumerate(all_tiles)]
    tile_results = batch_processor.process_tiles(tile_info, processor)
    tile_results = sorted(tile_results, key=lambda x: x.get("order", 0))
    
    # Generate TTS (with Tier 1 pause timing & adaptive speed)
    print("\n" + "=" * 80)
    print("PHASE 2: KOKORO TTS + SMART TIMING")
    print("=" * 80)
    
    audio_manifest = tts_engine.batch_generate(tile_results, config.AUDIO_DIR)
    
    # Generate chapters (Tier 2)
    print("\n" + "=" * 80)
    print("PHASE 3: CHAPTER DETECTION (TIER 2)")
    print("=" * 80)
    
    chapters = chapter_engine.generate_chapters_from_tiles(tile_results)
    print(f"Generated {len(chapters)} chapters")
    
    # Generate metadata
    print("\n" + "=" * 80)
    print("PHASE 4: METADATA & ANALYTICS (TIER 2)")
    print("=" * 80)
    
    metadata = generate_metadata(tile_results, audio_manifest)
    
    # Analytics
    retention_analysis = TimelineAnalytics.predict_retention(tile_results)
    pacing_analysis = TimelineAnalytics.analyze_pacing(tile_results)
    
    # YouTube metadata (Tier 2)
    youtube_metadata = YouTubeMetadataGenerator.generate_metadata(
        metadata,
        [ch.to_dict() for ch in chapters],
        metadata["total_duration_min"],
    )
    
    # Save all outputs
    print("\n" + "=" * 80)
    print("SAVING OUTPUTS")
    print("=" * 80)
    
    with open(config.MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(tile_results, f, indent=2, ensure_ascii=False)
    print(config.MASTER_JSON)
    
    with open(config.METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(config.METADATA_JSON)
    
    with open(config.AUDIO_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(audio_manifest, f, indent=2, ensure_ascii=False)
    print(config.AUDIO_MANIFEST)
    
    chapter_engine.save_chapters(config.CHAPTER_MARKERS)
    
    YouTubeMetadataGenerator.save_metadata(youtube_metadata, config.YOUTUBE_METADATA)
    
    # Save analytics
    analytics_file = os.path.join(config.OUTPUT_DIR, "analytics.json")
    with open(analytics_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "retention_analysis": retention_analysis,
                "pacing_analysis": pacing_analysis,
            },
            f,
            indent=2,
        )
    print(analytics_file)
    
    # Final report
    elapsed_min = (time.time() - start_time) / 60
    
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Tiles processed   : {metadata['total_tiles']}")
    print(f"Duration (min)    : {metadata['total_duration_min']}")
    print(f"TTS entries       : {metadata['tts_script_entries']}")
    print(f"Chapters detected : {len(chapters)}")
    print(f"Output directory  : {config.OUTPUT_DIR}")
    print(f"Processing time   : {elapsed_min:.1f} min")
    
    return {
        "tiles": tile_results,
        "metadata": metadata,
        "audio_manifest": audio_manifest,
        "chapters": chapters,
        "youtube_metadata": youtube_metadata,
        "analytics": {
            "retention": retention_analysis,
            "pacing": pacing_analysis,
        },
    }


if __name__ == "__main__":
    env_test_mode = os.getenv("PIPELINE_TEST_MODE", "0").strip().lower() in {"1", "true", "yes"}
    env_target_min = float(os.getenv("PIPELINE_TEST_TARGET_MIN", "2"))
    env_max_tiles = os.getenv("PIPELINE_TEST_MAX_TILES")
    pipeline_output = main(
        test_mode=env_test_mode,
        test_target_minutes=env_target_min,
        test_max_tiles=int(env_max_tiles) if env_max_tiles else None,
    )