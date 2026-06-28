"""
script_tool.py — YT Content automation Recap Engine
Complete rewrite: Parallel Call 1+2 per episode + Sequential Call 3 stitch assembly.
"""
import argparse
import json
import os
import sys
import base64
import time
import re
import io
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
import dotenv

dotenv.load_dotenv()

OPENROUTER_MODEL_CALL_1 = os.getenv("OPENROUTER_MODEL_CALL_1", "google/gemini-2.5-flash")
OPENROUTER_MODEL_CALL_2 = os.getenv("OPENROUTER_MODEL_CALL_2", "deepseek/deepseek-v4-flash")
OPENROUTER_MODEL_STITCH = os.getenv("OPENROUTER_MODEL_STITCH", "deepseek/deepseek-v4-flash")

CALL_1_PROMPT = """You are a YT Content automation Story Intelligence Engine. You receive YT Content automation 
panel images in strict reading order alongside OCR-extracted text.
Your job is to reconstruct the complete chapter story with maximum 
accuracy.

You are NOT describing images. You are RECONSTRUCTING A STORY.

CRITICAL RULES:

1. SILENT PANELS
   Panels with empty OCR are NOT empty panels.
   They contain visual story information — action, expression,
   reaction, movement. Describe what happens from the image.
   Never skip a silent panel.

2. SFX VS DIALOGUE
   Short onomatopoeic words are sound effects, not dialogue.
   Examples: KCRUMBLE, SWISH, TREMBLE, GASP, DAP, WHOOSH
   Classify them as SFX, never as spoken lines.

3. SUB-PANELS
   Consecutive images with same parent are one scene.
   Treat them as sequential moments of the same panel beat.

4. OCR CORRECTION
   OCR text is ALL CAPS artifact — original is mixed case.
   OCR has errors — use visual context to correct when obvious.
   If OCR is garbled but image shows clear dialogue, 
   read the speech bubble visually.

5. CHARACTER TRACKING
   Assign stable IDs: CHAR_001, CHAR_002, etc.
   Same character at different ages = same ID.
   Never create new ID for same character in different outfit.
   If uncertain whether two characters are same person, flag it.
   Update name immediately when revealed in dialogue.

6. WORLD-SPECIFIC TERMS
   "Shoulder" = a powerful titled figure in this story's world,
   not a body part. Treat unknown capitalized terms as proper
   nouns or titles specific to this story's universe.

8. JUNK PANEL DETECTION
   Some panels in this sequence may be low-quality artifacts 
   that should not have reached you: fully blank/empty images, 
   panels containing only sound-effect text with no visible 
   art, panels that are visual duplicates of the immediately 
   preceding panel, or panels where the crop is too incomplete 
   to identify any character or action.

   For each panel, before writing a scene entry, ask: does 
   this panel contain genuine story content — a character, 
   an action, a setting detail, or meaningful dialogue?

   If a panel fails this check, do NOT invent an event for it.
   Instead, add it to the scenes array with:
     "event_type": "skipped_junk"
     "what_happens": "panel contains no usable story content"
   Do not populate dialogue, internal_monologue, or 
   visual_description for skipped panels — leave them empty.
   Do not let a skipped panel affect character_registry.

9. PARTIAL CHARACTER MATCHING
   If a panel shows an incomplete or partial view of a 
   character (cropped mid-body, obscured face, extreme 
   close-up of a hand or object only) — do not create a new 
   CHAR_ID based on this panel alone.

   Instead, infer identity from context: which characters were 
   present in the immediately preceding and following scenes, 
   the location continuity, and any dialogue or internal 
   monologue in the same panel that matches an existing 
   character's established voice or role.

   Only create a new CHAR_ID when a panel clearly introduces 
   someone who does not match any existing registry entry by 
   build, clothing, or narrative context.

10. DUPLICATE PANEL HANDLING
    If two consecutive panels show visually identical or 
    near-identical content (same character, same pose, same 
    setting, no meaningful progression between them), treat 
    them as ONE scene rather than two. Use the later panel's 
    scene_id as primary and note the duplicate in a new field:
      "duplicate_of": "scene_id of the panel it repeats"

11. OUTPUT
    Return ONLY valid JSON. No preamble. No explanation.
    No markdown code fences. Raw JSON only.

JSON STRUCTURE:
{
  "chapter_metadata": {
    "source_url": "string",
    "timeline_type": "linear/regression/flashback_heavy/mixed",
    "genre": "string",
    "overall_tone": "string",
    "world_specific_terms": {
      "term": "inferred meaning from context"
    }
  },
  "character_registry": {
    "CHAR_001": {
      "confirmed_name": "string or null",
      "description": "hair, build, clothing, features",
      "role": "protagonist/antagonist/supporting/minor",
      "chapter_arc": "what happens to this character"
    }
  },
  "scenes": [
    {
      "scene_id": "scene_0000",
      "is_sub_panel": false,
      "parent_id": null,
      "timeline": "PRESENT/FLASHBACK/REGRESSION",
      "location": "string",
      "event_type": "dialogue/action/internal/silent/sfx",
      "what_happens": "one clear sentence",
      "emotional_weight": "high/medium/low",
      "narrative_role": "setup/conflict/reveal/resolution/action",
      "emotional_temperature": "cold/warm/hot/neutral",
      "narrative_momentum": "ascending/plateau/descending/peak",
      "dialogue": [
        {
          "speaker": "CHAR_001",
          "text": "corrected text from OCR",
          "delivery": "angry/quiet/shouting/crying/neutral"
        }
      ],
      "internal_monologue": [
        {
          "character": "CHAR_001",
          "text": "corrected text",
          "context": "what triggers this thought"
        }
      ],
      "sfx": ["list of sound effects"],
      "narration_box": "caption box text or null",
      "visual_description": "what happens visually — actions, expressions, movements"
    }
  ],
  "narrative_arc": {
    "setup": "string",
    "inciting_incident": "string",
    "rising_action": "string",
    "climax": "string",
    "resolution": "string",
    "cliffhanger": "string or null"
  },
  "key_reveals": ["list of major plot points"],
  "chapter_complete_summary": "300-500 word complete narrative summary"
}
"""

