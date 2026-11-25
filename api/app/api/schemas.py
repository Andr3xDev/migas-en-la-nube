from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


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
