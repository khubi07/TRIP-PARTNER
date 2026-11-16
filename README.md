# tripPartner

A context-aware AI trip concierge for Meghalaya. The MVP demonstrates grounded local recommendations, explicit tool routing, and weather-triggered itinerary adaptation.

## Current backend flow

1. `POST /assistant/chat` loads the fictional trip context and sends it with the guest message to the LangGraph workflow.
2. A Gemini structured-output router chooses recommendation, itinerary, weather, or clarification.
3. Recommendation and itinerary requests go through the BM25 local search service with metadata filters.
4. Gemini drafts a response from the retrieved candidates. Source URLs are attached from the dataset, and generated citation IDs are restricted to retrieved place IDs.
5. Weak retrieval returns a refinement prompt instead of asking Gemini to invent a place.

The live weather route is deliberately a placeholder at this stage; the next tool integration will connect an actual forecast source. No booking integration, scheduler, WhatsApp, or delivery system is included yet.

## API endpoints

- `GET /health`: process health check.
- `GET /demo/trip-context`: validated fictional booking and itinerary context.
- `GET /places`: curated, source-attributed local records.
- `GET /recommendations/search`: BM25 search with optional area, category, and setting filters.
- `POST /assistant/chat`: LangGraph routing and grounded response workflow.

## Run locally

Activate the existing virtual environment and install dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set `GOOGLE_API_KEY` in the local `.env` file. Optionally set `GEMINI_MODEL`; the default is `gemini-3.6-flash`. Never paste or commit secret values.

Run from the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API docs. Try `POST /assistant/chat` with a JSON body such as `{"message":"Suggest a cave near me"}`.
