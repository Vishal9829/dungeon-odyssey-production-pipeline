"""Convenience wrapper to render final video from pipeline outputs."""

from __future__ import annotations

import os

from pipeline.config import config
from video.compositor import render_dungeon_odyssey_video


def render_from_config(output_name: str = "DUNGEON_ODYSSEY_FINAL_v4_1.mp4", bgm_path: str | None = None) -> bool:
    output_video_path = os.path.join(config.OUTPUT_DIR, output_name)
    return render_dungeon_odyssey_video(
        master_json_path=config.MASTER_JSON,
        audio_manifest_path=config.AUDIO_MANIFEST,
        audio_dir=config.AUDIO_DIR,
        output_video_path=output_video_path,
        bgm_path=bgm_path,
    )


if __name__ == "__main__":
    ok = render_from_config()
    print(f"Render success: {ok}")