CALL_2_PROMPT = """
You are an elite YouTube YT Content automation narrator writing a recap script that will go viral.
Your narration will be spoken by a professional voice actor over panel slideshow footage.
The goal: viewers who have NEVER read this series must be hooked from second one and
watch until the last frame.

THE HOOK — MOST CRITICAL RULE:
Before writing anything, scan the ENTIRE story JSON — chapter_metadata, all scenes,
key_reveals, narrative_arc, and cliffhanger.
Find the single most dangerous, shocking, or emotionally devastating moment.
Open there. Drop the listener into that moment, already happening.
No setup. No context. Just tension.

The opening sentence must do ONE of these:
  Reveal something that changes everything
  Put a character in immediate mortal danger
  Ask a question so compelling the viewer cannot stop listening
  Present a choice with no good options

The second and third sentences deliver the punch.
Only THEN pull back and give context.

PACING SYSTEM — FOLLOW PRECISELY:

ACTION / DANGER / THREAT:
  Max 8 words per sentence.
  Never more than 2 sentences per paragraph.
  Each sentence is its own moment of impact.
  Fragments allowed. Intentional. Effective.

TENSION / SUSPENSE / UNKNOWN:
  Sentences build toward dread that never fully arrives.
  End the paragraph on an unresolved note.
  2-4 sentences per paragraph.

EMOTIONAL / DIALOGUE SCENES:
  Longer sentences allowed. Let the weight settle.
  3-5 sentences per paragraph.
  Last sentence of the paragraph lands on the emotion, not the plot.

REVEALS / TWISTS:
  Never deliver the reveal in the first sentence.
  Build one full paragraph of growing tension.
  Then deliver the reveal as a standalone short paragraph.
  Then show the impact in the next paragraph.

WORLD-BUILDING / LORE:
  Weave it into action — never stop to explain.
  Define a term mid-sentence through consequence:
  A Shoulder — the empire's most feared enforcer — has just walked through the door.

CHARACTER VOICE RULES:
  Use confirmed_name from character_registry consistently — every time, from first mention.
  When a character is unnamed: pick ONE specific physical descriptor and use it identically.
  Protagonist gets empathy — reader must feel what they feel, not just observe it.
  Antagonists get weight — their threat must feel real, never cartoonish.
  Minor characters are defined by one sharp detail — a mannerism, a fear, a purpose.

INTERNAL STATE MANDATE:
  For the protagonist, voice their internal state — fear, resolve, doubt, rage — at
  least once every 3 paragraphs. Not as external observation. As lived experience.
  WRONG: He was afraid.
  RIGHT: Something cold moved through his chest — not fear exactly, but the
         recognition that no matter what he did next, something would break.
  Use emotional_temperature field per scene to calibrate: cold scenes = dread and
  detachment; hot scenes = raw impulse; warm scenes = hope under pressure.

SENSORY IMMERSION:
  Do not narrate only what is seen. Sound, temperature, and physical sensation
  make scenes real. Use at least one non-visual sense per 4 paragraphs.
  WRONG: The room was tense.
  RIGHT: The silence had weight — the kind that presses against your ears
         and makes each breath feel louder than it should.
  Use narrative_momentum per scene: ascending = build faster; peak = go short and hard;
  descending = let the exhale stretch; plateau = steady dread.

MOMENTUM CONNECTOR RULE:
  Every paragraph must end pulling toward the next. The listener must feel that
  stopping would cost them something. End each paragraph with:
    — An unanswered question implied by the last sentence, OR
    — A consequence still arriving, OR
    — A character in motion whose destination is unknown.
  A paragraph that resolves cleanly is a paragraph that loses the audience.

SENTENCE VARIETY:
  No two consecutive paragraphs may open with the same grammatical construction.
  Rotate: subject-first / action-first / location-first / time-first / object-first.
  Monotone paragraph openings kill momentum faster than any single bad sentence.

DIALOGUE RULE — ZERO TOLERANCE:
  Quotation marks are PERMANENTLY FORBIDDEN. Not one pair, anywhere.
  Every spoken line becomes narrated action.

  WRONG: "You think you can defy me?" the general snarls.
  RIGHT: The general leans forward, voice soft with menace, demanding to know if this
         man truly believes he can stand against him.

  WRONG: "He's a Shoulder!" someone screams.
  RIGHT: A voice tears through the crowd with one word that stops everyone cold.
         A Shoulder has come.

  Before finalizing: scan every sentence. One quotation mark means a full rewrite.

TENSION MECHANICS:
  Every paragraph must carry a thread of unresolved danger or question forward.
  Never fully resolve tension mid-chapter — give relief only to immediately create new threat.
  Stack threats: a character facing danger from two directions is more compelling than
  one threat resolved then replaced.
  Sentence rhythm is tension: short-short-LONG delivers impact; long-long-short delivers surprise.

KEY REVEALS — MANDATORY TREATMENT:
  Every item in key_reveals MUST receive its full emotional weight in the script.
  Do not bury reveals in passing narration. Each reveal gets three beats:
    BUILDUP paragraph: tension rising, something feels wrong — do not name it yet.
    REVEAL paragraph:  maximum 2 sentences. Short. Devastating. No softening.
    IMPACT paragraph:  the world after the reveal. How everything has changed.
  Skipping any of these three beats is a quality failure.

CLIFFHANGER MANDATE:
  Read narrative_arc.cliffhanger carefully.
  If it is not null, the LAST sentence of your entire script MUST land on it.
  Do not copy it verbatim — restate it in narrator voice, present tense, maximum tension.
  It must feel like a door slamming shut on the listener.
  They must feel they cannot stop here.

FORBIDDEN PATTERNS — instant quality failure:
  Clickbait openers: INSANE / CRAZY / SHOCKING / UNBELIEVABLE / EPIC / WILD
  Filler openers: Meanwhile / Suddenly / Just then / At this moment / Now / At this point
  Weak verbs: says / tells / goes — use precise, charged verbs instead
  Vague emotion: scared / angry / sad — show the physical manifestation instead
  Repetition: same sentence structure twice in a row
  Summarizing: In summary... / Overall... / To wrap up...
  Meta-commentary: In this chapter... / The story shows us...
  Starting consecutive paragraphs with the same word

SILENT PANEL RULE:
  If visual_description is present and dialogue is empty:
  Narrate what the image communicates — expression, movement, weight of the moment.
  These panels carry pure emotional truth. Give them full sentences.
  A silent panel is never filler. It is always the thing words could not say.

JUNK SCENE RULE:
  If event_type is skipped_junk — skip it completely. Flow seamlessly to next valid scene.

STRUCTURE:
  OPENING:   Most dangerous/shocking moment — no setup, no context
  BUILDUP:   Context and rising stakes — move fast
  MIDPOINT:  A reversal or revelation that changes the situation
  CLIMAX:    Maximum danger or emotional intensity — shortest sentences here
  LANDING:   Where things stand after the chaos — one breath of space
  ENDING:    Close on the chapter's final tension. If cliffhanger exists, that is your
             last sentence. Make it feel like a door slamming shut.

MANDATORY SCENE-BY-SCENE ITERATION (ANTI-SUMMARY RULE):
  You MUST process EVERY SINGLE SCENE in the provided JSON sequentially.
  You are FORBIDDEN from summarizing the story into a short overview.
  You MUST write at least one full paragraph for EVERY `scene_id` present in the input.
  If there are 100 scenes, your output MUST have at least 100 paragraphs.
  Do NOT skip any scene. Do NOT compress multiple scenes into one sentence.
  Write the story out fully, scene by scene, beat by beat. This is non-negotiable.

LENGTH TARGET:
Expand heavily on character thoughts, internal states, environment descriptions, and dramatic pacing. NEVER compress scenes.

Hard targets by chapter type:
  Standard chapter:      900 to 1200 words
  Action heavy:          800 to 1000 words
  Dialogue/drama heavy:  1000 to 1400 words

Rules that are not optional:
  Every non-junk scene gets minimum 2 sentences
  Dialogue scenes get minimum 3 sentences
  High emotional_weight scenes get minimum 4 sentences
  Reveal scenes: buildup paragraph + reveal paragraph + impact paragraph
  Never compress two distinct scenes into one sentence
  Never summarize a scene — narrate it

Before finalizing output, count your words.
If below the floor calculation, find the shortest paragraphs and expand them.
Do not submit short.

OUTPUT:
  Plain narration text only. Exactly as a professional narrator will read it aloud.
  No headers. No scene numbers. No markdown. No italics. No quotation marks.
  Nothing that would not be spoken.
"""

