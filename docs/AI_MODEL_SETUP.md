# AI model setup and readiness

## Model files

Keep privately obtained and licensed model files outside source control:

- Plate detector: `ai-models\plate_yolo.pt`
- Optional vehicle detector: `ai-models\vehicle_yolo.pt`

The backend defaults to these paths when started from `backend\`. Override
`PLATE_MODEL_PATH` or `VEHICLE_MODEL_PATH` in `backend\.env` for another
location. Supported model loading depends on the installed Ultralytics release;
the currently integrated detector expects a compatible YOLO model checkpoint.
Do not download untrusted weights automatically.

Configure inference with `AI_DEVICE=cpu` (the safe default),
`ALPR_IMAGE_SIZE=640`, and `ALPR_CONFIDENCE_THRESHOLD=0.80`. GPU use is
optional and requires compatible local CUDA drivers and a matching PyTorch
installation. The rest of the application does not require a GPU.

## Diagnostics

From `backend\`, run:

```powershell
..\venv\Scripts\python.exe check_ai.py
```

The diagnostic reports configured paths, model loading state, package version,
OpenCV version, the selected inference device, and OCR engine/language
availability. The authenticated API equivalent is
`GET /api/v1/alpr/status`. `MODEL_READY` means a model loaded; it does not mean
that accuracy was validated on real footage. The response explicitly keeps
`real_footage_verified` false until a human performs that validation.

## Sample inference

Use the application’s authenticated ALPR image-upload page or
`POST /api/v1/alpr/detect` with a representative, authorized test image. Check
the returned `verification_required`, detector state, confidence, and
bounding-box values. Confirm the plate manually before creating a parking
record. Missing weights must leave the detector unavailable and must never
generate a synthetic detection.

## Bengali and English OCR

Tesseract must be installed locally with both `eng` and `ben` language data.
Set `TESSERACT_CMD` to the executable path and run the diagnostic to see
`languages_available`, `english_ready`, and `bengali_ready`. EasyOCR is only
configured for English (`en`) here; Bengali is not assumed to be supported by
EasyOCR. Install optional Python dependencies through `requirements.txt`;
network downloads of OCR models may require a separate controlled setup.

Real footage, camera position, lighting, supported formats, trained weights,
and measured accuracy remain external validation requirements.
