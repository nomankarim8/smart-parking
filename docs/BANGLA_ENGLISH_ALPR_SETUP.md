# Bangla + English ALPR Setup

The ALPR module supports two OCR paths: English OCR with EasyOCR and Bengali/English OCR with Tesseract. A trained YOLO plate detector is optional for image upload testing but required for reliable automatic plate localization on full vehicle frames.

## 1. Install Tesseract on Windows

Install Tesseract OCR and make sure the executable is available at the path configured by `TESSERACT_CMD` in `backend/.env`. The default expected path is:

`C:\Program Files\Tesseract-OCR\tesseract.exe`

Make sure the `ben` and `eng` trained data files are installed.

Verify from PowerShell:

```powershell
tesseract --version
tesseract --list-langs
```

You should see `ben` and `eng` in the language list.

## 2. Install Python dependencies

From `backend/`:

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure `.env`

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
BENGALI_OCR_ENABLED=true
OCR_ENABLED=true
ALPR_CONFIDENCE_THRESHOLD=0.80
PLATE_MODEL_PATH=../ai-models/plate_yolo.pt
```

## 4. Plate normalization examples

The parser intentionally stores the raw OCR text and a canonical searchable English representation. Examples:

- `ঢাকা মেট্রো গ ১২-৩৪৫৬` → `DHAKA METRO GA 12-3456`
- `ঢাকা মেট্রো ল ১৭-৭৫৪৪` → `DHAKA METRO LA 17-7544`
- `ঢাকা মেট্রো ক ১১-১২৩৪` → `DHAKA METRO KA 11-1234`
- `DHAKA METRO GA 12-3456` → `DHAKA METRO GA 12-3456`

The parser also extracts region, Bengali class character, English class code, series number, vehicle number, suggested vehicle category, OCR language and OCR engine.

## 5. Confidence handling

`ALPR_CONFIDENCE_THRESHOLD=0.80` is a configurable review threshold. A result below the threshold or with an invalid plate structure is marked `MANUAL_REQUIRED`. The operator can edit the normalized plate before parking entry.

## 6. YOLO model

Place a compatible trained plate detector at:

`ai-models/plate_yolo.pt`

Do not treat a generic object-detection model as a license-plate detector. The model should be trained/evaluated on representative plate images from the target deployment context.

## 7. Vehicle-category suggestion

The plate class is used only as a category suggestion. The current mapping follows the project rules and common Bangladesh plate class conventions, for example:

`ল → LA → MOTORCYCLE`

`ক → KA → CAR`

`গ → GA → CAR`

The registered vehicle record remains authoritative, and the operator can manually override the suggestion.
