from datetime import datetime
from uuid import uuid4

from app.ports.images import UPLOAD_TTL, ImageUpload


class MemoryImageStore:
    """Local stand-in: hands out URLs but stores nothing."""

    def __init__(self, images_container_url: str) -> None:
        self._container_url = images_container_url.rstrip("/")

    def create_upload(self, product_id: str, content_type: str) -> ImageUpload:
        image_url = f"{self._container_url}/products/{product_id}/{uuid4()}"
        return ImageUpload(image_url, image_url, datetime.now().astimezone() + UPLOAD_TTL)

    def delete_product_images(self, product_id: str) -> None:
        pass
