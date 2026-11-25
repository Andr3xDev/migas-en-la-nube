from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

MAX_ITEM_QUANTITY = 50
MAX_ORDER_ITEMS = 20
MAX_CUSTOMER_NAME_LENGTH = 100
MAX_PHONE_LENGTH = 30
MAX_PRICE = 10_000_000
MAX_STOCK = 10_000
MAX_PREP_MINUTES = 24 * 60


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


Email = Annotated[str, StringConstraints(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Password = Annotated[str, StringConstraints(min_length=8, max_length=1024)]


class Credentials(CamelModel):
    email: Email
    password: Password


class UserResponse(CamelModel):
    id: str
    email: str
    role: str


class TokenResponse(CamelModel):
    access_token: str


class AvailabilityResponse(CamelModel):
    status: str
    ready_minutes: int | None


class VariantResponse(CamelModel):
    name: str
    price: int
    stock: int
    availability: AvailabilityResponse


class ProductResponse(CamelModel):
    id: str
    name: str
    category: str
    description: str
    image_url: str | None
    prep_minutes: int
    variants: list[VariantResponse]


class OrderItemRequest(CamelModel):
    product_id: str
    variant_name: str
    quantity: int = Field(ge=1, le=MAX_ITEM_QUANTITY)


class OrderRequest(CamelModel):
    customer_name: RequiredText = Field(max_length=MAX_CUSTOMER_NAME_LENGTH)
    phone: RequiredText = Field(max_length=MAX_PHONE_LENGTH)
    pickup_time: datetime
    items: list[OrderItemRequest] = Field(min_length=1, max_length=MAX_ORDER_ITEMS)


class OrderItemResponse(CamelModel):
    product_id: str
    product_name: str
    variant_name: str
    unit_price: int
    quantity: int


class OrderResponse(CamelModel):
    code: str
    status: str
    items: list[OrderItemResponse]
    total: int
    pickup_time: datetime


class VariantRequest(CamelModel):
    name: RequiredText
    price: int = Field(le=MAX_PRICE)
    stock: int = Field(le=MAX_STOCK)


class ProductRequest(CamelModel):
    name: RequiredText
    category: RequiredText
    description: str
    image_url: str | None
    prep_minutes: int = Field(le=MAX_PREP_MINUTES)
    variants: list[VariantRequest]


class ImageUploadRequest(CamelModel):
    content_type: str


class ImageUploadResponse(CamelModel):
    upload_url: str
    image_url: str
    expires_at: datetime


class StatusRequest(CamelModel):
    status: str


class AdminOrderResponse(OrderResponse):
    customer_name: str
    phone: str
