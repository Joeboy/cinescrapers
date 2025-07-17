from pathlib import Path
from PIL import Image
from cinescrapers.utils import smart_square_thumbnail


def test_smart_square_thumbnail():
    """This only tests the YOLO path (and only tests that it creates some sort of image)"""
    input_path = Path(__file__).parent / "test_input_image.jpg"
    output_path = Path(__file__).parent / "test_output_thumbnail.jpg"
    output_path.unlink(missing_ok=True)  # Remove if it exists

    size = 300
    smart_square_thumbnail(input_path, output_path, size=size)

    assert output_path.exists()

    # Check dimensions
    with Image.open(output_path) as img:
        assert img.size == (size, size)
