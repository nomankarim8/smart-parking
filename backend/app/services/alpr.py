from io import BytesIO
from importlib.util import find_spec
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
 
import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.services.plate import clean, parse_plate


class ALPRService:
    """Dual-engine ALPR: optional YOLO plate detection + English/Bengali OCR."""

    def __init__(self):
        self.reader = None
        self.detector = None
        self._ocr_attempted = False
        self._tesseract_available = False
        self._tesseract_error: str | None = None
        self._tesseract_languages: list[str] = []
        self._easyocr_error: str | None = None
        self._detector_error: str | None = None
        self._inference_error: str | None = None
        self.detector_name = "Manual verification"

        model_path = Path(settings.PLATE_MODEL_PATH)
        if model_path.exists():
            try:
                from ultralytics import YOLO
                self.detector = YOLO(str(model_path))
                self.detector_name = "YOLO"
            except Exception as exc:
                self.detector = None
                self._detector_error = type(exc).__name__

        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            self._tesseract_available = bool(pytesseract.get_tesseract_version())
            if self._tesseract_available:
                self._tesseract_languages = pytesseract.get_languages(config="")
        except Exception as exc:
            self._tesseract_available = False
            self._tesseract_error = type(exc).__name__

    def status(self) -> dict:
        plate_model_exists = Path(settings.PLATE_MODEL_PATH).is_file()
        try:
            easyocr_installed = find_spec("easyocr") is not None
        except (ImportError, ValueError):
            easyocr_installed = False

        if self.detector is not None:
            detector_status = "READY"
        elif self._detector_error:
            detector_status = "LOAD_ERROR"
        else:
            detector_status = "MISSING"

        easyocr_status = (
            "READY" if self.reader is not None
            else "LOAD_ERROR" if self._easyocr_error
            else "AVAILABLE_NOT_INITIALIZED" if easyocr_installed and settings.OCR_ENABLED
            else "DISABLED" if not settings.OCR_ENABLED
            else "MISSING"
        )
        try:
            ultralytics_version = version("ultralytics")
        except PackageNotFoundError:
            ultralytics_version = None
        plate_model_path = Path(settings.PLATE_MODEL_PATH)
        vehicle_model_path = Path(settings.VEHICLE_MODEL_PATH)
        return {
            "plate_detector": {
                "status": detector_status,
                "readiness": "MODEL_READY" if self.detector is not None else "MODEL_MISSING" if not plate_model_exists else "LOAD_ERROR",
                "configured": plate_model_exists,
                "path": str(plate_model_path),
                "format": plate_model_path.suffix.lower() or None,
                "version": ultralytics_version,
                "error_type": self._detector_error,
                "inference_error_type": self._inference_error,
            },
            "vehicle_detector": {
                "status": "MODEL_MISSING" if not vehicle_model_path.is_file() else "CONFIGURED_NOT_LOADED",
                "configured": vehicle_model_path.is_file(),
                "path": str(vehicle_model_path),
                "loaded": False,
            },
            "ocr": {
                "easyocr": {"status": easyocr_status, "languages": ["en"]},
                "tesseract": {
                    "status": "READY" if self._tesseract_available else "MISSING",
                    "enabled": settings.BENGALI_OCR_ENABLED,
                    "path": settings.TESSERACT_CMD,
                    "languages_available": self._tesseract_languages,
                    "bengali_ready": "ben" in self._tesseract_languages,
                    "english_ready": "eng" in self._tesseract_languages,
                    "error_type": self._tesseract_error,
                },
            },
            "inference": {
                "device_configured": settings.AI_DEVICE,
                "image_size": settings.ALPR_IMAGE_SIZE,
                "confidence_threshold": settings.ALPR_CONFIDENCE_THRESHOLD,
                "opencv_version": cv2.__version__,
            },
            "automatic_plate_localization": self.detector is not None,
            "vehicle_detection": False,
            "real_footage_verified": False,
        }

    def _decode(self, data: bytes) -> np.ndarray:
        return np.array(Image.open(BytesIO(data)).convert("RGB"))
 
    def _ensure_easyocr(self):
        if self._ocr_attempted or not settings.OCR_ENABLED:
            return
        self._ocr_attempted = True
        try:
            import easyocr
            self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception as exc:
            self.reader = None
            self._easyocr_error = type(exc).__name__

    def _detect_plate(self, image: np.ndarray):
        if self.detector is None:
            return image, None
        try:
            result = self.detector.predict(
                source=image,
                conf=settings.ALPR_CONFIDENCE_THRESHOLD,
                imgsz=settings.ALPR_IMAGE_SIZE,
                device=settings.AI_DEVICE,
                verbose=False,
            )[0]
            if len(result.boxes) == 0:
                return image, None 
            
            confs = result.boxes.conf.cpu().numpy()
            idx = int(np.argmax(confs))
            x1, y1, x2, y2 = result.boxes.xyxy[idx].cpu().numpy().astype(int)
            h, w = image.shape[:2]
            x1, y1 = max(0, min(x1, w - 1)), max(0, min(y1, h - 1))
            x2, y2 = max(x1 + 1, min(x2, w)), max(y1 + 1, min(y2, h))
            return image[y1:y2, x1:x2], [x1, y1, x2, y2]
        except Exception as exc:
            self._inference_error = type(exc).__name__
            return image, None

    def _preprocess_variants(self, image: np.ndarray):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        yield "gray", gray
        enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        yield "clahe", enhanced
        yield "adaptive", cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield "otsu", otsu

    def _easy_candidates(self, image: np.ndarray):
        self._ensure_easyocr()
        if self.reader is None:
            return []
        candidates = []
        for variant_name, variant in self._preprocess_variants(image):
            try:
                results = self.reader.readtext(variant, detail=1, paragraph=False, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ")
                texts, confs = [], []
                for item in results:
                    if len(item) >= 3 and str(item[1]).strip():
                        texts.append(str(item[1]).strip())
                        confs.append(float(item[2]))
                if texts:
                    candidates.append({"text": " ".join(texts), "confidence": sum(confs)/len(confs), "language": "en", "engine": "EasyOCR", "variant": variant_name})
            except Exception:
                continue
        return candidates
 
    def _tesseract_candidates(self, image: np.ndarray):
        if not self._tesseract_available:
            return []
        try:
            import pytesseract
            from pytesseract import Output
        except Exception:
            return []
        candidates = []
        for variant_name, variant in self._preprocess_variants(image):
            for lang in (["ben"] if settings.BENGALI_OCR_ENABLED else []) + ["eng"]:
                try:
                    data = pytesseract.image_to_data(variant, lang=lang, config="--psm 7", output_type=Output.DICT)
                    texts, scores = [], []
                    for i, text in enumerate(data["text"]):
                        text = text.strip()
                        if not text:
                            continue
                        try:
                            conf = float(data["conf"][i])
                        except Exception:
                            conf = 0
                        if conf > 0:
                            texts.append(text)
                            scores.append(conf / 100.0)
                    if texts:
                        candidates.append({"text": " ".join(texts), "confidence": sum(scores)/len(scores), "language": "bn" if lang == "ben" else "en", "engine": "Tesseract", "variant": variant_name})
                except Exception:
                    continue
        return candidates

    def recognize(self, data: bytes) -> dict:
        image = self._decode(data)
        crop, plate_box = self._detect_plate(image)
        candidates = self._easy_candidates(crop) + self._tesseract_candidates(crop)
        if not candidates:
            return {
                "input_image_url": None, "license_plate": "", "normalized_plate": "", "raw_text": "",
                "confidence": 0.0, "status": "MANUAL_REQUIRED", "verification_required": True,
                "detector": self.detector_name, "plate_box": plate_box, "region_name": "", "class_bn": "",
                "class_code": "", "series_number": "", "vehicle_number": "", "vehicle_category": None,
                "suggested_category_id": None, "ocr_language": None, "ocr_engine": None,
            }

        ranked = []
        for candidate in candidates:
            parsed = parse_plate(candidate["text"])
            score = candidate["confidence"] + (0.20 if parsed["valid"] else 0) + (0.05 if parsed["class_code"] else 0)
            ranked.append((score, candidate, parsed))
        _, candidate, parsed = max(ranked, key=lambda x: x[0])

        confidence = min(1.0, candidate["confidence"] + (0.10 if parsed["valid"] else 0))
        verification_required = confidence < settings.ALPR_CONFIDENCE_THRESHOLD or not parsed["valid"]
        return {
            "input_image_url": None,
            "license_plate": parsed["normalized_plate"], "normalized_plate": parsed["normalized_plate"],
            "raw_text": clean(candidate["text"]), "confidence": round(confidence, 4),
            "status": "MANUAL_REQUIRED" if verification_required else "AUTO_ACCEPTED",
            "verification_required": verification_required,
            "detector": f"{self.detector_name} + {candidate['engine']}", "plate_box": plate_box,
            "region_name": parsed["region_name"], "class_bn": parsed["class_bn"], "class_code": parsed["class_code"],
            "series_number": parsed["series_number"], "vehicle_number": parsed["vehicle_number"],
            "vehicle_category": parsed["vehicle_category"], "suggested_category_id": parsed["suggested_category_id"],
            "ocr_language": candidate["language"], "ocr_engine": candidate["engine"],
        }


alpr_service = ALPRService()