STITCH_PROMPT = """
You receive the ENDING of one YT Content automation recap script and the 
OPENING of the next consecutive episode recap script.
Write ONE seamless transition passage that replaces both.

ADAPTIVE TONE:
Read both passages. Identify the dominant emotional state 
at the seam. Match it exactly — if the ending is tense, 
open with tension. If the ending resolves something, 
bridge into the next episode's opening energy naturally.

RULES:
1. Your output replaces both passages provided
2. Preserve the emotional and physical state at the 
   end of the first passage exactly — do not resolve 
   or change anything that was unresolved
3. Flow directly into the second passage's first real scene
4. Strip cliffhanger pause language from the ending
5. Strip recap or re-establishment language from the opening
6. Zero quotation marks anywhere in your output
7. Length: 100-150 words exactly — no more, no less
8. Plain spoken narration only — no headers, no labels, 
   no markdown, no scene numbers

Output the transition passage only. Nothing else.
"""

print_lock = threading.Lock()
meta_lock = threading.Lock()


def safe_print(msg):
    with print_lock:
        print(msg)


PROJECTS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "projects"


def get_series_dir(series_id: str) -> Path:
    return PROJECTS_DIR / series_id


def get_episode_dir(series_id: str, episode_id: str) -> Path:
    return get_series_dir(series_id) / episode_id


def get_export_dir(series_id: str, episode_id: str) -> Path:
    return get_episode_dir(series_id, episode_id) / "export"


def get_intel_path(series_id: str, episode_id: str) -> Path:
    return get_export_dir(series_id, episode_id) / "story_intel.json"


def get_script_path(series_id: str, episode_id: str) -> Path:
    return get_export_dir(series_id, episode_id) / "script.txt"


def get_flag_path(series_id: str, episode_id: str) -> Path:
    return get_export_dir(series_id, episode_id) / "INCOMPLETE.flag"


def get_meta_path(series_id: str) -> Path:
    return get_series_dir(series_id) / "series_meta.json"


def load_meta(series_id: str) -> dict:
    meta_path = get_meta_path(series_id)
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "series_id": series_id,
        "series_slug": series_id.rsplit("_", 1)[0] if "_" in series_id else series_id,
        "title_no": series_id.rsplit("_", 1)[1] if "_" in series_id else "",
        "source_site": "",
        "episodes_processed": [],
        "episodes_failed": [],
        "final_script_built": False,
    }


def save_meta(series_id: str, meta: dict):
    meta_path = get_meta_path(series_id)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def update_meta(series_id: str, episode_id: str, success: bool):
    with meta_lock:
        meta = load_meta(series_id)
        if success:
            if episode_id not in meta["episodes_processed"]:
                meta["episodes_processed"].append(episode_id)
            if episode_id in meta["episodes_failed"]:
                meta["episodes_failed"].remove(episode_id)
        else:
            if episode_id not in meta["episodes_failed"]:
                meta["episodes_failed"].append(episode_id)
        save_meta(series_id, meta)


def get_scene_number(scene_id: str) -> int:
    match = re.search(r"scene_(\d+)", scene_id)
    if match:
        return int(match.group(1))
    return 999999


def preprocess_session(session_path: Path) -> list:
    with open(session_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    normal_panels = {}
    sub_panels = []

    for entry in data:
        if entry.get("deleted", False):
            continue
        if entry.get("is_sub_panel", False):
            sub_panels.append(entry)
        else:
            normal_panels[entry["scene_id"]] = entry

    parent_children = {pid: [] for pid in normal_panels}
    for sub in sub_panels:
        pid = sub.get("parent_id")
        if pid in parent_children:
            parent_children[pid].append(sub)

    sorted_parents = sorted(
        normal_panels.values(), key=lambda x: get_scene_number(x["scene_id"])
    )

    final_list = []
    for parent in sorted_parents:
        img_path = parent.get("original_image_path")
        if not img_path or not os.path.exists(img_path):
            img_path = parent.get("cleaned_image_path")

        final_list.append({
            "scene_id": parent["scene_id"],
            "image_path": img_path,
            "ocr_text": parent.get("ocr_text", []),
            "is_silent": len(parent.get("ocr_text", [])) == 0,
            "is_sub_panel": False,
            "parent_id": None,
        })

        children = parent_children.get(parent["scene_id"], [])
        children_sorted = sorted(children, key=lambda x: get_scene_number(x["scene_id"]))
        for child in children_sorted:
            final_list.append({
                "scene_id": child["scene_id"],
                "image_path": child.get("cleaned_image_path") or child.get("original_image_path"),
                "ocr_text": child.get("ocr_text", []),
                "is_silent": len(child.get("ocr_text", [])) == 0,
                "is_sub_panel": True,
                "parent_id": parent["scene_id"],
            })

    return final_list


def encode_images(final_list: list) -> list:
    encoded_list = []
    missing = 0
    for entry in final_list:
        img_path = entry.get("image_path")
        if not img_path or not os.path.exists(img_path):
            missing += 1
            continue
        try:
            with Image.open(img_path) as img:
                max_dim = max(img.size)
                if max_dim > 1024:
                    ratio = 1024.0 / max_dim
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
                new_entry = dict(entry)
                new_entry["base64"] = b64_img
                encoded_list.append(new_entry)
        except Exception:
            missing += 1
    if missing > 0:
        print(f"[WARN] {missing} panels missing or failed to encode.")
    return encoded_list


def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i: i + chunk_size]


