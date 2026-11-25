import json
from pathlib import Path

from app.api.deps import get_product_repository
from app.core.settings import get_settings
from app.domain.models import Product, Variant
from app.services.catalog import seed_products

SEED_FILE = Path(__file__).with_name("products_seed.json")


def load_products(path: Path = SEED_FILE) -> list[Product]:
    return [
        Product(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            description=item["description"],
            image_url=item["imageUrl"],
            prep_minutes=item["prepMinutes"],
            variants=[Variant(**variant) for variant in item["variants"]],
        )
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]


if __name__ == "__main__":
    if not get_settings().cosmos_connection_string:
        raise SystemExit("PDC_COSMOS_CONNECTION_STRING is required")
    seed_products(get_product_repository(), load_products())
