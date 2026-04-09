"""Colab helper utilities for WeebCentral chapter download and tile prep.

This module wraps the same flow as your notebook cells:
1) install + clone downloader
2) scrape + select + download chapters as images
3) stitch images per chapter
4) clean raw page files while keeping stitched outputs
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from PIL import Image


DEFAULT_REPO_URL = "https://github.com/Yui007/weebcentral_downloader"
DEFAULT_CLONE_DIR = "/content/weebcentral_downloader"
DEFAULT_OUTPUT_DIR = "/content/weebcentral_downloader/colab/manga"


def install_colab_dependencies() -> None:
    """Install downloader support dependencies in Colab."""
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
    subprocess.run(["pip", "install", "-q", *pkgs], check=True)


def clone_weebcentral_downloader(clone_dir: str = DEFAULT_CLONE_DIR) -> str:
    """Clone or refresh the downloader repo."""
    if os.path.exists(clone_dir):
        return clone_dir
    subprocess.run(["git", "clone", DEFAULT_REPO_URL, clone_dir], check=True)
    return clone_dir


def _prepare_downloader_imports(clone_dir: str = DEFAULT_CLONE_DIR) -> Tuple:
    colab_mod_path = os.path.join(clone_dir, "colab")
    if colab_mod_path not in sys.path:
        sys.path.insert(0, colab_mod_path)

    from colab_scraper import scrape_chapter_list, scrape_manga_info  # type: ignore
    from colab_downloader import download_chapters, parse_chapter_selection  # type: ignore

    return scrape_manga_info, scrape_chapter_list, parse_chapter_selection, download_chapters


def download_chapters_as_images(
    series_url: str,
    selection: str = "all",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    clone_dir: str = DEFAULT_CLONE_DIR,
) -> Tuple[str, List[dict], dict]:
    """Download selected chapters as raw images.

    Args:
        series_url: WeebCentral series URL.
        selection: "all", "single 5", "range 1-10", "1,5,9".
        output_dir: Destination directory.
        clone_dir: Local downloader clone path.

    Returns:
        (output_dir, chapter_list, manga_info)
    """
    scrape_manga_info, scrape_chapter_list, parse_selection, download_chapters = _prepare_downloader_imports(clone_dir)

    manga_info = scrape_manga_info(series_url)
    chapters = scrape_chapter_list(series_url)
    total = len(chapters)
    selected = parse_selection(selection.strip(), total)

    resolved_output = download_chapters(
        manga_info=manga_info,
        chapters=chapters,
        selected_indices=selected,
        output_format="images",
        output_dir=output_dir,
    )
    return resolved_output, chapters, manga_info


def _iter_chapter_folders(output_dir: str) -> Iterable[str]:
    if not os.path.isdir(output_dir):
        return []
    folders = [
        os.path.join(output_dir, d)
        for d in os.listdir(output_dir)
        if os.path.isdir(os.path.join(output_dir, d))
    ]
    return sorted(folders)


def stitch_chapter_images(
    chapter_folder_path: str,
    chapter_name: str,
    max_stitched_height: int = 60000,
    jpeg_quality: int = 88,
) -> List[str]:
    """Stitch page images in a chapter folder into one or more long images."""
    image_files = sorted(
        [
            f
            for f in os.listdir(chapter_folder_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
    )
    if not image_files:
        return []

    images: List[Image.Image] = []
    for file_name in image_files:
        path = os.path.join(chapter_folder_path, file_name)
        try:
            with Image.open(path) as img:
                # Force RGB to avoid palette/alpha issues during paste-save.
                images.append(img.convert("RGB"))
        except Exception:
            continue

    if not images:
        return []

    max_width = max(img.width for img in images)
    total_height = sum(img.height for img in images)

    output_format = "WEBP"
    output_ext = ".webp"
    if max_width > 16383 or total_height > 16383:
        output_format = "JPEG"
        output_ext = ".jpeg"

    saved_outputs: List[str] = []
    current_chunk: List[Image.Image] = []
    current_height = 0
    part_count = 1

    def _save_chunk(chunk: List[Image.Image], part_num: int) -> None:
        nonlocal saved_outputs
        if not chunk:
            return
        chunk_width = max(img.width for img in chunk)

        resized_chunk: List[Image.Image] = []
        for img in chunk:
            if img.width == chunk_width:
                resized_chunk.append(img)
            else:
                ratio = chunk_width / float(img.width)
                new_h = max(1, int(img.height * ratio))
                resized_chunk.append(img.resize((chunk_width, new_h), Image.LANCZOS))

        chunk_total_h = sum(img.height for img in resized_chunk)
        canvas = Image.new("RGB", (chunk_width, chunk_total_h))

        y_offset = 0
        for img in resized_chunk:
            canvas.paste(img, (0, y_offset))
            y_offset += img.height

        out_name = f"{chapter_name}{output_ext}" if part_num == 1 else f"{chapter_name}_Part{part_num}{output_ext}"
        out_path = os.path.join(chapter_folder_path, out_name)
        if output_format == "WEBP":
            canvas.save(out_path, output_format, quality=jpeg_quality, method=6)
        else:
            canvas.save(out_path, output_format, quality=jpeg_quality, optimize=True)
        saved_outputs.append(out_path)

    for img in images:
        if current_chunk and (current_height + img.height > max_stitched_height):
            _save_chunk(current_chunk, part_count)
            current_chunk = []
            current_height = 0
            part_count += 1
        current_chunk.append(img)
        current_height += img.height

    if current_chunk:
        _save_chunk(current_chunk, part_count)

    return saved_outputs


def stitch_all_chapters(
    output_dir: str,
    max_stitched_height: int = 60000,
    jpeg_quality: int = 88,
) -> List[str]:
    """Stitch all chapter folders under output_dir."""
    stitched: List[str] = []
    for folder in _iter_chapter_folders(output_dir):
        chapter_name = os.path.basename(folder)
        stitched.extend(
            stitch_chapter_images(
                chapter_folder_path=folder,
                chapter_name=chapter_name,
                max_stitched_height=max_stitched_height,
                jpeg_quality=jpeg_quality,
            )
        )
    return stitched


def clean_raw_images(output_dir: str) -> int:
    """Delete raw per-page image files, keep stitched chapter outputs."""
    deleted = 0
    for folder in _iter_chapter_folders(output_dir):
        chapter_name = os.path.basename(folder)
        for file_name in os.listdir(folder):
            path = os.path.join(folder, file_name)
            if not os.path.isfile(path):
                continue

            lower = file_name.lower()
            is_image = lower.endswith((".png", ".jpg", ".jpeg", ".webp"))
            is_stitched = file_name.startswith(chapter_name) and lower.endswith((".jpeg", ".webp"))

            if is_image and not is_stitched:
                try:
                    os.remove(path)
                    deleted += 1
                except Exception:
                    pass
    return deleted


def print_best_tile_tweaks() -> None:
    """Print practical tuning tips for best OCR-ready tiles."""
    tips = [
        "Use output_format='images' and stitch with quality=88+ to preserve text edges.",
        "Keep max_stitched_height around 40k-60k; too huge images increase OCR failures.",
        "Prefer WEBP for normal dimensions; fallback to JPEG for >16383px dimensions.",
        "Avoid aggressive denoising/compression before OCR; it blurs dialogue glyphs.",
        "If OCR misses dialogue, run OCR per raw page instead of only stitched image.",
        "After stitching, keep chapter folder naming stable so downstream sorting is deterministic.",
    ]
    print("Best tile tweaks:")
    for idx, tip in enumerate(tips, start=1):
        print(f"{idx}. {tip}")

