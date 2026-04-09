"""Merged Colab runner: original WeebCentral downloader + pipeline processing.

This keeps the original downloader behavior (raw pages), saves to Google Drive,
and automatically starts the next processing step.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Dict, List

from pipeline.config import config
from pipeline.metadata_generator import generate_metadata
from pipeline.narration_engine import NarrationEngine
from pipeline.ocr_engine import OCREngine
from pipeline.tile_processor import TileProcessor
from pipeline.tts_engine import KokoroTTSEngine
from pipeline.weebcentral_autopilot import (
    _generate_character_bible,
    _load_clients,
)
from utils.analytics import TimelineAnalytics
from utils.youtube_metadata import YouTubeMetadataGenerator
from video.chapter_markers import ChapterMarkerEngine
from video.compositor import render_dungeon_odyssey_video


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "manhua"


def _install_and_clone_downloader() -> None:
    pkgs = [
        "requests",
        "httpx[http2]",
        "nest_asyncio",
        "beautifulsoup4",
        "lxml",
        "Pillow",
        "fpdf2",
        "tqdm",
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *pkgs], check=True)
    if not os.path.exists("/content/weebcentral_downloader"):
        subprocess.run(
            ["git", "clone", "https://github.com/Yui007/weebcentral_downloader", "/content/weebcentral_downloader"],
            check=True,
        )


def _load_downloader_modules():
    mod_path = "/content/weebcentral_downloader/colab"
    if mod_path not in sys.path:
        sys.path.insert(0, mod_path)
    from colab_scraper import scrape_manga_info, scrape_chapter_list  # type: ignore
    from colab_downloader import parse_chapter_selection, download_chapters  # type: ignore

    return scrape_manga_info, scrape_chapter_list, parse_chapter_selection, download_chapters


def _scale_durations(results: List[Dict], target_minutes: float) -> List[Dict]:
    current = sum(float(t.get("estimated_screen_time_sec", 3.0)) for t in results)
    target = max(60.0, float(target_minutes) * 60.0)
    if current <= 0:
        return results
    scale = target / current
    for item in results:
        d = float(item.get("estimated_screen_time_sec", 3.0)) * scale
        item["estimated_screen_time_sec"] = round(max(1.8, min(10.0, d)), 2)
    return results


def run_merged_interactive() -> Dict:
    """Run full merged flow in Colab and save outputs directly to Drive."""
    try:
        from google.colab import drive  # type: ignore

        drive.mount("/content/drive")
    except Exception:
        pass

    _install_and_clone_downloader()
    scrape_manga_info, scrape_chapter_list, parse_chapter_selection, download_chapters = _load_downloader_modules()

    series_url = input("Paste WeebCentral series URL: ").strip()
    if "weebcentral.com/series/" not in series_url.lower():
        raise ValueError("Only WeebCentral series links are supported.")

    manga_info = scrape_manga_info(series_url)
    chapters = scrape_chapter_list(series_url)
    total = len(chapters)
    print(f"Found {total} chapters")

    selection = input(f"Select chapters (all / range 1-10 / single 5 / 1,5,9) [1-{total}]: ").strip()
    selected = parse_chapter_selection(selection, total)

    target_minutes = float(input("Target final video length (minutes): ").strip())
    assets_root = input(
        "Optional assets root in Drive (contains BGM and sfx), or blank: "
    ).strip()

    series_slug = _slugify(manga_info.get("title", "") or series_url.rstrip("/").split("/")[-1])
    series_root = f"/content/drive/MyDrive/manhua_pipeline/{series_slug}"
    download_root = f"{series_root}/downloaded_chapters"
    os.makedirs(download_root, exist_ok=True)

    # Original downloader code path: output raw images.
    output_dir = download_chapters(
        manga_info=manga_info,
        chapters=chapters,
        selected_indices=selected,
        output_format="images",
        output_dir=download_root,
    )

    # Configure output locations in Drive.
    config.BASE_PATH = output_dir
    config.OUTPUT_DIR = f"{series_root}/pipeline_output"
    config.__post_init__()
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    os.makedirs(config.VIDEO_DIR, exist_ok=True)

    clients = _load_clients()
    character_path = os.path.join(config.OUTPUT_DIR, "character_bible.json")
    character_bible = _generate_character_bible(series_slug, clients, character_path)
    lore_override = (
        "=== SERIES CHARACTER BIBLE ===\n"
        + character_bible
        + "\n=== END CHARACTER BIBLE ===\n"
        + "Narrate in epic recap style and keep pacing optimized."
    )

    # Resume support.
    existing: List[Dict] = []
    if os.path.exists(config.MASTER_JSON):
        with open(config.MASTER_JSON, "r", encoding="utf-8") as f:
            existing = json.load(f)
    done = {x.get("tile") for x in existing}

    all_tiles = sorted(
        [
            os.path.join(root, f)
            for root, _, files in os.walk(config.BASE_PATH)
            for f in files
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
    )
    remaining = [p for p in all_tiles if os.path.basename(p) not in done]

    ocr = OCREngine()
    narr = NarrationEngine(lore_bible_override=lore_override)
    proc = TileProcessor(ocr, narr, clients, state_lock=None)

    results = existing[:]
    progress_path = os.path.join(config.OUTPUT_DIR, "progress_state.json")

    for idx, tile_path in enumerate(remaining, start=1):
        row = proc.process((idx, tile_path))
        if not row:
            continue
        results.append(row)
        if idx % 10 == 0:
            with open(config.MASTER_JSON, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump({"phase": "processing", "processed": len(results), "total": len(all_tiles)}, f, indent=2)

    results = _scale_durations(results, target_minutes)
    with open(config.MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    tts = KokoroTTSEngine()
    audio_manifest = tts.batch_generate(results, config.AUDIO_DIR)
    with open(config.AUDIO_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(audio_manifest, f, indent=2, ensure_ascii=False)

    chapters_engine = ChapterMarkerEngine()
    chapters_out = chapters_engine.generate_chapters_from_tiles(results)
    chapters_engine.save_chapters(config.CHAPTER_MARKERS)

    metadata = generate_metadata(results, audio_manifest)
    with open(config.METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    analytics = {
        "retention_analysis": TimelineAnalytics.predict_retention(results, int(target_minutes)),
        "pacing_analysis": TimelineAnalytics.analyze_pacing(results),
    }
    with open(os.path.join(config.OUTPUT_DIR, "analytics.json"), "w", encoding="utf-8") as f:
        json.dump(analytics, f, indent=2, ensure_ascii=False)

    yt = YouTubeMetadataGenerator.generate_metadata(
        metadata, [c.to_dict() for c in chapters_out], metadata["total_duration_min"]
    )
    YouTubeMetadataGenerator.save_metadata(yt, config.YOUTUBE_METADATA)

    # Optional assets
    bgm_path = None
    sfx_dir = None
    if assets_root and os.path.isdir(assets_root):
        for root, _, files in os.walk(assets_root):
            if bgm_path is None and "bgm" in root.lower():
                audio = [f for f in files if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"))]
                if audio:
                    bgm_path = os.path.join(root, sorted(audio)[0])
            if sfx_dir is None and os.path.basename(root).lower() == "sfx":
                sfx_dir = root

    final_video = os.path.join(config.OUTPUT_DIR, "final_video.mp4")
    render_dungeon_odyssey_video(
        master_json_path=config.MASTER_JSON,
        audio_manifest_path=config.AUDIO_MANIFEST,
        audio_dir=config.AUDIO_DIR,
        output_video_path=final_video,
        bgm_path=bgm_path,
        sfx_dir=sfx_dir,
        export_options={"width": 1920, "fps": 30, "codec": "libx264", "bitrate": "12000k", "preset": "slow"},
    )

    with open(progress_path, "w", encoding="utf-8") as f:
        json.dump({"phase": "completed", "final_video": final_video, "output_dir": config.OUTPUT_DIR}, f, indent=2)

    return {
        "series": series_slug,
        "output_dir": config.OUTPUT_DIR,
        "download_dir": output_dir,
        "final_video": final_video,
    }

