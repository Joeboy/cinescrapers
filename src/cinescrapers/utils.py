import datetime
from os import PathLike

import cv2
import dateparser
import numpy as np
from PIL import Image
from ultralytics import YOLO


class DateParsingError(Exception):
    pass


def parse_date_without_year(date_str: str) -> datetime.datetime | None:
    """If eg. date_str eg. "February 12th" and it's now October, assume the
    date is next year"""
    now = datetime.datetime.now()
    date = dateparser.parse(date_str)
    if date is None:
        raise DateParsingError()
    if now.month > 6 and date.month < 3:
        date = date.replace(year=1 + now.year)
    return date


haar_filename = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"  # type: ignore
face_cascade = cv2.CascadeClassifier(haar_filename)
yolo_model = YOLO("yolov8n.pt")


def smart_square_thumbnail(
    input_path: str | PathLike, output_path: str | PathLike, size: int
):
    """Try to create a sensibly cropped square thumbnail from an image"""
    pil_img = Image.open(input_path).convert("RGB")
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    height, width = cv_img.shape[:2]

    # --- 1. Try YOLO detection ---
    try:
        results = yolo_model(pil_img)
        boxes = results[0].boxes.xyxy.cpu().numpy()
        if len(boxes) > 0:
            x1, y1, x2, y2 = boxes[0]
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
        else:
            raise ValueError("No YOLO detection")
    except Exception:
        import traceback

        traceback.print_exc()
        # --- 2. Try OpenCV face detection ---
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) > 0:
            x, y, fw, fh = faces[0]
            cx = x + fw // 2
            cy = y + fh // 2
        else:
            # --- 3. Fallback to image center ---
            cx, cy = width // 2, height // 2

    # --- Calculate square crop ---
    crop_size = min(width, height)
    half = crop_size // 2
    left = max(0, cx - half)
    top = max(0, cy - half)
    right = min(width, cx + half)
    bottom = min(height, cy + half)

    cropped = pil_img.crop((left, top, right, bottom))
    cropped = cropped.resize((size, size), Image.LANCZOS)  # type: ignore
    cropped.save(output_path)

    print(f"Saved smart thumbnail to: {output_path}")
