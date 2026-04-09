"""OCR extraction helpers (Tesseract + optional vision fallback)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

import cv2
import numpy as np
import pytesseract
from pytesseract import TesseractError
from PIL import Image

from pipeline.config import config


@dataclass
class OCRResult:
    extracted_text: str
    ocr_confidence: float
    has_text: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "extracted_text": self.extracted_text,
            "ocr_confidence": self.ocr_confidence,
            "has_text": self.has_text,
        }


class OCREngine:
    """Hybrid OCR extractor used by tile processor."""

    def __init__(self) -> None:
        self.tesseract_ready = self._has_tesseract()

    @staticmethod
    def _has_tesseract() -> bool:
        try:
            _ = pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text_tesseract(self, image_path: str) -> Tuple[str, float]:
        if not self.tesseract_ready:
            return "", 0.0

        img = cv2.imread(image_path)
        if img is None:
            return "", 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(
            denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Extremely tall stitched images can fail with "Image too large".
        # Try normal OCR first, then fallback to strip-based OCR.
        try:
            return self._ocr_from_binary(binary)
        except TesseractError:
            pass

        # Fallback 1: downscale tall images before OCR.
        h, w = binary.shape[:2]
        max_dim = 12000
        if h > max_dim:
            scale = max_dim / float(h)
            resized = cv2.resize(binary, (max(1, int(w * scale)), max_dim), interpolation=cv2.INTER_AREA)
            try:
                return self._ocr_from_binary(resized)
            except TesseractError:
                pass

        # Fallback 2: strip OCR with overlap to avoid hard height limits.
        return self._ocr_in_strips(binary)

    def _ocr_from_binary(self, binary: np.ndarray) -> Tuple[str, float]:
        data = pytesseract.image_to_data(
            binary,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
            lang="eng",
        )

        words = []
        confidences = []
        for idx, txt in enumerate(data.get("text", [])):
            txt = (txt or "").strip()
            if not txt:
                continue
            try:
                conf = float(data["conf"][idx])
            except Exception:
                conf = -1
            if conf > 25:
                words.append(txt)
                confidences.append(conf)

        merged = " ".join(words).strip()
        avg_conf = (float(np.mean(confidences)) / 100.0) if confidences else 0.0
        return merged, round(avg_conf, 3)

    def _ocr_in_strips(self, binary: np.ndarray) -> Tuple[str, float]:
        h, _ = binary.shape[:2]
        chunk_h = 7000
        overlap = 300
        cursor = 0
        all_words = []
        all_conf = []

        while cursor < h:
            end = min(h, cursor + chunk_h)
            chunk = binary[cursor:end, :]
            try:
                data = pytesseract.image_to_data(
                    chunk,
                    output_type=pytesseract.Output.DICT,
                    config="--oem 3 --psm 6",
                    lang="eng",
                )
                for idx, txt in enumerate(data.get("text", [])):
                    txt = (txt or "").strip()
                    if not txt:
                        continue
                    try:
                        conf = float(data["conf"][idx])
                    except Exception:
                        conf = -1
                    if conf > 25:
                        all_words.append(txt)
                        all_conf.append(conf)
            except TesseractError:
                # Skip failed strip and continue.
                pass
            if end >= h:
                break
            cursor = max(0, end - overlap)

        merged = " ".join(all_words).strip()
        avg_conf = (float(np.mean(all_conf)) / 100.0) if all_conf else 0.0
        return merged, round(avg_conf, 3)

    @staticmethod
    def _gemini_extract(image_path: str, gemini_client: Any, model_name: str) -> Tuple[str, float]:
        if gemini_client is None:
            return "", 0.0
        try:
            img = Image.open(image_path)
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=[
                    "Extract all visible text from this manga/manhwa panel. "
                    "Return plain text only.",
                    img,
                ],
            )
            text = (response.text or "").strip()
            return text, 0.85 if text else 0.0
        except Exception:
            return "", 0.0

    def hybrid_extract(self, image_path: str, gemini_client: Any = None, gemini_model: str = "") -> Dict[str, Any]:
        t_text, t_conf = self.extract_text_tesseract(image_path)

        # Optional vision fallback if Tesseract is weak.
        if t_conf < config.OCR_CONFIDENCE_THRESHOLD and gemini_client and gemini_model:
            g_text, g_conf = self._gemini_extract(image_path, gemini_client, gemini_model)
            if g_conf > t_conf and len(g_text) > len(t_text):
                t_text, t_conf = g_text, g_conf

        result = OCRResult(
            extracted_text=t_text,
            ocr_confidence=round(float(t_conf), 2),
            has_text=len(t_text) >= config.TEXT_EXTRACTION_THRESHOLD,
        )
        return result.to_dict()

