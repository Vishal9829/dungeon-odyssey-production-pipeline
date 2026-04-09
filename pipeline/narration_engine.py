"""
Enhanced Narration Engine with Tier 1 upgrades
- Smart pause timing
- Adaptive speed
- Emotion-based analysis
"""

import json
import re
import threading
from collections import deque
from typing import Dict, Optional, Tuple
import numpy as np

from pipeline.config import config

class NarrationEngine:
    """
    Generate unique, non-repetitive narrations with context awareness
    Tier 1: Smart pause timing & adaptive speed
    """
    
    def __init__(self, lore_bible_override: Optional[str] = None):
        self.narration_context = deque(maxlen=config.CONTEXT_WINDOW)
        self.lock = threading.Lock()
        self.lore_bible = lore_bible_override or self._load_lore_bible()
    
    def _load_lore_bible(self) -> str:
        """Load lore reference"""
        return """
=== DUNGEON ODYSSEY — LORE BIBLE ===

PROTAGONIST: Kim Jinwoo — Dungeon Baby, strategic genius, Naga Labyrinth owner

KEY ALLIES:
- Drakan: Powerful dragon-like warrior
- Naga Army: Main infantry force
- Hyunji: Emotional anchor (sister figure)
- Yeongho: Skilled expedition fighter

LABYRINTH LORDS (Rivals/Allies):
- Malaxus: Dwarf King (smithing + warfare)
- Hekarim: Centaur King (spear master)
- Ariane: Elf Queen (illusion magic)
- Gorintos: Swamp King
- Useo: Slime King
- Valicius: Undead King

THEMES:
1. Dungeon management & resource economy
2. Inter-labyrinth politics & alliances
3. Sacrifice & consequences
4. Loyalty bonds & betrayal
5. Power hierarchy: weakness = death

TONE: Epic, political, strategic (NOT "hero fights monsters")
"""
    
    def create_prompt(self, ocr_data: Dict, visual_context: str, 
                     scene_type: str = '') -> str:
        """
        Create comprehensive narration prompt
        """
        context_str = ""
        if self.narration_context:
            context_str = "\n=== RECENT NARRATIONS (avoid exact repetition) ===\n"
            for i, narr in enumerate(list(self.narration_context)[-5:], 1):
                context_str += f"{i}. \"{narr}\"\n"
        
        extracted = ocr_data.get('extracted_text', '')
        has_text = ocr_data.get('has_text', False)
        
        text_instruction = ""
        if has_text and extracted:
            text_instruction = f"""
EXTRACTED TEXT/DIALOGUE:
{extracted[:200]}...

Use this to contextualize your narration.
"""
        
        return f"""{self.lore_bible}

{context_str}

=== NARRATION TASK ===
Scene Type: {scene_type or 'unknown'}
Visual Context: {visual_context}

{text_instruction}

GENERATE A SHORT, PUNCHY NARRATION:
- Exactly 8-14 words
- YouTube Hook style: dramatic, compelling
- NEVER repeat previous narrations
- Stay true to Lore: epic, political, strategic

ALSO ANALYZE:
- Primary emotion (epic, dramatic, dark, emotional, tense, mysterious)
- Importance level (1-10, where 10 = story climax)
- Scene type confirmation

OUTPUT ONLY THIS JSON (no markdown):
{{
  "narration": "<8-14 words>",
  "emotion": "<emotion>",
  "importance": <1-10>,
  "confirmed_scene_type": "<scene_type>",
  "tts_speed_modifier": <0.7-1.2>,
  "color_grade_recommendation": "<color_grade_name>"
}}
"""
    
    def generate_narration(self, ocr_data: Dict, visual_context: str, 
                          scene_type: str, client, model: str) -> Optional[Dict]:
        """
        Generate narration with Tier 1 smart analysis
        Returns complete narration with timing recommendations
        """
        try:
            prompt = self.create_prompt(ocr_data, visual_context, scene_type)
            
            # Call API
            result_text = self._call_api(prompt, client, model)
            
            # Parse JSON
            result = self._parse_json(result_text)
            
            if not result:
                return None
            
            narration = result.get('narration', '').strip()
            
            # Check for repetition
            if self._is_repetitive(narration):
                narration = self._remediate(narration, scene_type)
                result['narration'] = narration
            
            # Add to context
            with self.lock:
                self.narration_context.append(narration)
            
            # TIER 1: Calculate smart pause timing
            emotion = result.get('emotion', 'neutral')
            pause_timing = self._calculate_pause_timing(
                scene_type, emotion, result.get('importance', 5)
            )
            result['tts_pause_before_ms'] = pause_timing['before_ms']
            result['tts_pause_after_ms'] = pause_timing['after_ms']
            
            # TIER 1: Adaptive TTS speed
            tts_speed = self._calculate_tts_speed(
                result.get('importance', 5),
                emotion,
                scene_type
            )
            result['tts_speed'] = tts_speed
            
            # TIER 1: Color grading recommendation
            color_grade = result.get('color_grade_recommendation', 'dramatic')
            result['color_grade'] = self._get_color_grade(color_grade)
            
            return result
        
        except Exception as e:
            print(f"❌ Narration generation failed: {e}")
            return None
    
    def _call_api(self, prompt: str, client, model: str) -> str:
        """Call API (Gemini or NVIDIA)"""
        if 'gemini' in model.lower():
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            return response.choices[0].message.content
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """Robust JSON extraction"""
        try:
            text = re.sub(r'```(?:json)?', '', text).strip()
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                candidate = text[start:end+1]
                return json.loads(candidate)
        except Exception:
            pass
        return None
    
    def _is_repetitive(self, narration: str, threshold: float = 0.7) -> bool:
        """Check if narration repeats recent ones"""
        current_words = set(narration.lower().split())
        
        for prev in list(self.narration_context)[-5:]:
            prev_words = set(prev.lower().split())
            if len(current_words & prev_words) / max(len(current_words | prev_words), 1) > threshold:
                return True
        
        return False
    
    def _remediate(self, base_narration: str, scene_type: str) -> str:
        """Generate variant if repetitive"""
        variants_by_scene = {
            'action': [
                "Power unleashes in devastating waves.",
                "Combat erupts with primal fury.",
                "The strongest warrior rises.",
                "Armies clash in total war.",
                "Strategy becomes reality in blood.",
            ],
            'dialogue': [
                "Words carry the weight of empires.",
                "A promise forged in dungeon stone.",
                "Harsh truths spoken by leaders.",
                "Alliances shift with single sentences.",
                "Negotiations determine empire futures.",
            ],
            'establishing': [
                "New territory awaits conquest ahead.",
                "The dungeon reveals new secrets.",
                "An empire expands its borders.",
                "Strategic positions fortified for war.",
                "The realm transforms once more.",
            ],
            'climactic': [
                "Everything comes down to this moment.",
                "The final battle begins now.",
                "Destiny itself hangs in balance.",
                "All sacrifices lead to this.",
                "The point of no return.",
            ]
        }
        
        variants = variants_by_scene.get(scene_type, variants_by_scene['action'])
        return variants[hash(base_narration) % len(variants)]
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: SMART PAUSE TIMING
    # ─────────────────────────────────────────────────────────────────────────
    
    def _calculate_pause_timing(self, scene_type: str, emotion: str, 
                               importance: int) -> Dict[str, int]:
        """
        Calculate smart pause timing based on context
        Tier 1 upgrade: dramatic pacing for emotional impact
        """
        # Base timing from config
        base_timing = config.TTS_PAUSE_CONFIG.get(
            scene_type, 
            config.TTS_PAUSE_CONFIG['action']
        )
        
        before_ms = base_timing['before_ms']
        after_ms = base_timing['after_ms']
        
        # Adjust for importance
        if importance >= 9:
            before_ms = int(before_ms * 1.5)  # 50% longer dramatic pause
            after_ms = int(after_ms * 1.5)
        elif importance <= 2:
            before_ms = int(before_ms * 0.7)  # Shorter for unimportant
            after_ms = int(after_ms * 0.7)
        
        # Adjust for emotion
        if emotion == 'emotional':
            after_ms = int(after_ms * 1.3)  # Let emotion breathe
        elif emotion == 'tense':
            before_ms = int(before_ms * 0.8)  # Quick tension
        
        return {'before_ms': before_ms, 'after_ms': after_ms}
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: ADAPTIVE TTS SPEED
    # ─────────────────────────────────────────────────────────────────────────
    
    def _calculate_tts_speed(self, importance: int, emotion: str, 
                            scene_type: str) -> float:
        """
        Calculate adaptive TTS speed for emotional impact
        Tier 1 upgrade: slow for dramatic, fast for action
        """
        base_speed = config.TTS_SPEED_BASE
        
        # Speed by importance
        if importance <= 2:
            speed_mod = 1.05  # Faster for unimportant
        elif importance >= 9:
            speed_mod = 0.80  # Slower for climactic
        elif importance >= 7:
            speed_mod = 0.85
        else:
            speed_mod = 0.95
        
        # Speed by emotion
        emotion_speed_mod = {
            'epic': 0.90,
            'dramatic': 0.85,
            'dark': 0.88,
            'emotional': 0.82,
            'tense': 0.92,
            'mysterious': 0.87
        }
        
        emotion_mod = emotion_speed_mod.get(emotion, 0.95)
        
        # Speed by scene type
        scene_speed_mod = {
            'action': 0.95,
            'dialogue': 0.93,
            'establishing': 0.97,
            'reaction': 0.85,
            'transition': 1.00,
            'climactic': 0.75
        }
        
        scene_mod = scene_speed_mod.get(scene_type, 0.95)
        
        # Combine all factors
        final_speed = base_speed * speed_mod * emotion_mod * scene_mod
        
        # Clamp to reasonable range
        return max(0.7, min(1.2, final_speed))
    
    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: COLOR GRADING
    # ─────────────────────────────────────────────────────────────────────────
    
    def _get_color_grade(self, grade_name: str) -> Dict[str, float]:
        """Get color grading values"""
        return config.COLOR_GRADES.get(
            grade_name,
            config.COLOR_GRADES['dramatic']
        )