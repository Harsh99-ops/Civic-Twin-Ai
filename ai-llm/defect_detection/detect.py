"""
CIVIC-TWIN AI — Defect Detection Inference
=============================================
Runs the trained YOLOv8 model on a single image and returns a clean,
structured JSON result describing every defect found — ready to hand off
to the backend team.

USAGE:
    python detect.py --image path/to/photo.jpg --weights runs/detect/civic_twin_defect_model/weights/best.pt
"""

import argparse
import json
from ultralytics import YOLO
from PIL import Image
from severity import compute_severity, box_area_ratio


def detect_defects(image_path: str, weights_path: str, conf_threshold: float = 0.35) -> dict:
    """
    Run defect detection on one image.

    Args:
        image_path: path to the input photo.
        weights_path: path to trained model weights (best.pt from training).
        conf_threshold: minimum confidence to report a detection (filters noise).

    Returns:
        dict matching the JSON contract the backend expects.
    """
    model = YOLO(weights_path)
    img = Image.open(image_path)
    img_width, img_height = img.size

    results = model.predict(source=image_path, conf=conf_threshold, verbose=False)
    result = results[0]

    defects = []
    for box in result.boxes:
        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
        confidence = float(box.conf[0])
        xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

        ratio = box_area_ratio(xyxy, img_width, img_height)
        sev = compute_severity(ratio, confidence, class_name)

        defects.append({
            "defect_type": class_name,
            "confidence": round(confidence, 3),
            "bounding_box": {
                "x1": round(xyxy[0], 1), "y1": round(xyxy[1], 1),
                "x2": round(xyxy[2], 1), "y2": round(xyxy[3], 1),
            },
            "severity": sev["severity"],
            "severity_score": sev["severity_score"],
        })

    # Sort so the most severe defect appears first — handy for the dashboard.
    defects.sort(key=lambda d: d["severity_score"], reverse=True)

    output = {
        "image": image_path,
        "image_width": img_width,
        "image_height": img_height,
        "defects_found": len(defects),
        "detections": defects,
        # This top-level severity is what the Risk Prediction / Prioritization
        # modules downstream will consume.
        "overall_severity": defects[0]["severity"] if defects else "None",
    }
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CIVIC-TWIN AI defect detection on an image")
    parser.add_argument("--image", type=str, required=True, help="Path to input image")
    parser.add_argument("--weights", type=str, default="runs/detect/civic_twin_defect_model/weights/best.pt")
    parser.add_argument("--conf", type=float, default=0.35, help="Confidence threshold")
    args = parser.parse_args()

    output = detect_defects(args.image, args.weights, args.conf)
    print(json.dumps(output, indent=2))
