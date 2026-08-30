#!/usr/bin/env python3
"""Count people in an image using the locally cached BLIP model.

Usage:
    python count_people.py <image_path>

This uses BLIP image captioning (large) from the local HF cache.
Since it's a captioning model (not VQA), it generates a description
and parses person-words from the caption.
"""

import sys
import re
from pathlib import Path

import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

MODEL_DIR = Path.home() / ".cache/huggingface/hub/models--Salesforce--blip-image-captioning-large/snapshots/353689b859fcf0523410b1806dace5fb46ecdf41"

PERSON_WORDS = [
    "person", "people", "man", "men", "woman", "women",
    "boy", "girl", "child", "children", "pedestrian",
    "crowd", "group", "family", "couple",
]


def count_people(image_path: str) -> None:
    image = Image.open(image_path).convert("RGB")

    processor = BlipProcessor.from_pretrained(str(MODEL_DIR))
    model = BlipForConditionalGeneration.from_pretrained(str(MODEL_DIR))

    # Generate a detailed caption with beam search
    inputs = processor(image, return_tensors="pt")
    out = model.generate(
        **inputs,
        max_length=128,
        num_beams=5,
        no_repeat_ngram_size=2,
    )
    caption = processor.decode(out[0], skip_special_tokens=True)

    print(f"Image: {image_path}")
    print(f"Caption: {caption}")

    # Count person-related words in caption
    caption_lower = caption.lower()
    matches = {w: caption_lower.count(w) for w in PERSON_WORDS if caption_lower.count(w) > 0}
    total = sum(matches.values())

    if matches:
        print(f"Person words found: {matches}")
    print(f"People count: {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_people.py <image_path>", file=sys.stderr)
        sys.exit(1)
    count_people(sys.argv[1])
