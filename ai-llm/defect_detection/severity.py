"""
Converts a raw YOLO detection (bounding box + confidence) into a
human-meaningful severity label. This is the "AI reasoning" layer that
turns a bounding box into something a municipal officer can act on.

The logic here is intentionally simple and explainable — for a hackathon,
judges will trust a clear rule-based severity score more than a black-box
number. You can make this fancier later (e.g. factor in road type, traffic
density from GIS data, etc.) once the core pipeline works.
"""


def compute_severity(box_area_ratio: float, confidence: float, defect_class: str) -> dict:
    """
    Estimate severity of a detected road defect.

    Args:
        box_area_ratio: the bounding box's area as a fraction of the whole
                         image area (0.0 to 1.0). A pothole that fills more
                         of the frame is generally a bigger/closer defect.
        confidence: the model's detection confidence (0.0 to 1.0).
        defect_class: one of "pothole", "crack", "waterlogging".

    Returns:
        dict with 'severity' (Low/Medium/High/Critical) and 'severity_score' (0-100).
    """
    # Base score scales with how much of the image the defect covers.
    size_score = min(box_area_ratio * 400, 70)  # cap contribution at 70 points

    # Confidence contributes up to 20 points — a very confident detection
    # is more trustworthy and worth escalating.
    confidence_score = confidence * 20

    # Some defect types are inherently riskier regardless of size.
    class_weight = {
        "pothole": 10,
        "waterlogging": 8,
        "crack": 4,
    }.get(defect_class.lower(), 5)

    total_score = round(size_score + confidence_score + class_weight, 1)
    total_score = min(total_score, 100)

    if total_score >= 75:
        severity = "Critical"
    elif total_score >= 50:
        severity = "High"
    elif total_score >= 25:
        severity = "Medium"
    else:
        severity = "Low"

    return {"severity": severity, "severity_score": total_score}


def box_area_ratio(box_xyxy, img_width: int, img_height: int) -> float:
    """
    Compute what fraction of the image a bounding box covers.
    box_xyxy: [x1, y1, x2, y2] pixel coordinates of the box.
    """
    x1, y1, x2, y2 = box_xyxy
    box_area = max(0, (x2 - x1)) * max(0, (y2 - y1))
    image_area = img_width * img_height
    return box_area / image_area if image_area > 0 else 0.0
