# tripPartner

A context-aware AI trip concierge for Meghalaya. The MVP demonstrates grounded local recommendations, explicit tool routing, and weather-triggered itinerary adaptation.

## Current backend flow

1. `POST /assistant/chat` loads the fictional trip context and sends it with the guest message to LangGraph.
2. A Gemini structured-output router chooses recommendation, itinerary, weather, or clarification.
3. Recommendation and itinerary requests go through the BM25 local search service with metadata filters.
4. Weather questions use the Open-Meteo geocoding and forecast APIs; Gemini summarizes the normalized forecast.
5. `POST /events/weather-change` accepts a forecast-change event. Deterministic rules check whether rain risk rose enough and an outdoor itinerary item is scheduled for that date.
6. Only an impactful event searches for an unscheduled local cave alternative and calls Gemini to draft an approval-gated suggestion.
7. The demo trip and weather suggestions are stored in a local SQLite database. A guest can approve or reject a suggestion; approval updates the persisted itinerary, while rejection leaves it unchanged.

The weather-change endpoint is a manually triggered event simulation; no scheduler or forecast monitor emits events yet. Open-Meteo free use is non-commercial and requires attribution.

## API endpoints

- `GET /health`: process health check.
- `GET /demo/trip-context`: validated fictional booking and itinerary context.
- `GET /places`: curated, source-attributed local records.
- `GET /recommendations/search`: BM25 search with optional area, category, and setting filters.
- `GET /weather/forecast`: normalized Open-Meteo forecast; defaults to the demo property's area.
- `POST /assistant/chat`: LangGraph routing and grounded response workflow.
- `POST /events/weather-change`: evaluate an event and return a persisted suggestion with an `event_id`.
- `POST /events/weather-change/{event_id}/decision`: approve or reject a pending suggestion.

Example simulated event for the demo's outdoor Nohkalikai visit:

```json
{
  "trip_id": "trip-demo-001",
  "forecast_date": "2027-01-16",
  "previous_precipitation_probability": 20,
  "current_precipitation_probability": 85,
  "area": "Sohra",
  "event_source": "simulated"
}
```

The demo trigger requires current precipitation probability of at least 60% and an increase of at least 20 percentage points. These are explicit prototype rules, not weather-safety guarantees. Suggestions remain pending until explicitly approved or rejected. The demo database is `backend/app/data/trip_partner.sqlite3`; deleting that file resets the persisted demo trip to the checked-in JSON seed.

After creating a suggestion, use its returned `event_id` to decide it:

```json
{"decision": "approve"}
```

Send that body to `POST /events/weather-change/{event_id}/decision`. Use `{"decision":"reject"}` to decline it. Read `GET /demo/trip-context` to see the persisted itinerary after approval.

## Run locally

Activate the existing virtual environment and install dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set `GOOGLE_API_KEY` in the local `.env` file for Gemini. Optionally set `GEMINI_MODEL`; the default is `gemini-3.6-flash`. Open-Meteo requires no key for this non-commercial prototype. Never paste or commit secret values.

Run from the `backend` directory:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API docs.
