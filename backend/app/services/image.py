import hashlib
import io
from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageOps

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
MAX_PIXELS = 25_000_000  # 25 MP limit for decompression bomb defense
MIN_DIMENSION = 100
MAX_DIMENSION = 10_000

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class ImageValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ImageMetadata:
    width: int
    height: int
    orientation: int
    format: str
    mime_type: str
    sha256: str
    normalized_bytes: bytes


def validate_and_process_image(data: bytes, expected_content_type: str) -> ImageMetadata:
    if not data:
        raise ImageValidationError("empty_file", "The uploaded file is empty")

    sha256_hash = hashlib.sha256(data).hexdigest()

    # 1. Magic bytes validation
    if expected_content_type == "image/png":
        if not data.startswith(PNG_MAGIC):
            raise ImageValidationError("invalid_magic_bytes", "File does not match PNG signature")
    elif expected_content_type == "image/jpeg":
        if not data.startswith(JPEG_MAGIC):
            raise ImageValidationError("invalid_magic_bytes", "File does not match JPEG signature")
    else:
        raise ImageValidationError("unsupported_mime_type", f"Unsupported content type: {expected_content_type}")

    # 2. PIL decoding & decompression bomb prevention
    try:
        with Image.open(io.BytesIO(data)) as img:
            img_format = img.format
            if expected_content_type == "image/png" and img_format != "PNG":
                raise ImageValidationError("format_mismatch", "Declared PNG but decoded format differs")
            if expected_content_type == "image/jpeg" and img_format != "JPEG":
                raise ImageValidationError("format_mismatch", "Declared JPEG but decoded format differs")

            # Check EXIF orientation
            orientation = 1
            exif = img.getexif()
            if exif:
                orientation = exif.get(0x0112, 1)

            # Transpose orientation if needed to align geometry
            transposed = ImageOps.exif_transpose(img)
            width, height = transposed.size

            if width < MIN_DIMENSION or height < MIN_DIMENSION:
                raise ImageValidationError(
                    "image_too_small",
                    f"Image dimensions ({width}x{height}) must be at least {MIN_DIMENSION}x{MIN_DIMENSION}px",
                )
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise ImageValidationError(
                    "image_too_large",
                    f"Image dimensions ({width}x{height}) exceed maximum allowed {MAX_DIMENSION}x{MAX_DIMENSION}px",
                )

            # If transposed changed orientation, export normalized bytes
            if orientation != 1:
                buffer = io.BytesIO()
                transposed.save(buffer, format=img_format)
                normalized_bytes = buffer.getvalue()
            else:
                normalized_bytes = data

            return ImageMetadata(
                width=width,
                height=height,
                orientation=orientation,
                format=img_format or "PNG",
                mime_type=expected_content_type,
                sha256=sha256_hash,
                normalized_bytes=normalized_bytes,
            )
    except Image.DecompressionBombError as error:
        raise ImageValidationError("decompression_bomb", "Image pixel count exceeds safe processing limit") from error
    except ImageValidationError:
        raise
    except Exception as error:
        raise ImageValidationError("corrupt_image", f"Failed to decode image: {error}") from error
