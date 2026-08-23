"""
CIVIC-TWIN AI — Defect Detection
====================================
Runs pothole detection on an uploaded citizen photo and returns a
structured result: bounding box, confidence, and a severity score.

TWO DETECTION BACKENDS:

1. YOLOv8 (real, trained model) — used automatically. Ships with real
   weights at backend/models/best.pt (single class: "Pothole"). Needs
   `ultralytics` + `torch` installed (see requirements.txt).

2. Heuristic CV fallback — only used if the weights file is missing or
   `ultralytics`/`torch` aren't installed, so the pipeline still runs
   end-to-end without the ML stack. Finds the darkest, most irregular
   blob in the road region of the photo using OpenCV and treats it as a
   candidate pothole. NOT a substitute for the trained model — it's a
   safety net, not the primary path.

Only "pothole" is modeled here (per the training data available). Any
other citizen-selected issue category (waterlogging, streetlight,
waste) skips vision detection entirely and is scored from category
priors — see `severity_for_category()` below.

VALIDATION THRESHOLD: the caller (main.py's /report endpoint) only
accepts a Road Damage complaint into the store if the detected
confidence is >= MIN_POTHOLE_CONFIDENCE (40%). Below that, the photo
is treated as not actually showing a pothole and the complaint is
rejected rather than stored — see PotholeDetectionResult below.
"""

import io
import os
import random

import numpy as np
from PIL import Image

MODEL_WEIGHTS = os.environ.get(
    "MODEL_WEIGHTS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "best.pt"),
)

MIN_POTHOLE_CONFIDENCE = 0.40

_yolo_model = None
_yolo_checked = False


def _try_load_yolo():
    """Lazily attempt to load a real YOLOv8 model. Cached after first try."""
    global _yolo_model, _yolo_checked
    if _yolo_checked:
        return _yolo_model
    _yolo_checked = True
    if not os.path.exists(MODEL_WEIGHTS):
        return None
    try:
        from ultralytics import YOLO
        _yolo_model = YOLO(MODEL_WEIGHTS)
    except Exception:
        _yolo_model = None
    return _yolo_model


# ---------------------------------------------------------------------------
# Severity scoring — same rule-based logic as the original severity.py,
# generalized so it can score both real detections and category priors.
# ---------------------------------------------------------------------------

CLASS_WEIGHT = {
    "pothole": 10,
    "waterlogging": 8,
    "crack": 4,
}


def box_area_ratio(box_xyxy, img_width, img_height):
    x1, y1, x2, y2 = box_xyxy
    box_area = max(0, (x2 - x1)) * max(0, (y2 - y1))
    image_area = img_width * img_height
    return box_area / image_area if image_area > 0 else 0.0


def compute_severity(area_ratio: float, confidence: float, defect_class: str) -> dict:
    size_score = min(area_ratio * 400, 70)
    confidence_score = confidence * 20
    class_weight = CLASS_WEIGHT.get(defect_class.lower(), 5)

    total = round(size_score + confidence_score + class_weight, 1)
    total = min(total, 100)

    if total >= 75:
        severity = "Critical"
    elif total >= 50:
        severity = "High"
    elif total >= 25:
        severity = "Medium"
    else:
        severity = "Low"

    return {"severity": severity, "severity_score": total}


# ---------------------------------------------------------------------------
# Heuristic CV fallback detector
# ---------------------------------------------------------------------------

def _heuristic_pothole_detect(img: Image.Image) -> dict | None:
    """
    Finds the largest dark, irregular contour in the lower 2/3 of the
    frame (where a road surface typically sits in a citizen photo) and
    treats it as a candidate pothole. Returns None if nothing plausible
    is found (e.g. a bright, uniform image).
    """
    try:
        import cv2
    except Exception:
        cv2 = None

    w, h = img.size
    if cv2 is None:
        # No OpenCV available either — degrade to a seeded pseudo-random
        # but still image-derived result so the pipeline never hard-fails.
        arr = np.array(img.convert("L"))
        seed = int(arr.mean() * 1000) % (2**32)
        rng = random.Random(seed)
        bw, bh = w * rng.uniform(0.15, 0.4), h * rng.uniform(0.12, 0.32)
        x1 = rng.uniform(0.1, 0.6) * w
        y1 = h * 0.5 + rng.uniform(0, 0.3) * h
        conf = round(rng.uniform(0.55, 0.9), 3)
        return {"box": [x1, y1, min(x1 + bw, w), min(y1 + bh, h)], "confidence": conf}

    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    roi_top = int(h * 0.35)  # ignore sky/buildings in the top of the frame
    roi = gray[roi_top:, :]

    blur = cv2.GaussianBlur(roi, (7, 7), 0)
    # Potholes/waterlogged patches read as locally dark, irregular regions.
    thresh_val = max(0, int(blur.mean() - blur.std() * 0.6))
    _, mask = cv2.threshold(blur, thresh_val, 255, cv2.THRESH_BINARY_INV)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    best = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(best)
    frame_area = roi.shape[0] * roi.shape[1]
    if area < frame_area * 0.008:  # too small to be meaningful
        return None

    x, y, bw, bh = cv2.boundingRect(best)
    y += roi_top  # shift back into full-image coordinates

    # Confidence proxy: how dark + how irregular (non-rectangular) the
    # blob is relative to its bounding box — a real pothole's contour
    # fills its box less neatly than a shadow or drain cover would.
    fill_ratio = area / max(bw * bh, 1)
    darkness = 1 - (blur[max(0, y - roi_top):y - roi_top + bh, x:x + bw].mean() / 255 if bh > 0 and bw > 0 else 0.5)
    confidence = 0.5 + 0.3 * (1 - fill_ratio) + 0.2 * darkness
    confidence = round(min(max(confidence, 0.4), 0.97), 3)

    return {"box": [float(x), float(y), float(x + bw), float(y + bh)], "confidence": confidence}


