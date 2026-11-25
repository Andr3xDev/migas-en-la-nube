from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class ImageUpload:
    upload_url: str
    image_url: str
    expires_at: datetime


class ImageStore(Protocol):
    def create_upload(self, product_id: str, content_type: str) -> ImageUpload: ...

    def delete_product_images(self, product_id: str) -> None: ...
