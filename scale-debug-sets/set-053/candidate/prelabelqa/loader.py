import csv
import json
from dataclasses import dataclass

from .geometry import Box, from_xywh

COORDS = ("x_min", "y_min", "x_max", "y_max")


@dataclass
class Image:
    image_id: str
    dataset: str
    width: int
    height: int


def clean(value):
    return str(value if value is not None else "").strip()


def norm_image(value):
    return clean(value).lower()


def norm_box_id(value):
    return clean(value).upper() or None


def norm_label(value):
    return clean(value).lower()


def parse_coord(value):
    text = clean(value)
    return float(text) if text else None


def load_images(path):
    images = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            image = Image(norm_image(row["image_id"]), norm_label(row["dataset"]),
                          int(clean(row["width"])), int(clean(row["height"])))
            images[image.image_id] = image
    return images


def load_prelabels(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [from_xywh(norm_image(item["image"]), norm_box_id(item["box_id"]),
                      norm_label(item["label"]), item["bbox"]) for item in raw]


def load_reviews(path):
    reviews = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            coords = [parse_coord(row[k]) for k in COORDS]
            if not all(coords):
                continue
            reviews.append(Box(norm_image(row["image"]), norm_box_id(row["box_id"]),
                               norm_label(row["label"]), *coords))
    return reviews
