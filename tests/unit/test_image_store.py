import base64
import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from app.adapters.blob.images import BlobImageStore
from app.domain.errors import RuleViolationError

ACCOUNT = "migasdev"
CONTAINER_URL = f"https://{ACCOUNT}.blob.core.windows.net/images"
CONNECTION_STRING = (
    "DefaultEndpointsProtocol=https;"
    f"AccountName={ACCOUNT};"
    f"AccountKey={base64.b64encode(b'fake-account-key').decode()};"
    "EndpointSuffix=core.windows.net"
)
NOW = datetime(2026, 11, 25, 12, 0, 0, tzinfo=UTC)


class FakeContainerClient:
    def __init__(self, names=(), list_error=None, delete_error=None):
        self.names = list(names)
        self.list_error = list_error
        self.delete_error = delete_error
        self.prefixes: list[str] = []
        self.deleted: list[str] = []

    def list_blobs(self, name_starts_with=None):
        self.prefixes.append(name_starts_with)
        if self.list_error:
            raise self.list_error
        return [SimpleNamespace(name=name) for name in self.names]

    def delete_blob(self, name):
        if self.delete_error:
            raise self.delete_error
        self.deleted.append(name)


class FakeServiceClient:
    def __init__(self, container: FakeContainerClient):
        self.container = container

    def get_container_client(self, name):
        assert name == "images"
        return self.container


def make_store(container: FakeContainerClient | None = None) -> BlobImageStore:
    return BlobImageStore(
        CONNECTION_STRING,
        CONTAINER_URL,
        now=lambda: NOW,
        service_client=FakeServiceClient(container or FakeContainerClient()),
    )


def test_create_upload_signs_five_minute_create_write_sas():
    upload = make_store().create_upload("croissant", "image/png")

    query = parse_qs(urlsplit(upload.upload_url).query)
    assert query["sp"] == ["cw"]
    assert query["se"] == ["2026-11-25T12:05:00Z"]
    assert query["spr"] == ["https"]
    assert upload.expires_at == NOW + timedelta(minutes=5)


def test_create_upload_returns_public_blob_url_under_product_prefix():
    upload = make_store().create_upload("croissant", "image/png")

    assert re.fullmatch(rf"{CONTAINER_URL}/products/croissant/[^/]+\.png", upload.image_url)
    assert upload.upload_url.startswith(f"{upload.image_url}?")


@pytest.mark.parametrize(
    ("content_type", "extension"),
    [("image/jpeg", "jpg"), ("image/png", "png"), ("image/webp", "webp")],
)
def test_create_upload_maps_content_type_to_extension(content_type, extension):
    assert make_store().create_upload("p", content_type).image_url.endswith(f".{extension}")


def test_create_upload_rejects_unsupported_content_type():
    with pytest.raises(RuleViolationError):
        make_store().create_upload("croissant", "image/gif")


def test_delete_product_images_deletes_every_blob_under_product_prefix():
    container = FakeContainerClient(names=["products/p1/a.png", "products/p1/b.jpg"])

    make_store(container).delete_product_images("p1")

    assert container.prefixes == ["products/p1/"]
    assert container.deleted == ["products/p1/a.png", "products/p1/b.jpg"]


@pytest.mark.parametrize(
    "make_container",
    [
        lambda: FakeContainerClient(list_error=RuntimeError("storage down")),
        lambda: FakeContainerClient(names=["products/p1/a.png"], delete_error=RuntimeError("gone")),
    ],
    ids=["list", "delete"],
)
def test_delete_product_images_propagates_storage_failures(make_container):
    with pytest.raises(RuntimeError):
        make_store(make_container()).delete_product_images("p1")
