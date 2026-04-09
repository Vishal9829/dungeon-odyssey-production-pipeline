\# 🚀 Dungeon Odyssey Production Pipeline v4.1 — Complete Setup Guide



\## Prerequisites



✅ Google Colab with GPU

✅ Google Drive with dungeon tiles

✅ API Keys (Gemini + NVIDIA optional)



\## Quick Start (3 Steps)



\### Step 1: Install Environment



```bash

\# In Colab cell 1:

!bash setup\_environment.sh

```



\### Step 2: Set API Keys



```python

\# In Colab cell 2:

from google.colab import userdata



userdata.set('GEMINI\_API\_KEY', 'your-gemini-key')

userdata.set('NVIDIA\_KEY\_1', 'your-nvidia-key')

```



\### Step 3: Run Pipeline



```python

\# In Colab cell 3:

from pipeline.main import main



result = main()

# Quick test run (~2 min target timeline)
test_result = main(test_mode=True, test_target_minutes=2.0)

```



\## Outputs Generated



✅ `dungeon\_odyssey\_master\_v4\_1.json` — Complete tile analysis

✅ `pipeline\_metadata\_v4\_1.json` — Video stats \& quality metrics

✅ `audio\_manifest.json` — TTS audio file mapping

✅ `chapter\_markers.json` — YouTube chapter timestamps

✅ `youtube\_metadata.json` — SEO-optimized metadata

✅ `analytics.json` — Retention \& pacing analysis

✅ `audio/` — 1000+ TTS audio files (Kokoro)

✅ `video/` — Video composition ready



\## Tier 1 Upgrades ⭐ (Implemented)



✅ \*\*Smart Pause Timing\*\* — Importance \& emotion-based delays

✅ \*\*Adaptive TTS Speed\*\* — Slow for dramatic, fast for action

✅ \*\*SFX Layer\*\* — Scene-type mapped sound effects

✅ \*\*Color Grading\*\* — Emotion-based cinematic looks



\## Tier 2 Upgrades ⭐⭐ (Implemented)



✅ \*\*Adaptive VFX\*\* — Zoom, fade, vignette by importance

✅ \*\*Chapter Markers\*\* — Auto-detect + format for YouTube

✅ \*\*YouTube Metadata\*\* — Complete SEO optimization

✅ \*\*Analytics\*\* — Retention prediction \& pacing analysis



\## Customization



Edit `pipeline/config.py` to customize:



```python

\# TTS voice \& speed

TTS\_VOICE = 'af\_bella'  # Male deep voice

TTS\_SPEED\_BASE = 0.95



\# SFX settings

SFX\_ENABLED = True

SFX\_VOLUME = 0.4



\# VFX settings

VFX\_ENABLED = True

VFX\_BY\_IMPORTANCE = {...}



\# Chapter settings

CHAPTERS\_ENABLED = True

CHAPTER\_IMPORTANCE\_THRESHOLD = 8



\# YouTube metadata

YOUTUBE\_TITLE\_TEMPLATE = "DUNGEON ODYSSEY..."

```



\## Next: Video Rendering



Once pipeline completes, render video:



```python

from video.renderer import render\_dungeon\_odyssey\_video



render\_dungeon\_odyssey\_video(

&#x20;   master\_json\_path=config.MASTER\_JSON,

&#x20;   audio\_manifest\_path=config.AUDIO\_MANIFEST,

&#x20;   audio\_dir=config.AUDIO\_DIR,

&#x20;   output\_video\_path=os.path.join(config.OUTPUT\_DIR, 'FINAL\_VIDEO.mp4'),

&#x20;   bgm\_path=None  # Optional: your background music

)

```



\## Quality Targets



✅ Duration: 60-90 minutes

✅ OCR Confidence: >70%

✅ Narration Uniqueness: >90%

✅ Video: 1080p, 30fps, 8000kbps

✅ Audio: Frame-accurate sync



\## Troubleshooting



\### Kokoro TTS Not Installing

```bash

pip install git+https://github.com/remsky/Kokoro-82M.git

```



\### Out of Memory

\- Reduce `NUM\_WORKERS` in config

\- Process tiles in batches



\### API Rate Limits

\- Increase `API\_RATE\_LIMIT\_DELAY\_SEC`

\- Rotate between multiple API keys



\---



\*\*Ready?\*\* Run the pipeline now and check `/pipeline\_output\_v4\_1/` for results!

## Colab Downloader Module (WeebCentral)

Use the built-in helper module that mirrors your 4-cell downloader flow:

```python
from utils.colab_weebcentral import (
    install_colab_dependencies,
    clone_weebcentral_downloader,
    download_chapters_as_images,
    stitch_all_chapters,
    clean_raw_images,
    print_best_tile_tweaks,
)

install_colab_dependencies()
clone_weebcentral_downloader()

series_url = "https://weebcentral.com/series/01JNKGRKJ61H73S8M5CKZ5FKWD/dungeon-odyssey"
output_dir, chapters, manga_info = download_chapters_as_images(
    series_url=series_url,
    selection="range 1-30",  # "all", "single 5", "1,3,9"
)

stitched = stitch_all_chapters(output_dir, max_stitched_height=50000, jpeg_quality=90)
deleted = clean_raw_images(output_dir)

print(f"Stitched files: {len(stitched)} | Raw pages removed: {deleted}")
print_best_tile_tweaks()
```

## One-Input WeebCentral Autopilot (Colab)

For fully automated flow (download + process + render + resume), use:

```python
from pipeline.weebcentral_autopilot import run_interactive

result = run_interactive()
print(result)
```

It will:
- accept only WeebCentral series links
- ask chapter selection and target video minutes
- create `/content/manhua_pipeline/<manhua-name>/...`
- save progress continuously in `progress_state.json`
- resume from existing JSON/audio/video files on re-run

