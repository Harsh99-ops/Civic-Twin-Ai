# CIVIC-TWIN AI — Defect Detection Module

This is your part: an AI model that looks at road photos and detects
potholes, cracks, and waterlogging, then rates how severe each one is.

You don't need deep ML knowledge — we're using a **pretrained YOLOv8
model** and just teaching it your specific defect types. Follow these
steps in order.

---

## Step 1: Set up your environment

You have two options. **Google Colab is strongly recommended** since
you're a beginner — it gives you a free GPU and you don't install
anything locally.

### Option A — Google Colab (recommended)
1. Go to https://colab.research.google.com
2. New Notebook → Runtime → Change runtime type → select **GPU (T4)**
3. Upload `train.py`, `detect.py`, `severity.py` to the Colab session
   (left sidebar → Files → upload), or `git clone` if you push this to GitHub.
4. In a Colab cell, run:
   ```
   !pip install ultralytics
   ```

### Option B — Your own machine
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 2: Get a dataset

You need labeled images of potholes/cracks/waterlogging (images + boxes
drawn around each defect with a class label). Don't label thousands of
images by hand — use an existing open dataset:

1. Go to **Roboflow Universe**: https://universe.roboflow.com
2. Search **"pothole detection"** — there are several public datasets
   with thousands of pre-labeled images (some also include cracks).
3. Pick one, click **Download Dataset**, choose format **"YOLOv8"**.
4. This gives you a folder like:
   ```
   dataset/
     train/images, train/labels
     valid/images, valid/labels
     data.yaml          <-- this file tells YOLO where everything is & class names
   ```
5. If your dataset only has "pothole" as a class, that's fine — start
   there. You can add crack/waterlogging datasets later and merge them,
   or fine-tune further once the base pipeline is working. Don't try to
   do all three defect types perfectly before demo day; a solid pothole
   detector alone is already a strong, working demo.

Search terms to try: "pothole detection", "road damage detection",
"road crack detection", "waterlogging detection".

---

## Step 3: Train the model

Point `train.py` at your `data.yaml`:

```bash
python train.py --data dataset/data.yaml --epochs 50 --model yolov8n.pt
```

- On Colab GPU: ~20-40 minutes for a few thousand images.
- `yolov8n.pt` = nano model, fastest, good enough for a hackathon demo.
- Watch the training logs — you'll see `mAP` (mean average precision)
  going up each epoch. Above ~0.5 mAP is a reasonable hackathon result;
  above 0.7 is very good.

When it finishes, your trained model is saved at:
```
runs/detect/civic_twin_defect_model/weights/best.pt
```
**This file is your trained AI model. Keep it safe — download it from
Colab before your session ends, or it will be lost.**

---

## Step 4: Test it on a photo

```bash
python detect.py --image test_photo.jpg --weights runs/detect/civic_twin_defect_model/weights/best.pt
```

You'll get JSON output like:
```json
{
  "image": "test_photo.jpg",
  "defects_found": 1,
  "detections": [
    {
      "defect_type": "pothole",
      "confidence": 0.87,
      "bounding_box": {"x1": 120.5, "y1": 340.2, "x2": 310.8, "y2": 480.1},
      "severity": "High",
      "severity_score": 68.4
    }
  ],
  "overall_severity": "High"
}
```

This is exactly the structure your backend/GIS teammates need to plot
the defect on the map and prioritize it.

---

## Step 5: Turn it into a service your teammates can call

Your frontend/backend team doesn't need to touch Python or YOLO — they
just call an API endpoint. Run:

```bash
uvicorn api:app --reload --port 8001
```

Now they can send a POST request to `http://localhost:8001/detect` with
an image file, and get the same JSON back. Share this with your backend
teammate — this is the "contract" between your AI module and their system.

---

## What's next (once this works)

This covers Module 1 (Defect Detection). Your other AI/LLM modules from
the proposal:
- **Smart Complaint Analysis** (text → issue type/severity via an LLM API like Gemini)
- **Duplicate Complaint Detection** (embedding similarity between complaints)
- **Risk Prediction Engine** (predicting future failure hotspots from historical data)
- **Maintenance Prioritization / Budget Optimization** (ranking + optimization logic, can also be LLM-assisted reasoning)

We can build any of these next the same way — just say the word.

---

## Troubleshooting for beginners

- **"CUDA out of memory"** → lower `--imgsz` to 416, or use `yolov8n.pt` (smallest model).
- **Training is very slow** → make sure you selected GPU runtime in Colab (Runtime → Change runtime type).
- **mAP stays very low** → your dataset may be too small or poorly labeled; try a bigger Roboflow dataset, or train for more epochs.
- **"No module named ultralytics"** → run `pip install ultralytics` again in the same environment you're running the script from.
