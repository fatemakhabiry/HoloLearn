"""
classifier_runner.py
====================
Stage 6: run your CNN classifier over the crops listed in the CSV,
write the predicted label and confidence score back into the CSV.

Usage
-----
    from classifier_runner import run_classifier

    csv_path = run_classifier(
        csv_path   = "output/crops/page1.csv",
        model_path = "models/classifier.pt",
        device     = "cpu",          # or "cuda"
        skip_done  = True,           # skip rows that already have a label
        batch_size = 32,             # images processed together on GPU
    )

Label mapping (must match your CNN's output classes)
-----------------------------------------------------
    0 → code
    1 → diagram
    2 → equation
    3 → table
    4 → text
"""

import csv
import os
import torch.nn as nn
from torchvision import models

LABEL_MAP = {
    0: "code",
    1: "diagram",
    2: "equation",
    3: "table",
    4: "text",
}


def build_model(n_classes=5, dropout=0.3):
    """Exactly the same architecture you used during training."""
    model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")

    for param in model.features.parameters():
        param.requires_grad = False

    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.Hardswish(),
        nn.Dropout(p=dropout),
        nn.Linear(256, n_classes),
    )
    return model


def _load_model(model_path: str, device: str = "cpu"):
    import torch

    print(f"🔄 Loading model from: {model_path}")

    if device == "cuda" and not torch.cuda.is_available():
        print("⚠️ CUDA not available → falling back to CPU")
        device = "cpu"

    map_location = torch.device(device)
    checkpoint   = torch.load(model_path, map_location=map_location)
    model        = build_model(n_classes=5, dropout=0.3)

    if isinstance(checkpoint, dict):
        if "state_dict" in checkpoint:
            print(" Loading from state_dict")
            model.load_state_dict(checkpoint["state_dict"])
        elif "model_state_dict" in checkpoint:
            print("Loading from model_state_dict")
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            print("Loading raw state_dict")
            model.load_state_dict(checkpoint)
    else:
        print("Full model loaded")
        model = checkpoint

    model = model.to(map_location)
    model.eval()
    print(f"Model loaded successfully on {map_location}")
    return model


def _make_transform():
    from torchvision import transforms
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])


def _predict_batch(model, image_paths: list, device: str, transform) -> list:
    """
    Run a batch of crops through the classifier in one forward pass.
    Returns a list of (label, confidence) tuples in the same order as image_paths.
    confidence is a float in [0.0, 1.0] — softmax probability of the top class.
    """
    import torch
    from PIL import Image

    tensors = []
    for path in image_paths:
        img = Image.open(path).convert("RGB")
        tensors.append(transform(img))

    batch = torch.stack(tensors).to(device)   # (B, 3, 224, 224)

    with torch.no_grad():
        logits      = model(batch)                        # (B, num_classes)
        probs       = torch.softmax(logits, dim=1)        # (B, num_classes)
        top_probs, top_indices = probs.max(dim=1)         # (B,), (B,)

    results = []
    for idx, prob in zip(top_indices.tolist(), top_probs.tolist()):
        label      = LABEL_MAP.get(idx, "text")
        confidence = round(prob, 4)
        results.append((label, confidence))

    return results


def _write_csv(rows: list, csv_path: str) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_classifier(
    csv_path:   str,
    model_path: str,
    device:     str  = "cpu",
    skip_done:  bool = False,
    batch_size: int  = 32,
) -> str:
    """
    Read the crop CSV, classify each crop, write label + confidence back.

    Parameters
    ----------
    csv_path   : path to CSV written by crop_and_save.py
    model_path : path to your saved CNN weights (.pt / .pth)
    device     : "cpu" or "cuda"
    skip_done  : if True, skip rows that already have a non-empty label
    batch_size : number of images per GPU forward pass (default 32)

    Returns
    -------
    str  same csv_path (updated in-place)
    """
    model     = _load_model(model_path, device)
    transform = _make_transform()

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total   = len(rows)
    skipped = 0

    # Collect indices that actually need classification
    pending = []
    for i, row in enumerate(rows):
        if skip_done and row.get("label", "").strip():
            skipped += 1
            continue
        if not os.path.isfile(row.get("crop_path", "")):
            print(f"  [{i+1}/{total}] MISSING  {row.get('crop_path')}")
            row["label"]      = "error_missing_crop"
            row["confidence"] = "0.0"
            continue
        pending.append(i)

    if skipped:
        print(f"  Skipping {skipped} already-labelled row(s)")

    # Process in batches
    for batch_start in range(0, len(pending), batch_size):
        batch_indices = pending[batch_start : batch_start + batch_size]
        batch_paths   = [rows[i]["crop_path"] for i in batch_indices]

        results = _predict_batch(model, batch_paths, device, transform)

        for i, (label, confidence) in zip(batch_indices, results):
            rows[i]["label"]      = label
            rows[i]["confidence"] = confidence
            flag = "✓" if confidence >= 0.85 else "?"
            print(f"  [{i+1:>4}/{total}] {flag} "
                  f"{os.path.basename(rows[i]['crop_path']):40s} "
                  f"→ {label:10s}  conf={confidence:.4f}")

        # Save after every batch — crash loses at most batch_size rows
        _write_csv(rows, csv_path)

    print(f"  Labels + confidence written → {csv_path}")
    return csv_path