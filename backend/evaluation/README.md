# Testing and retrieval evaluation

Run the deterministic unit suite from the `backend` directory:

```powershell
..\.venv\Scripts\python.exe -m pytest
```

Run the small BM25 retrieval benchmark from the same directory:

```powershell
..\.venv\Scripts\python.exe -m evaluation.run_retrieval_eval
```

The retrieval cases are manually labeled examples, not a representative production benchmark. The evaluator reports Precision@3, Recall@3, MRR@3, and whether the system correctly abstains on an unsupported query. It makes no network calls.

Run the live routing evaluation only when you want to spend Gemini API quota. It makes one routing call per case (currently six):

```powershell
..\.venv\Scripts\python.exe -m evaluation.run_routing_eval
```

The routing cases are also a small manually labeled smoke set, not a production quality estimate. This checks route selection only; it does not evaluate response grounding or weather API behavior.

The retrieval benchmark currently has perfect recall and MRR because each expected result appears in the top three. Precision@3 is lower because several queries return fewer than three results, with missing slots counted as non-relevant; this is a tiny curated dataset, so treat the figures as a baseline for regression checks rather than a quality claim.
