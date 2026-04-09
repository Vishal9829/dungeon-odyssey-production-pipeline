# 🎬 Dungeon Odyssey Production Pipeline v4.1

Fully automated video production: OCR -> narration -> TTS -> MoviePy composition.

## 🚀 Features

- Advanced OCR (Tesseract + optional Gemini Vision assist)
- Context-aware narration with repetition control
- Kokoro TTS support and adaptive pacing
- MoviePy composition with overlays, VFX, and chapter metadata
- WeebCentral-only autopilot for one-input Colab workflow
- Resumable progress with saved JSON/audio/video artifacts

## 🧩 Colab Download Prep

`utils/colab_weebcentral.py` automates:

- dependency install
- WeebCentral downloader clone
- chapter download as images
- chapter stitching and raw-image cleanup
- tile quality tweak tips for better OCR/narration

## 🤖 WeebCentral Autopilot

`pipeline/weebcentral_autopilot.py` supports:

- paste WeebCentral link
- choose chapter selection
- choose target video length (minutes)
- optional assets root for BGM/SFX
- auto-create `/content/manhua_pipeline/<series>/...`
- trend-mode render options for competitive output
- resumable outputs via `progress_state.json`