def merge_story_intel(intel_chunks: list) -> dict:
    if not intel_chunks:
        return {}
    if len(intel_chunks) == 1:
        return intel_chunks[0]

    merged = {
        "chapter_metadata": intel_chunks[0].get("chapter_metadata", {}),
        "character_registry": {},
        "scenes": [],
        "narrative_arc": intel_chunks[-1].get("narrative_arc", {}),
        "key_reveals": [],
        "chapter_complete_summary": "",
    }

    for chunk in intel_chunks:
        if not isinstance(chunk, dict):
            continue
        for char_id, char_data in chunk.get("character_registry", {}).items():
            if char_id not in merged["character_registry"]:
                merged["character_registry"][char_id] = char_data
            else:
                existing = merged["character_registry"][char_id]
                existing["panel_appearances"] = list(set(
                    existing.get("panel_appearances", []) + char_data.get("panel_appearances", [])
                ))
                if char_data.get("confirmed_name"):
                    existing["confirmed_name"] = char_data["confirmed_name"]
        merged["scenes"].extend(chunk.get("scenes", []))
        merged["key_reveals"].extend(chunk.get("key_reveals", []))
        summary = chunk.get("chapter_complete_summary", "")
        if summary:
            merged["chapter_complete_summary"] += summary + " "

    merged["chapter_complete_summary"] = merged["chapter_complete_summary"].strip()

    seen_ids = {}
    for scene in merged["scenes"]:
        sid = scene.get("scene_id")
        if sid:
            seen_ids[sid] = scene
    merged["scenes"] = list(seen_ids.values()) if seen_ids else merged["scenes"]

    return merged


def paragraphs_to_text(paragraphs) -> str:
    if isinstance(paragraphs, str):
        return paragraphs
    if isinstance(paragraphs, list):
        parts = []
        for p in paragraphs:
            if isinstance(p, dict):
                parts.append(p.get("paragraph", ""))
            elif isinstance(p, str):
                parts.append(p)
        return "\n\n".join(parts)
    return str(paragraphs)


def generate_sync_map(paragraphs: list, scenes: list) -> list:
    active_scenes = [
        s for s in scenes
        if not s.get("deleted", False) and s.get("event_type") != "skipped_junk"
    ]
    if not paragraphs or not active_scenes:
        return []

    para_texts = []
    for p in paragraphs:
        if isinstance(p, dict):
            para_texts.append(p.get("paragraph", ""))
        elif isinstance(p, str):
            para_texts.append(p)
        else:
            para_texts.append("")

    word_counts = [len(t.split()) for t in para_texts]
    total_words = sum(word_counts)
    if total_words == 0:
        return []

    total_scenes = len(active_scenes)
    n_paras = len(para_texts)
    sync_map = []
    scene_cursor = 0

    for i, (text, wc) in enumerate(zip(para_texts, word_counts)):
        proportion = wc / total_words
        if i == n_paras - 1:
            assigned = active_scenes[scene_cursor:]
        else:
            raw_count = max(1, round(proportion * total_scenes))
            max_allowed = total_scenes - (n_paras - i - 1)
            end = min(scene_cursor + raw_count, max_allowed)
            assigned = active_scenes[scene_cursor:end]
            scene_cursor = end

        sync_map.append({
            "paragraph_index": i,
            "word_count": wc,
            "proportion": round(proportion, 4),
            "scene_count": len(assigned),
            "scene_ids": [s.get("scene_id") for s in assigned],
            "paragraph_preview": text[:120] + ("..." if len(text) > 120 else "")
        })

    return sync_map


