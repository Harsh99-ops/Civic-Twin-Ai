"""
CIVIC-TWIN AI — Defect Detection Model Training
=================================================
This script fine-tunes a pretrained YOLOv8 model on a road-defect dataset
(potholes, cracks, waterlogging) so it can detect these issues in
citizen-uploaded photos.

HOW TO RUN THIS:
1. Get a dataset (see README.md "Step 2: Get a dataset" section).
2. Put the dataset's data.yaml path below (or pass it as an argument).
3. Run:  python train.py
4. Training results (best model weights) will be saved in:
   runs/detect/civic_twin_defect_model/weights/best.pt

This is designed to run on Google Colab with a free GPU (recommended for
beginners) or on your own machine if you have a GPU.
"""

from ultralytics import YOLO
import argparse


def train_model(data_yaml: str, epochs: int = 50, img_size: int = 640, model_size: str = "yolov8n.pt"):
    """
    Fine-tune a YOLOv8 model on a custom road-defect dataset.

    Args:
        data_yaml: path to the dataset's data.yaml file (defines classes + image paths)
        epochs: how many passes over the dataset (50 is a good starting point)
        img_size: image resolution used for training (640 is standard, faster on Colab)
        model_size: which pretrained YOLOv8 checkpoint to start from.
                    "yolov8n.pt" = nano (fastest, good for beginners/limited GPU)
                    "yolov8s.pt" = small (a bit more accurate, still fast)
    """
    # Load a pretrained YOLOv8 model — this already knows general object
    # shapes from millions of images, we're just teaching it road defects.
    model = YOLO(model_size)

    # Fine-tune it on your dataset.
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=img_size,
        batch=16,
        name="civic_twin_defect_model",
        patience=15,        # stop early if it stops improving (saves Colab time)
        device=0,            # 0 = first GPU. Use "cpu" if no GPU available (much slower).
    )

    print("\nTraining complete!")
    print("Best model weights saved at: runs/detect/civic_twin_defect_model/weights/best.pt")
    print("Copy that file — you'll need it for inference (detect.py) and the API (api.py).")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CIVIC-TWIN AI defect detection model")
    parser.add_argument("--data", type=str, default="dataset/data.yaml",
                         help="Path to dataset's data.yaml file")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--model", type=str, default="yolov8n.pt",
                         help="yolov8n.pt (fastest) or yolov8s.pt (more accurate)")
    args = parser.parse_args()

    train_model(data_yaml=args.data, epochs=args.epochs, img_size=args.imgsz, model_size=args.model)
