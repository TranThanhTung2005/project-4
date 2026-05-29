from pathlib import Path
import re
import unicodedata

from werkzeug.utils import secure_filename


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_DIR = Path(__file__).resolve().parent.parent / "g6images"


def normalize_filename_stem(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", ascii_text).strip("-")
    return stem or "product-image"


def save_product_image(file_storage, sku=None):
    if not file_storage or not file_storage.filename:
        return None

    original_name = secure_filename(file_storage.filename)
    extension = Path(original_name).suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        raise ValueError("Chỉ nhận file ảnh .jpg, .jpeg, .png, .webp hoặc .gif.")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    base_name = normalize_filename_stem(sku) if sku else normalize_filename_stem(Path(original_name).stem)
    filename = f"{base_name}{extension}"
    target = IMAGE_DIR / filename
    counter = 2
    while target.exists():
        filename = f"{base_name}-{counter}{extension}"
        target = IMAGE_DIR / filename
        counter += 1

    file_storage.save(target)
    return f"/images/{filename}"