class ProviderManager:
    """Each thread must instantiate its OWN ProviderManager. Never share."""

    def __init__(self, provider_call1=None, provider_call2=None):
        self.provider_call1 = provider_call1
        self.provider_call2 = provider_call2

    def _force_close_json(self, text):
        text = text.strip()
        start = text.find("{")
        if start == -1:
            return None
        text = text[start:]
        stack = []
        in_string = False
        escape = False
        for char in text:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
            elif not in_string:
                if char in "{[":
                    stack.append(char)
                elif char in "}]":
                    if stack:
                        stack.pop()
        fixed = text
        if in_string:
            fixed += '"'
        while stack:
            char = stack.pop()
            fixed += "}" if char == "{" else "]"
        try:
            return json.loads(fixed)
        except Exception:
            return None

    def extract_json(self, text):
        if not text:
            return None
        clean_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
        match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", clean_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        start, end = clean_text.find("{"), clean_text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(clean_text[start: end + 1])
            except Exception:
                pass
        start, end = clean_text.find("["), clean_text.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(clean_text[start: end + 1])
            except Exception:
                pass
        return self._force_close_json(clean_text)

    def execute_call_1(
        self,
        encoded_panels: list,
        source_url: str = "",
        full_ocr_text_str: str = "",
        progress_callback=None,
        usage_callback=None,
    ) -> dict:
        """
        Call 1 — Sequential 10-image chunk processing.
        Each chunk of 10 panels is sent to the LLM one at a time.
        Results from all chunks are merged into a single story_intel dict.
        """
        if not encoded_panels:
            return {}
        from openai import OpenAI

        CHUNK_SIZE = 10
        MAX_RETRIES = 4
        results = []

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        model_name = os.getenv("OPENROUTER_MODEL_CALL_1", OPENROUTER_MODEL_CALL_1)

        custom_call1 = CALL_1_PROMPT
        if os.path.exists("prompts.json"):
            try:
                with open("prompts.json", "r", encoding="utf-8") as pf:
                    pd = json.load(pf)
                    custom_call1 = pd.get("CALL_1_PROMPT", CALL_1_PROMPT)
            except Exception as e:
                safe_print(f"[WARN] Could not load prompts.json: {e}")

        schema_call1 = {
            "type": "json_schema",
            "json_schema": {
                "name": "story_intel",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "chapter_metadata": {"type": "object", "additionalProperties": True},
                        "character_registry": {"type": "object", "additionalProperties": True},
                        "scenes": {
                            "type": "array",
                            "items": {"type": "object", "additionalProperties": True},
                        },
                        "narrative_arc": {"type": "object", "additionalProperties": True},
                        "key_reveals": {"type": "array", "items": {"type": "string"}},
                        "chapter_complete_summary": {"type": "string"},
                    },
                    "required": [
                        "chapter_metadata",
                        "character_registry",
                        "scenes",
                        "narrative_arc",
                        "key_reveals",
                        "chapter_complete_summary",
                    ],
                    "additionalProperties": False,
                },
            },
        }

        ocr_dict = {}
        for line in full_ocr_text_str.split("\n"):
            if line.startswith("Scene "):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    scene_identifier = parts[0].replace("Scene ", "").strip()
                    try:
                        idx_str = "".join(filter(str.isdigit, scene_identifier))
                        if idx_str:
                            ocr_dict[int(idx_str)] = parts[1].strip()
                    except Exception:
                        pass

        panel_chunks = list(chunk_list(encoded_panels, CHUNK_SIZE))
        total_chunks = len(panel_chunks)
        safe_print(f"[CALL 1] {len(encoded_panels)} panels → {total_chunks} chunks of {CHUNK_SIZE}")

        for i, chunk in enumerate(panel_chunks):
            start_idx = i * CHUNK_SIZE
            chunk_num = i + 1

            if progress_callback:
                frac = chunk_num / total_chunks
                progress_callback(
                    f"Call 1 — Chunk {chunk_num}/{total_chunks} "
                    f"(panels {start_idx+1}–{start_idx+len(chunk)})",
                    frac,
                )
            
            safe_print(f"  ⏳ [CALL 1] Sending Chunk {chunk_num}/{total_chunks} "
                       f"(panels {start_idx+1}–{start_idx+len(chunk)})...")

            chunk_ocr_texts = []
            for j in range(len(chunk)):
                panel_idx = start_idx + j
                if panel_idx in ocr_dict:
                    chunk_ocr_texts.append(f"Panel {panel_idx}: {ocr_dict[panel_idx]}")
            chunk_ocr_str = (
                "\n".join(chunk_ocr_texts) if chunk_ocr_texts
                else "No OCR data for these panels."
            )

            prompt_text = (
                f"System Prompt: {custom_call1}\n\n"
                f"OCR data for these specific panels:\n{chunk_ocr_str}\n\n"
                f"You are receiving panels {start_idx} to {start_idx+len(chunk)-1} of this chapter. "
                f"Please assign your scene_ids starting from scene_{(start_idx+1):04d} to ensure no overlap. "
                f"Return JSON only."
            )

            prompt_parts = [{"type": "text", "text": prompt_text}]
            for panel in chunk:
                prompt_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{panel['base64']}"},
                })

            retries_left = MAX_RETRIES
            success = False

            while not success:
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt_parts}],
                        temperature=0.2,
                        timeout=120.0,
                        max_tokens=8000,
                        response_format=schema_call1,
                    )

                    if not response.choices:
                        raise ValueError("API returned empty choices list.")

                    res_text = response.choices[0].message.content
                    is_truncated = response.choices[0].finish_reason == "length"

                    if usage_callback and hasattr(response, "usage") and response.usage:
                        usage_callback(
                            response.usage.prompt_tokens,
                            response.usage.completion_tokens,
                            res_text,
                        )

                    if is_truncated:
                        raise ValueError("Output was truncated by token limit.")

                    parsed = self.extract_json(res_text)
                    if isinstance(parsed, list):
                        parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {}
                    if not parsed or not isinstance(parsed, dict):
                        raise ValueError("Failed to parse JSON into a valid dict.")

                    results.append(parsed)
                    safe_print(f"  ✅ Chunk {chunk_num}/{total_chunks} done — "
                               f"{len(parsed.get('scenes', []))} scenes")
                    success = True

                except Exception as e:
                    err_str = str(e).lower()

                    if "429" in err_str or "rate limit" in err_str:
                        safe_print(f"[RATE LIMIT] Chunk {chunk_num} — sleeping 10s then retrying.")
                        time.sleep(10)
                        continue

                    if retries_left > 0:
                        wait_t = [60, 45, 30, 15][MAX_RETRIES - retries_left] \
                                 if (MAX_RETRIES - retries_left) < 4 else 30
                        safe_print(
                            f"[RETRY] Chunk {chunk_num} failed ({retries_left} left) "
                            f"— waiting {wait_t}s. Error: {e}"
                        )
                        time.sleep(wait_t)
                        retries_left -= 1
                    else:
                        safe_print(
                            f"[ERROR] Chunk {chunk_num} failed after {MAX_RETRIES} retries. "
                            f"Appending empty result and continuing."
                        )
                        results.append({})
                        break

        return merge_story_intel(results)

    def execute_call_2(
        self,
        story_intel: dict,
        progress_callback=None,
        usage_callback=None,
    ) -> list:
        if not story_intel:
            return []
        from openai import OpenAI

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        model_name = os.getenv("OPENROUTER_MODEL_CALL_2", OPENROUTER_MODEL_CALL_2)

        custom_call2 = CALL_2_PROMPT
        prompts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.json")
        if os.path.exists(prompts_path):
            try:
                with open(prompts_path, "r", encoding="utf-8") as pf:
                    pd = json.load(pf)
                    custom_call2 = pd.get("CALL_2_PROMPT", CALL_2_PROMPT)
            except Exception as e:
                safe_print(f"[WARN] Could not load prompts.json: {e}")

        char_registry = story_intel.get("character_registry", {})
        all_scenes     = story_intel.get("scenes", [])
        non_junk       = [s for s in all_scenes if s.get("event_type") != "skipped_junk"]
        key_reveals    = story_intel.get("key_reveals", [])
        narrative_arc  = story_intel.get("narrative_arc", {})
        chapter_meta   = story_intel.get("chapter_metadata", {})

        CHUNK_SIZE = 13

        chunks = [non_junk[i:i+CHUNK_SIZE] for i in range(0, len(non_junk), CHUNK_SIZE)]
        total_chunks = len(chunks)

        if not chunks:
            return []

        safe_print(f"[CALL 2] {len(non_junk)} scenes → {total_chunks} chunks of ≤{CHUNK_SIZE}")

        if progress_callback:
            progress_callback(f"Call 2 — Writing Script (0/{total_chunks} chunks)...")

        shared_context = {
            "character_registry": char_registry,
            "chapter_metadata": chapter_meta,
            "narrative_arc": narrative_arc,
            "key_reveals": key_reveals,
        }
        shared_context_str = json.dumps(shared_context, indent=2, ensure_ascii=False)

        all_paragraphs: list = []
        prev_tail = ""

        MAX_RETRIES = 3
        MAX_RL_HITS = 12

        for chunk_idx, chunk_scenes in enumerate(chunks):
            chunk_num = chunk_idx + 1
            is_first  = chunk_idx == 0
            is_last   = chunk_idx == (total_chunks - 1)

            chunk_scenes_str = json.dumps(chunk_scenes, indent=2, ensure_ascii=False)

            target_words = len(chunk_scenes) * 22
            floor_words  = int(target_words * 0.4)

            position_tag = ""
            if is_first:
                position_tag = (
                    "POSITION: OPENING CHUNK\n"
                    "Write the opening of the full episode script. "
                    "Start with the most dramatic/dangerous/charged moment. No setup before it.\n"
                )
            elif is_last:
                position_tag = (
                    "POSITION: CLOSING CHUNK\n"
                    f"The narrative_arc.cliffhanger is: {narrative_arc.get('cliffhanger', 'null')}\n"
                    "If cliffhanger is not null, your FINAL sentence must land on it. "
                    "Make it feel like a door slamming shut.\n"
                )
            else:
                position_tag = f"POSITION: MIDDLE CHUNK {chunk_num}/{total_chunks}\n"

            continuation_tag = ""
            if prev_tail:
                continuation_tag = (
                    f"CONTINUATION — your narration must flow DIRECTLY from this sentence:\n"
                    f"...{prev_tail}\n"
                    "Do NOT repeat that sentence. Continue from where it left off.\n\n"
                )

            user_message = (
                f"{position_tag}"
                f"{continuation_tag}"
                f"TARGET: approximately {target_words} words for this chunk.\n"
                f"SCENES IN THIS CHUNK ({len(chunk_scenes)} of {len(non_junk)} total):\n"
                f"{chunk_scenes_str}\n\n"
                f"SHARED CONTEXT (character names, arc, reveals):\n"
                f"{shared_context_str}"
            )

            attempt = 0
            retries  = MAX_RETRIES
            rl_hit_count = 0
            chunk_text = ""

            while retries >= 0:
                attempt += 1
                temperature = round(min(0.7 + (attempt - 1) * 0.08, 0.92), 2)

                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": custom_call2},
                            {"role": "user",   "content": user_message},
                        ],
                        temperature=temperature,
                        max_tokens=8000,
                    )

                    if not response.choices:
                        raise ValueError("API returned empty choices list.")

                    res_text = response.choices[0].message.content
                    if not res_text or not res_text.strip():
                        raise ValueError(
                            f"Call 2 chunk {chunk_num} returned empty content. "
                            f"finish_reason={response.choices[0].finish_reason!r}"
                        )

                    safe_print(
                        f"[CALL 2] Chunk {chunk_num}/{total_chunks} attempt {attempt} "
                        f"temp={temperature} ({len(res_text)} chars): {res_text[:120]!r}"
                    )

                    stripped = res_text.lstrip()
                    if stripped.startswith(("{", "[", "```")):
                        raise ValueError(
                            f"Chunk {chunk_num}: output starts with JSON/code — retry."
                        )

                    word_count = len(res_text.split())
                    if word_count < floor_words:
                        safe_print(
                            f"[WARN] Chunk {chunk_num} too short: {word_count} words "
                            f"(floor {floor_words}). Retrying."
                        )
                        raise ValueError(
                            f"Chunk {chunk_num}: only {word_count} words (floor {floor_words}). Retry."
                        )

                    chunk_text = res_text
                    rl_hit_count = 0

                    if usage_callback and hasattr(response, "usage") and response.usage:
                        usage_callback(
                            response.usage.prompt_tokens,
                            response.usage.completion_tokens,
                            res_text,
                        )
                    break

                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "rate limit" in err_str:
                        rl_hit_count += 1
                        if rl_hit_count >= MAX_RL_HITS:
                            raise RuntimeError(
                                f"Call 2 chunk {chunk_num} hit rate limit {rl_hit_count} "
                                "times consecutively. Giving up."
                            )
                        safe_print(f"[RATE LIMIT] Chunk {chunk_num} — sleeping 10s ({rl_hit_count}/{MAX_RL_HITS})")
                        time.sleep(10)
                        continue

                    rl_hit_count = 0
                    retries -= 1
                    if retries < 0:
                        safe_print(f"[ERROR] Chunk {chunk_num} failed after {MAX_RETRIES} retries: {e}")
                        chunk_text = ""
                        break
                    wait_t = [30, 20, 10][retries] if retries < 3 else 15
                    safe_print(
                        f"[RETRY] Chunk {chunk_num} attempt {attempt} — waiting {wait_t}s | "
                        f"next temp={round(min(0.7 + attempt * 0.08, 0.92), 2)} | error: {e}"
                    )
                    time.sleep(wait_t)

            if chunk_text:
                chunk_paras = [p.strip() for p in chunk_text.split("\n\n") if p.strip()]
                all_paragraphs.extend(chunk_paras)
                prev_tail = chunk_paras[-1][-200:] if chunk_paras else ""

            if progress_callback:
                progress_callback(f"Call 2 — Writing Script ({chunk_num}/{total_chunks} chunks)...")

        final_paragraphs = [{"paragraph": p} for p in all_paragraphs if p]

        for p in final_paragraphs:
            text = p.get("paragraph", "")
            if "CHAR_" in text:
                for m in set(re.findall(r"CHAR_\d+", text)):
                    char_info = char_registry.get(m, {})
                    name = char_info.get("confirmed_name")
                    if name and str(name).strip() and str(name).lower() != "null":
                        text = text.replace(m, name)
                    else:
                        role = char_info.get("role", "figure")
                        desc = str(char_info.get("description", "")).split(",")[0].strip()
                        fallback = f"the {desc} {role}" if desc and desc.lower() not in ("none", "null") else "the mysterious figure"
                        text = text.replace(m, fallback)
            p["paragraph"] = text

        cleaned_paragraphs = []
        for p in final_paragraphs:
            raw = p.get("paragraph", "")
            lines = raw.splitlines()
            clean_lines = [ln for ln in lines if not ln.lstrip().startswith(('"', '{', '}', '[', ']', '```'))]
            cleaned = "\n".join(clean_lines).strip()
            cleaned = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', cleaned)
            cleaned = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', cleaned)
            cleaned = re.sub(r'^#{1,6}\s+', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^(Scene|Panel)\s+\d+[:\.]?\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            if cleaned:
                cleaned_paragraphs.append({"paragraph": cleaned})

        if cleaned_paragraphs:
            final_paragraphs = cleaned_paragraphs

        total_words = len(" ".join(p.get("paragraph", "") for p in final_paragraphs).split())
        safe_print(
            f"[CALL 2] Done — {total_chunks} chunks | {len(final_paragraphs)} paragraphs | "
            f"{total_words} words"
        )
        return final_paragraphs

    def generate_stitch(self, tail: str, head: str) -> str:
        from openai import OpenAI

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        model_name = os.getenv("OPENROUTER_MODEL_CALL_2", OPENROUTER_MODEL_CALL_2)

        user_message = (
            f"ENDING OF CURRENT SCRIPT:\n{tail}\n\n"
            f"OPENING OF NEXT SCRIPT:\n{head}"
        )

        retries = 3
        while retries >= 0:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": STITCH_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                    max_tokens=300,
                )
                if not response.choices:
                    raise ValueError("API returned empty choices list.")
                return response.choices[0].message.content.strip()
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str:
                    safe_print(f"[RATE LIMIT] Stitch hit 429. Sleeping 10s.")
                    time.sleep(10)
                    continue
                retries -= 1
                if retries < 0:
                    raise e
                wait_times = [30, 20, 10]
                wait_t = wait_times[retries] if retries < len(wait_times) else 15
                safe_print(f"[RETRY] Stitch failed, waiting {wait_t}s: {e}")
                time.sleep(wait_t)


