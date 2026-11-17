"""Small SQLite store for the demo trip and weather-event approvals."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.schemas.trip_context import TripContext

DATABASE_PATH = Path(__file__).parents[1] / "data" / "trip_partner.sqlite3"


class TripStore:
    """Persist demo trip changes and approval decisions between API requests."""

    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS trips (
                trip_id TEXT PRIMARY KEY,
                context_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS weather_events (
                event_id TEXT PRIMARY KEY,
                trip_id TEXT NOT NULL,
                response_json TEXT NOT NULL,
                approval_status TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            );
            """
        )
        return connection

    def get_trip_context(self, seed_context: TripContext) -> TripContext:
        """Seed from the checked-in demo JSON once, then return persisted state."""
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO trips (trip_id, context_json) VALUES (?, ?)",
                (
                    seed_context.trip_id,
                    seed_context.model_dump_json(),
                ),
            )
            row = connection.execute(
                "SELECT context_json FROM trips WHERE trip_id = ?",
                (seed_context.trip_id,),
            ).fetchone()
        return TripContext.model_validate_json(row["context_json"])

    def save_weather_event(self, event_id: str, trip_id: str, response: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO weather_events
                   (event_id, trip_id, response_json, approval_status)
                   VALUES (?, ?, ?, ?)""",
                (
                    event_id,
                    trip_id,
                    json.dumps(response),
                    "pending" if response.get("requires_guest_approval") else None,
                ),
            )

    def decide_weather_event(self, event_id: str, decision: str) -> dict[str, Any] | None:
        """Record a one-time decision; apply approved replacement atomically."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            event_row = connection.execute(
                "SELECT * FROM weather_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            if event_row is None:
                connection.rollback()
                return None
            if event_row["approval_status"] != "pending":
                connection.rollback()
                raise ValueError("This weather suggestion has already been decided.")

            response = json.loads(event_row["response_json"])
            approval_status = "approved" if decision == "approve" else "rejected"
            if decision == "approve":
                trip_row = connection.execute(
                    "SELECT context_json FROM trips WHERE trip_id = ?",
                    (event_row["trip_id"],),
                ).fetchone()
                context = json.loads(trip_row["context_json"])
                target_ids = set(response.get("affected_item_ids", []))
                alternative = response.get("suggested_alternative") or {}
                for item in context.get("itinerary", []):
                    if item.get("item_id") in target_ids:
                        item.update(
                            {
                                "title": alternative.get("title", item["title"]),
                                "place_id": alternative.get("place_id", item.get("place_id")),
                                "area": alternative.get("area", item["area"]),
                                "category": "cave",
                                "setting": alternative.get("setting", "mixed"),
                            }
                        )
                connection.execute(
                    "UPDATE trips SET context_json = ? WHERE trip_id = ?",
                    (json.dumps(context), event_row["trip_id"]),
                )

            response["approval_status"] = approval_status
            response["requires_guest_approval"] = False
            response["message"] += (
                " The suggested change was approved and added to the itinerary."
                if decision == "approve"
                else " The suggested change was declined; the itinerary is unchanged."
            )
            connection.execute(
                "UPDATE weather_events SET response_json = ?, approval_status = ? WHERE event_id = ?",
                (json.dumps(response), approval_status, event_id),
            )
            connection.commit()
            return response


trip_store = TripStore()
