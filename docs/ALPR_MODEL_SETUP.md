# ALPR Model Setup

The application has two levels of ALPR operation.

## 1. Demo / OCR-only mode

The application can accept an uploaded image and run EasyOCR when `OCR_ENABLED=true`. A low-confidence result is returned as `MANUAL_REQUIRED`; it is intentionally not treated as a confirmed plate.

## 2. Real plate detector mode

Place a trained Ultralytics YOLO license-plate detector at:

```text
ai-models/plate_yolo.pt
```

The model should be trained for license-plate bounding boxes. It is not enough to place a generic vehicle-detection model in this file.

Recommended workflow:

1. Collect a legally obtained, representative dataset of Bangladeshi vehicle plates.
2. Annotate plate bounding boxes.
3. Split into train/validation/test sets.
4. Train a compatible YOLO model.
5. Copy the trained `.pt` file to `ai-models/plate_yolo.pt`.
6. Restart the backend.
7. Verify the ALPR response field `detector`.
8. Measure precision/recall and character-level recognition accuracy on a held-out test set before making any accuracy claim.

## OCR notes

The current OCR reader is English-character based. Bangladesh-specific plate recognition is improved by combining the plate detector with domain-specific normalization and, for a higher-accuracy research version, a dedicated OCR model/dataset covering the actual plate typography.

## Manual verification

Never auto-commit an unverified low-confidence OCR result. The frontend should allow the operator to edit the normalized plate and then submit the final value to the parking entry workflow.

## Real cameras

Browser applications generally should not open an RTSP URL directly. For a production deployment, use one of:

- a backend RTSP reader using OpenCV/FFmpeg;
- an authenticated camera gateway that converts RTSP to browser-safe WebRTC/HLS;
- a local USB camera captured by the browser with `getUserMedia`.

The project keeps the ALPR API independent from the camera source so Demo/Upload mode remains available for the final-year presentation.