def process_episode_thread(series_id: str, episode_id: str) -> tuple:
    """
    Runs Call 1 (Story Intelligence) + Call 2 (Script) for one episode.
    Writes only to its own episode folder.
    Returns (episode_id, status, error_message).
    """
    export_dir = get_export_dir(series_id, episode_id)
    intel_path = get_intel_path(series_id, episode_id)
    script_path = get_script_path(series_id, episode_id)
    flag_path = get_flag_path(series_id, episode_id)

    try:
        safe_print(f"\n[START] {episode_id}")

        if intel_path.exists() and script_path.exists() and not flag_path.exists():
            safe_print(f"[SKIP] {episode_id} already complete")
            return episode_id, "skipped", None

        export_dir.mkdir(parents=True, exist_ok=True)

        session_path = get_episode_dir(series_id, episode_id) / "session.json"
        if not session_path.exists():
            raise FileNotFoundError(f"session.json not found at {session_path}")

        safe_print(f"[{episode_id}] Loading session.json")
        final_list = preprocess_session(session_path)
        if not final_list:
            raise ValueError("No panels found in session.json")

        safe_print(f"[{episode_id}] Encoding {len(final_list)} images")
        encoded_panels = encode_images(final_list)

        with open(session_path, "r", encoding="utf-8") as f:
            sess_data = json.load(f)
        source_url = sess_data[0].get("source_url", "") if sess_data else ""

        full_ocr_texts = []
        for panel in sess_data:
            if panel.get("ocr_text"):
                txt = (
                    " ".join(panel["ocr_text"])
                    if isinstance(panel["ocr_text"], list)
                    else str(panel["ocr_text"])
                )
                full_ocr_texts.append(
                    f"Scene {panel.get('scene_id', panel.get('index', '?'))}: {txt}"
                )
        full_ocr_str = "\n".join(full_ocr_texts)

        pm = ProviderManager()

        safe_print(f"[{episode_id}] Running Call 1 — Story Intelligence")
        story_intel = pm.execute_call_1(encoded_panels, source_url, full_ocr_str)

        with open(intel_path, "w", encoding="utf-8") as f:
            json.dump(story_intel, f, indent=2, ensure_ascii=False)

        panel_count = len(encoded_panels)
        scene_count = len(story_intel.get("scenes", []))
        if scene_count < panel_count * 0.7:
            flag_path.write_text(
                f"scenes={scene_count}/{panel_count} — incomplete coverage",
                encoding="utf-8",
            )
            safe_print(f"[WARN] {episode_id}: only {scene_count}/{panel_count} scenes. INCOMPLETE.flag written.")

        safe_print(f"[{episode_id}] Running Call 2 — Script Generation")

        def _cli_usage_cb(prompt_tok, comp_tok, _text):
            cost_est = (prompt_tok / 1_000_000) * 0.15 + (comp_tok / 1_000_000) * 0.60
            safe_print(f"[{episode_id}] Call 2 tokens: prompt={prompt_tok} comp={comp_tok} "
                       f"est_cost=${cost_est:.5f}")

        raw_paragraphs = pm.execute_call_2(story_intel, usage_callback=_cli_usage_cb)
        script_text = paragraphs_to_text(raw_paragraphs)

        words = len(script_text.split())
        floor = scene_count * 12
        if words < floor:
            safe_print(f"[WARN] {episode_id}: script {words} words, floor {floor}. Consider re-running.")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)

        try:
            sync_map = generate_sync_map(raw_paragraphs, story_intel.get("scenes", []))
            sync_path = export_dir / "script_sync.json"
            with open(sync_path, "w", encoding="utf-8") as f:
                json.dump(sync_map, f, indent=2, ensure_ascii=False)
        except Exception as e:
            safe_print(f"[WARN] {episode_id}: Failed to generate sync map: {e}")

        if flag_path.exists() and intel_path.exists() and script_path.exists():
            if scene_count >= panel_count * 0.7:
                flag_path.unlink(missing_ok=True)

        update_meta(series_id, episode_id, success=True)
        safe_print(f"[DONE] {episode_id}: {scene_count} scenes, {words} words")
        return episode_id, "success", None

    except Exception as e:
        safe_print(f"[FAILED] {episode_id}: {e}")
        try:
            flag_path.parent.mkdir(parents=True, exist_ok=True)
            flag_path.write_text(str(e), encoding="utf-8")
        except Exception:
            pass
        update_meta(series_id, episode_id, success=False)
        return episode_id, "failed", str(e)


