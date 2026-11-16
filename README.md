# tripPartner

A context-aware AI trip concierge for Meghalaya. The MVP demonstrates grounded local recommendations, explicit tool routing, and weather-triggered itinerary adaptation.

## First vertical slice

1. Load a fictional booking and build a typed trip context.
2. Retrieve relevant, sourced places from a small curated Meghalaya dataset.
3. Use a LangGraph workflow to choose local retrieval, a weather lookup, or a clarification question.
4. Generate a day plan from retrieved candidates and require guest approval before saving changes.
5. Simulate a weather-change event and suggest a sourced alternative when an outdoor itinerary item is affected.
6. Evaluate retrieval quality, source correctness, and workflow/tool selection on fixed scenarios.

The initial demo uses a manual weather event endpoint. A background scheduler, booking integration, WhatsApp, and live notification delivery are deferred until the core flow is working.

## Current implementation

The FastAPI backend provides:

- `GET /health`: process health check.
- `GET /demo/trip-context`: loads fictional booking, preference, property, and itinerary data and validates it as `TripContext`.
- `GET /places`: lists curated, source-attributed recommendations.
- `GET /recommendations/search`: BM25 lexical search with optional `area`, `category`, and `setting` filters. Results include source metadata, matched query terms, a score, and a fallback response when evidence is weak.

The schemas omit guest name, phone, and real booking data. The search baseline is intentionally lexical; embeddings and agent routing come after we measure this baseline on a fixed set of realistic queries.

## Run locally

Activate the existing virtual environment, then run these commands from `backend`:

```powershell
python -m pip install -r ..\requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. Do not paste or commit secret values from `.env`.
