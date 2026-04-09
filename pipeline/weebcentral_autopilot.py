"""One-entry Colab autopilot for any WeebCentral manhua pipeline.

Workflow:
1) paste WeebCentral URL
2) enter chapters to download/process
3) choose target video length in minutes
4) run resumable end-to-end pipeline with organized output folders
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from openai import OpenAI

from pipeline.config import config
from pipeline.metadata_generator import generate_metadata
from pipeline.narration_engine import NarrationEngine
from pipeline.ocr_engine import OCREngine
from pipeline.tile_processor import TileProcessor
from pipeline.tts_engine import KokoroTTSEngine
from utils.analytics import TimelineAnalytics
from utils.colab_weebcentral import (
    clone_weebcentral_downloader,
    download_chapters_as_images,
    install_colab_dependencies,
    print_best_tile_tweaks,
)
from utils.youtube_metadata import YouTubeMetadataGenerator
from video.chapter_markers import ChapterMarkerEngine
from video.compositor import render_dungeon_odyssey_video


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "manhua"


def _series_name_from_url(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1]
    return _slugify(tail)


def _is_weebcentral_url(url: str) -> bool:
    return "weebcentral.com/series/" in url.lower()


def _get_secret(key: str) -> Optional[str]:
    value = os.getenv(key)
    if value:
        return value
    try:
        from google.colab import userdata  # type: ignore

        return userdata.get(key)
    except Exception:
        return None


def _load_clients() -> List[Dict]:
    clients: List[Dict] = []
    gemini_key = _get_secret("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai

            clients.append(
                {
                    "type": "gemini",
                    "client": genai.Client(api_key=gemini_key),
                    "model": config.GEMINI_MODEL,
                }
            )
        except Exception:
            pass

    for i in range(1, 6):
        k = _get_secret(f"NIM_API_KEY_{i}")
        if not k:
            k = _get_secret(f"NVIDIA_KEY_{i}")
        if not k and i == 1:
            k = _get_secret("NIM_API_KEY")
        if not k and i == 1:
            k = _get_secret("NVIDIA_API_KEY")
        if k:
            clients.append(
                {
                    "type": "nvidia",
                    "client": OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=k),
                    "model": config.NVIDIA_MODEL,
                }
            )
    if not clients:
        raise RuntimeError("No API keys found. Set GEMINI_API_KEY and/or NIM_API_KEY_1.")
    return clients


def _generate_character_bible(series_title: str, clients: List[Dict], output_path: str) -> str:
    """Use Gemini to generate a web-knowledge character bible and cache it."""
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("character_bible_text", "")

    gemini = next((c for c in clients if c["type"] == "gemini"), None)
    if not gemini:
        text = f"Series: {series_title}\nNo Gemini client available, using default lore prompt."
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"series_title": series_title, "character_bible_text": text}, f, indent=2)
        return text

    prompt = (
        f"Create a concise character bible for the manhua '{series_title}'. "
        "Use your best available public/web knowledge and include: main cast, factions, powers, "
        "aliases, relationships, and recurring themes. Keep it factual and structured with bullets."
    )
    try:
        resp = gemini["client"].models.generate_content(model=gemini["model"], contents=prompt)
        text = (resp.text or "").strip()
    except Exception:
        text = f"Series: {series_title}\nCharacter bible generation failed; fallback mode."

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"series_title": series_title, "character_bible_text": text}, f, indent=2, ensure_ascii=False)
    return text


def _apply_duration_target(tile_results: List[Dict], target_minutes: float) -> List[Dict]:
    """Scale tile durations to approximately hit requested final video length."""
    if not tile_results:
        return tile_results
    current_total = sum(float(t.get("estimated_screen_time_sec", 3.0)) for t in tile_results)
    target_total = max(60.0, float(target_minutes) * 60.0)
    if current_total <= 0:
        return tile_results
    scale = target_total / current_total
    for t in tile_results:
        d = float(t.get("estimated_screen_time_sec", 3.0)) * scale
        t["estimated_screen_time_sec"] = round(max(1.8, min(10.0, d)), 2)
    return tile_results


def _pick_bgm_from_assets(assets_root: Optional[str]) -> Optional[str]:
    if not assets_root or not os.path.isdir(assets_root):
        return None
    candidates: List[str] = []
    for root, _, files in os.walk(assets_root):
        for f in files:
            if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".flac")) and "bgm" in root.lower():
                candidates.append(os.path.join(root, f))
    return sorted(candidates)[0] if candidates else None


def _resolve_sfx_dir(assets_root: Optional[str]) -> Optional[str]:
    if not assets_root or not os.path.isdir(assets_root):
        return None
    for root, dirs, _ in os.walk(assets_root):
        for d in dirs:
            if d.lower() == "sfx":
                return os.path.join(root, d)
    return None


def _list_tiles(base_path: str) -> List[str]:
    return sorted(
        [
            os.path.join(root, f)
            for root, _, files in os.walk(base_path)
            for f in files
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
    )


def run_weebcentral_pipeline(
    series_url: str,
    chapter_selection: str,
    target_video_minutes: float,
    workspace_root: str = "/content/manhua_pipeline",
    assets_root: Optional[str] = None,
    trend_mode: bool = True,
) -> Dict:
    if not _is_weebcentral_url(series_url):
        raise ValueError("Only WeebCentral series links are supported.")

    install_colab_dependencies()
    clone_weebcentral_downloader()

    series_slug = _series_name_from_url(series_url)
    series_root = os.path.join(workspace_root, series_slug)
    download_root = os.path.join(series_root, "downloaded_chapters")
    os.makedirs(series_root, exist_ok=True)
    os.makedirs(download_root, exist_ok=True)

    # 1) Download using original downloader output (raw page images only).
    output_dir, chapters, manga_info = download_chapters_as_images(
        series_url=series_url,
        selection=chapter_selection,
        output_dir=download_root,
    )
    # Important: do NOT stitch or delete raw pages here.
    # OCR is more stable on original page images and avoids Tesseract "image too large" errors.
    print_best_tile_tweaks()

    # 2) Dynamic config paths per manhua
    config.BASE_PATH = output_dir
    config.OUTPUT_DIR = os.path.join(series_root, "pipeline_output")
    config.__post_init__()
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    os.makedirs(config.VIDEO_DIR, exist_ok=True)

    progress_file = os.path.join(config.OUTPUT_DIR, "progress_state.json")
    character_file = os.path.join(config.OUTPUT_DIR, "character_bible.json")
    final_video_path = os.path.join(config.OUTPUT_DIR, "final_video.mp4")
    bgm_path = _pick_bgm_from_assets(assets_root)
    sfx_dir = _resolve_sfx_dir(assets_root)

    clients = _load_clients()
    character_bible = _generate_character_bible(series_slug, clients, character_file)
    lore_override = (
        "=== SERIES CHARACTER BIBLE ===\n"
        + character_bible
        + "\n=== END CHARACTER BIBLE ===\n"
        + "Narrate in epic recap style with clear pacing and transitions."
    )

    # 3) Resumable processing
    existing_tiles: List[Dict] = []
    if os.path.exists(config.MASTER_JSON):
        with open(config.MASTER_JSON, "r", encoding="utf-8") as f:
            existing_tiles = json.load(f)
    done_tiles = {x.get("tile") for x in existing_tiles}

    all_tiles = _list_tiles(config.BASE_PATH)
    remaining = [p for p in all_tiles if os.path.basename(p) not in done_tiles]

    ocr_engine = OCREngine()
    narration_engine = NarrationEngine(lore_bible_override=lore_override)
    processor = TileProcessor(ocr_engine, narration_engine, clients, state_lock=None)

    tile_results = existing_tiles[:]
    if remaining:
        # Sequential save-after-each tile for robust resume.
        for idx, tile_path in enumerate(remaining, start=1):
            result = processor.process((idx, tile_path))
            if not result:
                continue
            tile_results.append(result)
            with open(config.MASTER_JSON, "w", encoding="utf-8") as f:
                json.dump(tile_results, f, indent=2, ensure_ascii=False)
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "phase": "tile_processing",
                        "processed": len(tile_results),
                        "total": len(all_tiles),
                    },
                    f,
                    indent=2,
                )

    # 4) Fit requested duration
    tile_results = _apply_duration_target(tile_results, target_video_minutes)
    with open(config.MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(tile_results, f, indent=2, ensure_ascii=False)

    # 5) TTS (resumable at manifest level)
    if os.path.exists(config.AUDIO_MANIFEST):
        with open(config.AUDIO_MANIFEST, "r", encoding="utf-8") as f:
            audio_manifest = json.load(f)
    else:
        tts_engine = KokoroTTSEngine()
        audio_manifest = tts_engine.batch_generate(tile_results, config.AUDIO_DIR)
        with open(config.AUDIO_MANIFEST, "w", encoding="utf-8") as f:
            json.dump(audio_manifest, f, indent=2, ensure_ascii=False)

    # 6) Metadata + chapters
    chapter_engine = ChapterMarkerEngine()
    chapters = chapter_engine.generate_chapters_from_tiles(tile_results)
    chapter_engine.save_chapters(config.CHAPTER_MARKERS)

    metadata = generate_metadata(tile_results, audio_manifest)
    with open(config.METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    analytics = {
        "retention_analysis": TimelineAnalytics.predict_retention(tile_results, int(target_video_minutes)),
        "pacing_analysis": TimelineAnalytics.analyze_pacing(tile_results),
    }
    with open(os.path.join(config.OUTPUT_DIR, "analytics.json"), "w", encoding="utf-8") as f:
        json.dump(analytics, f, indent=2, ensure_ascii=False)

    yt = YouTubeMetadataGenerator.generate_metadata(metadata, [c.to_dict() for c in chapters], metadata["total_duration_min"])
    YouTubeMetadataGenerator.save_metadata(yt, config.YOUTUBE_METADATA)

    # 7) Final render (resumable: skip if exists)
    if not os.path.exists(final_video_path):
        export_options = {
            "width": 1920,
            "fps": 30,
            "codec": "libx264",
            "bitrate": "12000k" if trend_mode else "8000k",
            "preset": "slow" if trend_mode else "medium",
        }
        render_dungeon_odyssey_video(
            master_json_path=config.MASTER_JSON,
            audio_manifest_path=config.AUDIO_MANIFEST,
            audio_dir=config.AUDIO_DIR,
            output_video_path=final_video_path,
            bgm_path=bgm_path,
            sfx_dir=sfx_dir,
            export_options=export_options,
        )

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "phase": "completed",
                "series": series_slug,
                "output_dir": config.OUTPUT_DIR,
                "final_video": final_video_path,
            },
            f,
            indent=2,
        )

    return {
        "series": series_slug,
        "series_root": series_root,
        "output_dir": config.OUTPUT_DIR,
        "tiles": len(tile_results),
        "target_video_minutes": target_video_minutes,
        "final_video": final_video_path,
        "bgm_path": bgm_path,
        "sfx_dir": sfx_dir,
        "metadata_json": config.METADATA_JSON,
        "master_json": config.MASTER_JSON,
        "audio_manifest": config.AUDIO_MANIFEST,
    }


def run_interactive() -> Dict:
    """Prompt-driven Colab runner."""
    print("WeebCentral Autopilot")
    series_url = input("Paste WeebCentral manhua link: ").strip()
    if not _is_weebcentral_url(series_url):
        raise ValueError("Invalid link. Please paste a WeebCentral /series/ URL.")

    chapter_selection = input("Enter chapter selection (all / range 1-10 / 1,5,9): ").strip()
    duration_raw = input("Target final video length in minutes (e.g. 120): ").strip()
    target_minutes = float(duration_raw)
    assets_root = input(
        "Optional assets root path (contains BGM and SFX folders in Drive, or leave blank): "
    ).strip()
    trend_mode_raw = input("Enable competition quality mode? (y/n, default y): ").strip().lower()
    trend_mode = trend_mode_raw not in {"n", "no", "0", "false"}

    return run_weebcentral_pipeline(
        series_url=series_url,
        chapter_selection=chapter_selection,
        target_video_minutes=target_minutes,
        assets_root=assets_root or None,
        trend_mode=trend_mode,
    )