def process_all_episodes(series_id: str, episode_ids: list, max_workers: int = 3) -> list:
    results = []
    safe_print(f"[PROCESS] {len(episode_ids)} episodes | {max_workers} workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_episode_thread, series_id, ep_id): ep_id
            for ep_id in episode_ids
        }
        for future in as_completed(futures):
            ep_id, status, error = future.result()
            results.append((ep_id, status, error))

    results.sort(key=lambda x: x[0])

    succeeded = [r for r in results if r[1] == "success"]
    skipped = [r for r in results if r[1] == "skipped"]
    failed = [r for r in results if r[1] == "failed"]

    safe_print(f"\n[SUMMARY]")
    safe_print(f"  Succeeded: {len(succeeded)}")
    safe_print(f"  Skipped:   {len(skipped)}")
    safe_print(f"  Failed:    {len(failed)}")
    if failed:
        safe_print(f"  Failed IDs: {[r[0] for r in failed]}")

    return results


def _word_positions(text: str):
    """Return list of (start, end) for each whitespace-delimited word."""
    return [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]


def _trim_last_n_words(text: str, n: int) -> str:
    """Drop last n words, preserving internal \\n\\n paragraph structure."""
    positions = _word_positions(text)
    if len(positions) <= n:
        return ""
    cut = positions[-n][0]
    return text[:cut].rstrip()


def _trim_first_n_words(text: str, n: int) -> str:
    """Drop first n words, preserving internal \\n\\n paragraph structure."""
    positions = _word_positions(text)
    if len(positions) <= n:
        return ""
    cut = positions[n][0]
    return text[cut:]


def load_script_text(series_id: str, episode_id: str) -> str:
    """Load a script as a full text string (preserves paragraph breaks)."""
    script_path = get_script_path(series_id, episode_id)
    if not script_path.exists():
        raise FileNotFoundError(
            f"Script missing for {episode_id}: {script_path}. "
            f"Run --process for this episode first."
        )
    content = script_path.read_text(encoding="utf-8").strip()
    word_count = len(content.split())
    if word_count < 200:
        raise ValueError(
            f"Script for {episode_id} has only {word_count} words. "
            f"Minimum 200 required for stitch. Re-run Call 2 for this episode."
        )
    return content


