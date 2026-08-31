from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
from app.core.config import settings
from app.services.plate import normalize,clean

class ALPRService:
    def __init__(self):
        self.reader=None; self.detector=None; self._ocr_attempted=False; self.detector_name="OCR-only / manual verification"
        if settings.OCR_ENABLED:
            self._ocr_attempted=False
        model=Path(settings.PLATE_MODEL_PATH)
        if model.exists():
            try:
                from ultralytics import YOLO
                self.detector=YOLO(str(model)); self.detector_name="YOLO + EasyOCR" if self.reader else "YOLO + manual verification"
            except Exception: self.detector=None

    def _decode(self,b):
        img=Image.open(BytesIO(b)).convert("RGB"); return np.array(img)
    def _ensure_ocr(self):
        if self._ocr_attempted or not settings.OCR_ENABLED: return
        self._ocr_attempted=True
        try:
            import easyocr
            self.reader=easyocr.Reader(["en"],gpu=False,verbose=False)
            self.detector_name="YOLO + EasyOCR" if self.detector is not None else "EasyOCR"
        except Exception:
            self.reader=None

    def recognize(self,b):
        self._ensure_ocr(); img=self._decode(b); crop=img
        plate_box=None
        # Use plate detector when a real trained model is supplied.
        if self.detector is not None:
            try:
                result=self.detector.predict(source=img,conf=0.35,verbose=False)[0]
                if len(result.boxes)>0:
                    box=result.boxes.xyxy[0].cpu().numpy().astype(int); x1,y1,x2,y2=box
                    plate_box=[int(x1),int(y1),int(x2),int(y2)]
                    crop=img[max(0,y1):max(y1+1,y2),max(0,x1):max(x1+1,x2)]
            except Exception: pass
        if self.reader is None:
            return {"license_plate":"","normalized_plate":"","raw_text":"","confidence":0.0,"status":"MANUAL_REQUIRED","verification_required":True,"detector":self.detector_name,"plate_box":plate_box}
        
        # OCR-friendly preprocessing; retain the original crop for auditability.
        gray=cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        clahe=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
        enhanced=cv2.adaptiveThreshold(clahe,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)
        results=self.reader.readtext(enhanced)
        if not results:
            results=self.reader.readtext(crop)
        if not results:
            return {"license_plate":"","normalized_plate":"","raw_text":"","confidence":0.0,"status":"MANUAL_REQUIRED","verification_required":True,"detector":self.detector_name,"plate_box":plate_box}
        texts=[r[1] for r in results]; confs=[float(r[2]) for r in results]; raw=" ".join(texts); norm=normalize(raw); conf=sum(confs)/len(confs)
        required=conf < settings.ALPR_CONFIDENCE_THRESHOLD or not norm
        return {"license_plate":norm,"normalized_plate":norm,"raw_text":clean(raw),"confidence":round(conf,4),"status":"MANUAL_REQUIRED" if required else "AUTO_ACCEPTED","verification_required":required,"detector":self.detector_name,"plate_box":plate_box}

alpr_service=ALPRService()
