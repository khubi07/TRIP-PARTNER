import json
from pathlib import Path

import pytest

from app.schemas.trip_context import TripContext


DATA_DIR = Path(__file__).parents[1] / "app" / "data"


@pytest.fixture
def demo_trip_context():
    raw_context = json.loads((DATA_DIR / "demo_trip_context.json").read_text(encoding="utf-8"))
    return TripContext.model_validate(raw_context).model_dump(mode="json")