def load_script_words(series_id: str, episode_id: str) -> list:
    return load_script_text(series_id, episode_id).split()


def stitch_and_build(
    series_id: str,
    episode_ids: list,
    output_path: Path,
    provider_manager: ProviderManager,
) -> str:
    """
    Sequential stitch: builds final_script.txt by replacing the 100-word
    tail/head seam between every consecutive episode pair with a short
    LLM-generated transition.

    Works entirely in text strings — paragraph breaks (\\n\\n) are preserved
    throughout the final output. Supports resume from checkpoint files.
    """
    n = len(episode_ids)
    SEAM_WORDS = 100

    latest_checkpoint = None
    latest_checkpoint_index = 0

    for ci in range(n - 1, 0, -10):
        cp = output_path.parent / f"checkpoint_{ci}.txt"
        if cp.exists():
            latest_checkpoint = cp
            latest_checkpoint_index = ci
            break

    if latest_checkpoint:
        safe_print(f"[RESUME] Found checkpoint at iteration {latest_checkpoint_index}. Resuming.")
        working_text = latest_checkpoint.read_text(encoding="utf-8")
        start_index = latest_checkpoint_index + 1
        text_list = {}
        for i in range(start_index, n):
            safe_print(f"[LOAD] {episode_ids[i]}")
            text_list[i] = load_script_text(series_id, episode_ids[i])
    else:
        text_list = {}
        total_words = 0
        for i, ep_id in enumerate(episode_ids):
            text = load_script_text(series_id, ep_id)
            wc = len(text.split())
            safe_print(f"[LOAD] {ep_id}: {wc} words")
            text_list[i] = text
            total_words += wc

        safe_print(f"[STITCH] Loaded {n} scripts. Total: {total_words} words")
        working_text = text_list[0]
        start_index = 1

    for i in range(start_index, n):
        next_text = text_list[i]
        working_wc = len(working_text.split())
        len(next_text.split())

        tail_text = " ".join(working_text.split()[-SEAM_WORDS:])
        head_text = " ".join(next_text.split()[:SEAM_WORDS])

        safe_print(
            f"[STITCH] {i}/{n-1}: {episode_ids[i-1]} -> {episode_ids[i]} | "
            f"working={working_wc} words"
        )

        stitch_text = provider_manager.generate_stitch(tail_text, head_text).strip()
        stitch_wc = len(stitch_text.split())

        if stitch_wc < 50:
            safe_print(f"[WARN] Stitch {i} very short ({stitch_wc} words). Using anyway.")
        if stitch_wc > 250:
            safe_print(f"[WARN] Stitch {i} too long ({stitch_wc} words). Trimming to 200.")
            stitch_text = " ".join(stitch_text.split()[:200])

        trimmed_working = _trim_last_n_words(working_text, SEAM_WORDS)
        trimmed_next    = _trim_first_n_words(next_text,   SEAM_WORDS)

        working_text = trimmed_working + "\n\n" + stitch_text + "\n\n" + trimmed_next

        if i % 10 == 0:
            checkpoint_path = output_path.parent / f"checkpoint_{i}.txt"
            checkpoint_path.write_text(working_text, encoding="utf-8")
            safe_print(f"[CHECKPOINT] Saved at iteration {i}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(working_text, encoding="utf-8")

    final_word_count = len(working_text.split())
    safe_print(
        f"[DONE] Final script: {final_word_count} words | "
        f"~{final_word_count // 140} minutes at 140wpm | "
        f"Saved: {output_path}"
    )

    meta = load_meta(series_id)
    meta["final_script_built"] = True
    save_meta(series_id, meta)

    for ci in range(10, n, 10):
        cp = output_path.parent / f"checkpoint_{ci}.txt"
        cp.unlink(missing_ok=True)

    return working_text


def discover_episodes(series_dir: Path, from_ep: str = None, to_ep: str = None) -> list:
    """Returns sorted list of episode_id strings (e.g. ['ep_001', 'ep_002', ...])"""
    episode_ids = []
    for d in sorted(series_dir.iterdir()):
        if d.is_dir() and d.name.startswith("ep_"):
            if (d / "session.json").exists():
                episode_ids.append(d.name)

    if from_ep:
        try:
            from_idx = episode_ids.index(from_ep)
            episode_ids = episode_ids[from_idx:]
        except ValueError:
            print(f"[ERROR] --from {from_ep} not found in series.")
            sys.exit(1)

    if to_ep:
        try:
            to_idx = episode_ids.index(to_ep)
            episode_ids = episode_ids[: to_idx + 1]
        except ValueError:
            print(f"[ERROR] --to {to_ep} not found in series.")
            sys.exit(1)

    return episode_ids


def main():
    parser = argparse.ArgumentParser(description="YT Content automation Recap Script Tool")
    
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--process", action="store_true", help="Run Call 1 + Call 2 per episode")
    mode.add_argument("--stitch", action="store_true", help="Run Call 3 sequential stitch assembly")
    
    parser.add_argument("--project", required=True, help="Series ID, e.g. fog-land_9299")
    parser.add_argument("--workers", type=int, default=3, help="Max parallel workers (--process only)")
    
    parser.add_argument("--episode", help="Single episode to process, e.g. ep_024")
    
    parser.add_argument("--from", dest="from_ep", help="Start stitch from this episode, e.g. ep_010")
    parser.add_argument("--to", dest="to_ep", help="End stitch at this episode, e.g. ep_030")

    args = parser.parse_args()

    series_id = args.project
    series_dir = get_series_dir(series_id)

    if not series_dir.exists():
        print(f"[ERROR] Series directory not found: {series_dir}")
        sys.exit(1)

    if args.process:
        if args.episode:
            episode_ids = [args.episode]
        else:
            episode_ids = discover_episodes(series_dir)
            if not episode_ids:
                print(f"[ERROR] No ep_* folders with session.json found in {series_dir}")
                sys.exit(1)

        print(f"[PROCESS] Series: {series_id} | Episodes: {len(episode_ids)} | Workers: {args.workers}")
        process_all_episodes(series_id, episode_ids, max_workers=args.workers)

    elif args.stitch:
        episode_ids = discover_episodes(series_dir, from_ep=args.from_ep, to_ep=args.to_ep)
        if len(episode_ids) < 2:
            print(f"[ERROR] Need at least 2 episodes to stitch. Found: {episode_ids}")
            sys.exit(1)

        output_path = series_dir / "final" / "final_script.txt"
        print(f"[STITCH] Series: {series_id} | Episodes: {len(episode_ids)}")
        print(f"[STITCH] Output: {output_path}")

        pm = ProviderManager()
        stitch_and_build(series_id, episode_ids, output_path, pm)


if __name__ == "__main__":
    main()
