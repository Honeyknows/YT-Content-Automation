<div align="center">

# 🎬 YT Content Automation

### Drop a chapter URL. Get a narrated, CapCut-ready recap video — automatically.

One URL. A full AI-narrated, character-aware, editable CapCut project — automatically.

![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/status-active%20development-orange?style=flat-square)
![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)

</div>

<br>

## The Problem

Visual content recap channels are blowing up on YouTube. The actual workflow behind most of them is brutal: download images manually, crop them, write a script by hand, record or outsource voiceover, drop everything into an editor, sync timing by eye, render, repeat — for every single episode, every single week.

**YT Content Automation replaces that entire manual chain with one pipeline.**

You give it a source URL. It hands you back a fully narrated script *and* an editable CapCut project — synced, timed, ready to scrub through and tweak before you hit publish. You stay in control of the final cut; the tool kills the 4 hours of grunt work that happen before it.

<br>

## ✨ What It Actually Does

| Stage | What happens |
|---|---|
| 🔗 **Image Extraction** | Paste source URLs → tool downloads images and uses YOLOv8 to detect and crop the most important panels automatically |
| 🧹 **Text Removal** | EasyOCR detects text → LaMa AI inpainting removes them cleanly for use in video |
| 🧠 **Story Intelligence (Call 1)** | Vision AI reads each panel image and generates a full structured JSON breakdown — characters, dialogue, scene events |
| ✍️ **Script Writing (Call 2)** | Text AI reads the story JSON and writes a professional YouTube voiceover narration script |
| 🔍 **Manual Review** | Built-in review screen lets you inspect, reorder, merge, or delete extracted panels before script generation |
| 🗣️ **Voiceover (TTS)** | Microsoft Edge TTS generates MP3 audio from the script — free, local, no API key needed |
| 🧩 **CapCut Export** | Generates a real, openable editable draft — images synced to audio timing, 100% editable before you export |
| 📚 **Mega Merge** | Combines scripts from multiple batches into one seamless long-form narration with AI-written transitions |
| 💸 **Cost Tracking** | Every run logs estimated API spend per episode (Call 1 + Call 2) |
| 🖥️ **Desktop GUI** | Full Tkinter desktop app — runs entirely on your machine, no cloud dependency, API keys never leave your PC |
| ⚙️ **GPU Acceleration** | Automatically uses NVIDIA GPU (CUDA) for YOLOv8, EasyOCR, and LaMa if available — falls back to CPU |

<br>

## 🔧 How It Works

```
Source URL(s)
    ↓
Image Downloader  (core/downloader.py + core/series_scraper.py)
    ↓
AI Panel Processor  (YOLOv8 crop + EasyOCR + LaMa inpainting)  (core/processor.py)
    ↓
[Manual Review — reorder / merge / delete panels]  (ui/review_view.py)
    ↓
Story Intelligence  ← Call 1: Vision AI via OpenRouter  (script_tool.py)
    ↓ story_intel.json
Script Writer  ← Call 2: Text AI via OpenRouter  (script_tool.py)
    ↓ script.txt
[Optional: Mega Merge — combine multiple batches]
    ↓ merged_script.txt
Edge TTS Voiceover  (core/audio_generator.py)
    ↓ voiceover MP3s
Project Exporter  (core/exporter.py)
    ↓
Editable Draft
```

<br>

## 🚀 Quick Start

**Step 1 — Run Setup** *(first time only)*
```
Double-click: setup_app.bat
```
Installs Python venv, PyTorch with CUDA support, and all dependencies automatically.

**Step 2 — Launch**
```
Double-click: run_app.bat
```


## 📁 Project Structure

```
yt-content-automation/
├── main.py                    # App entry point (Tkinter desktop GUI)
├── script_tool.py             # Core AI engine (Call 1, Call 2, Mega Merge)
├── setup_app.bat              # First-time setup (run once)
├── run_app.bat                # Launch the tool
├── requirements.txt           # Python dependencies
├── prompts.json               # Editable AI prompts (Call 1 + Call 2 + Merge)
├── config.json                # Output folder name settings
├── .env                       # Your API keys (never commit this)
├── core/
│   ├── downloader.py          # Image downloader from source URLs
│   ├── series_scraper.py      # Series/batch URL handler
│   ├── processor.py           # YOLOv8 panel crop + EasyOCR + LaMa inpainting
│   ├── exporter.py            # draft project builder + audio sync
│   ├── audio_generator.py     # Edge TTS voiceover generator
│   ├── project_session.py     # Per-batch session manager
│   └── config_manager.py      # Config loader
├── ui/
│   ├── main_window.py         # Main dashboard window
│   ├── processing_view.py     # Live processing dashboard
│   ├── review_view.py         # Manual panel review screen
│   ├── script_dashboard.py    # Script Tool GUI (Call 1/2/Merge + cost tracker)
│   ├── prompt_editor.py       # Prompt editor UI
│   └── crop_window.py         # Manual crop helper
└── projects/                  # All generated output (gitignored)
```

<br>

## 🗺️ Features Status

- [x] Image extraction from source URLs
- [x] YOLOv8 panel detection and cropping
- [x] EasyOCR text extraction for AI context
- [x] LaMa inpainting — clean text removal from panels
- [x] Manual review screen (reorder / merge / delete panels)
- [x] Genre-adaptive script generation via OpenRouter (Call 1 + Call 2)
- [x] Editable AI prompts via in-app Prompt Editor
- [x] Voiceover generation (Microsoft Edge TTS — free, local)
- [x] CapCut desktop project export (synced to audio timing)
- [x] Multi-episode Mega Merge into one long-form script
- [x] Per-run API cost estimation
- [x] GPU acceleration (CUDA) with automatic CPU fallback
- [x] Batch processing with retry/error handling
- [ ] Additional TTS provider support
- [ ] Background music layer

<br>

## 💸 Cost Reference

| Component | Cost |
|---|---|
| Image processing (YOLOv8 + LaMa + OCR) | Free — runs locally |
| Story Intelligence — Call 1 (Vision AI) | ~$0.01–$0.05 per 100 images (depends on model + images count) |
| Script Writing — Call 2 (Text AI) | ~$0.01–$0.03 per batch |
| Mega Merge (10 Batchs) | ~$0.05–$0.20 |
| Voiceover (Edge TTS) | Free — local |
| Editable export | Free |

A single batch process can realistically be produced for **under $0.05** in API spend on the budget tier.

> **Tip:** Use a cheaper model for Call 1 (scene reading) and a better model for Call 2 (script writing needs more creativity).

<br>

## ⚖️ Disclaimer

This project automates a creative production workflow. It does not grant rights to redistribute copyrighted source material. You are responsible for complying with the Terms of Service of any platform you use this with, and applicable copyright law in your jurisdiction. Provided for educational and personal-automation purposes.

<br>

## 📄 License

MIT — use freely, modify freely, don't hold us liable.

<br>

<div align="center">

**If this saved you hours of manual editing, a ⭐ on the repo goes a long way.**

Built by [@honeyknows](https://github.com/honeyknows)

</div>
