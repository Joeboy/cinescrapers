import datetime
import functools
from os import PathLike

import cv2
import dateparser
import numpy as np
from PIL import Image


class DateParsingError(Exception):
    pass


class ImageCentreNotFound(Exception):
    "Failed to (smartly) detect the image centre point"

    pass


def parse_date_without_year(date_str: str) -> datetime.datetime:
    """If eg. date_str eg. "February 12th" and it's now October, assume the
    date is next year"""
    now = datetime.datetime.now()
    date = dateparser.parse(date_str)
    if date is None:
        raise DateParsingError()
    if now.month > 6 and date.month < 3:
        date = date.replace(year=1 + now.year)
    return date


@functools.lru_cache(maxsize=1)
def get_face_cascade():
    haar_filename = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"  # type: ignore
    return cv2.CascadeClassifier(haar_filename)


@functools.lru_cache(maxsize=1)
def get_yolo_model():
    from ultralytics import YOLO

    return YOLO("yolov8n.pt")


def get_yolo_centre(pil_img: Image.Image) -> tuple[int, int]:
    """Look for a good image centre to use when cropping the image to a square,
    using YOLO model"""
    yolo_model = get_yolo_model()
    results = yolo_model(pil_img)
    boxes = results[0].boxes.xyxy.cpu().numpy()
    print(f"Found {len(boxes)} boxes with YOLO")
    if len(boxes) > 0:
        # Just use the first box, which is expected to have the highest confidence
        x1, y1, x2, y2 = boxes[0]
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return cx, cy
    raise ImageCentreNotFound()


def get_facial_centre(cv_img) -> tuple[int, int]:
    """Look for a good image centre to use when cropping the image to a square,
    using OpenCV Face detection"""
    face_cascade = get_face_cascade()
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) > 0:
        x, y, fw, fh = faces[0]
        cx = x + fw // 2
        cy = y + fh // 2
        return cx, cy
    raise ImageCentreNotFound()


def smart_square_thumbnail(
    input_path: str | PathLike, output_path: str | PathLike, size: int
):
    """Try to create a sensibly cropped square thumbnail from an image"""
    pil_img = Image.open(input_path).convert("RGB")
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    height, width = cv_img.shape[:2]

    try:
        cx, cy = get_yolo_centre(pil_img)
        method = "yolo"
    except ImageCentreNotFound:
        try:
            # It seems like this rarely gets a result where yolo fails.
            cx, cy = get_facial_centre(cv_img)
            method = "facial"
        except ImageCentreNotFound:
            # Fallback to image centre
            cx, cy = width // 2, height // 2
            method = "centre"

    # Calculate square crop size (largest possible square that fits in the image)
    crop_size = min(width, height)
    half = crop_size // 2

    # Constrain the center to ensure we can crop a full square
    cx = max(half, min(width - half, cx))
    cy = max(half, min(height - half, cy))

    # Now crop the square
    left = cx - half
    top = cy - half
    right = cx + half
    bottom = cy + half

    cropped = pil_img.crop((left, top, right, bottom))
    cropped = cropped.resize((size, size), Image.LANCZOS)  # type: ignore
    cropped.save(output_path)

    print(f"Saved smart thumbnail to: {output_path} ({method})")