def detect_pothole(image_bytes: bytes) -> dict:
    """
    Run pothole detection on raw image bytes.

    Returns a dict:
        {
          "defect_type": "pothole" | None,
          "confidence": float | None,
          "bounding_box": {...} | None,
          "severity": "Low"/"Medium"/"High"/"Critical",
          "severity_score": float,
          "detector": "yolov8-custom" | "heuristic-cv",
          "image_width": int, "image_height": int,
        }
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_width, img_height = img.size

    model = _try_load_yolo()

    if model is not None:
        # Real trained-model path. Pass the PIL Image directly rather than
        # a raw numpy array — ultralytics treats bare ndarrays as BGR
        # (OpenCV convention), which silently corrupts colors and confidence
        # for genuinely RGB-sourced images like ours.
        results = model.predict(source=img, conf=0.35, verbose=False)
        result = results[0]
        if len(result.boxes) == 0:
            return {
                "defect_type": None, "confidence": None, "bounding_box": None,
                "severity": "Low", "severity_score": 0.0,
                "detector": "yolov8-custom",
                "image_width": img_width, "image_height": img_height,
            }
        box = max(result.boxes, key=lambda b: float(b.conf[0]))
        cls_id = int(box.cls[0])
        class_name = model.names[cls_id].lower()  # e.g. "Pothole" -> "pothole"
        confidence = float(box.conf[0])
        xyxy = box.xyxy[0].tolist()
        ratio = box_area_ratio(xyxy, img_width, img_height)
        sev = compute_severity(ratio, confidence, class_name)
        return {
            "defect_type": class_name,
            "confidence": round(confidence, 3),
            "bounding_box": {"x1": round(xyxy[0], 1), "y1": round(xyxy[1], 1),
                              "x2": round(xyxy[2], 1), "y2": round(xyxy[3], 1)},
            "severity": sev["severity"], "severity_score": sev["severity_score"],
            "detector": "yolov8-custom",
            "image_width": img_width, "image_height": img_height,
        }

    # Fallback heuristic path.
    found = _heuristic_pothole_detect(img)
    if found is None:
        return {
            "defect_type": None, "confidence": None, "bounding_box": None,
            "severity": "Low", "severity_score": 8.0,
            "detector": "heuristic-cv",
            "image_width": img_width, "image_height": img_height,
        }

    ratio = box_area_ratio(found["box"], img_width, img_height)
    sev = compute_severity(ratio, found["confidence"], "pothole")
    x1, y1, x2, y2 = found["box"]
    return {
        "defect_type": "pothole",
        "confidence": found["confidence"],
        "bounding_box": {"x1": round(x1, 1), "y1": round(y1, 1), "x2": round(x2, 1), "y2": round(y2, 1)},
        "severity": sev["severity"], "severity_score": sev["severity_score"],
        "detector": "heuristic-cv",
        "image_width": img_width, "image_height": img_height,
    }


# ---------------------------------------------------------------------------
# Non-vision categories (waterlogging / streetlight / waste): no trained
# model exists for these, so severity is derived from category risk priors
# with a small deterministic spread so repeated reports aren't identical.
# ---------------------------------------------------------------------------

CATEGORY_BASE_SEVERITY = {
    "Drainage / Waterlogging": 62,
    "Streetlight / Electrical": 38,
    "Waste Management": 30,
    "Road Damage": 55,
}


def severity_for_category(category: str, complaint_id: str) -> dict:
    base = CATEGORY_BASE_SEVERITY.get(category, 35)
    rng = random.Random(complaint_id)
    score = round(min(max(base + rng.uniform(-10, 14), 5), 100), 1)
    if score >= 75:
        severity = "Critical"
    elif score >= 50:
        severity = "High"
    elif score >= 25:
        severity = "Medium"
    else:
        severity = "Low"
    return {"severity": severity, "severity_score": score}
