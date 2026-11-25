import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

from app.domain.errors import RuleViolationError
from app.ports.images import ImageUpload

UPLOAD_TTL = timedelta(minutes=5)
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(UTC)


class BlobImageStore:
    def __init__(
        self,
        connection_string: str,
        images_container_url: str,
        now: Callable[[], datetime] = now_utc,
        service_client: BlobServiceClient | None = None,
    ) -> None:
        if not images_container_url:
            raise ValueError("PDC_IMAGES_CONTAINER_URL is required")
        settings = dict(part.split("=", 1) for part in connection_string.split(";") if "=" in part)
        self._account_name = settings["AccountName"]
        self._account_key = settings["AccountKey"]
        self._connection_string = connection_string
        self._container_url = images_container_url.rstrip("/")
        self._container_name = urlsplit(self._container_url).path.rsplit("/", 1)[-1]
        self._now = now
        self._service_client = service_client

    def create_upload(self, product_id: str, content_type: str) -> ImageUpload:
        extension = EXTENSIONS.get(content_type)
        if extension is None:
            raise RuleViolationError(f"Unsupported image type: {content_type}")
        blob_name = f"products/{product_id}/{uuid4()}.{extension}"
        expires_at = self._now() + UPLOAD_TTL
        sas = generate_blob_sas(
            account_name=self._account_name,
            container_name=self._container_name,
            blob_name=blob_name,
            account_key=self._account_key,
            permission=BlobSasPermissions(create=True, write=True),
            expiry=expires_at,
            protocol="https",
        )
        image_url = f"{self._container_url}/{blob_name}"
        return ImageUpload(f"{image_url}?{sas}", image_url, expires_at)

    def delete_product_images(self, product_id: str) -> None:
        try:
            if self._service_client is None:
                self._service_client = BlobServiceClient.from_connection_string(
                    self._connection_string
                )
            container = self._service_client.get_container_client(self._container_name)
            for blob in container.list_blobs(name_starts_with=f"products/{product_id}/"):
                container.delete_blob(blob.name)
        except Exception as error:
            # Type only: storage errors can echo request details.
            logger.warning("Image cleanup failed for %s: %s", product_id, type(error).__name__)
