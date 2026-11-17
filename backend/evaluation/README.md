# Testing and retrieval evaluation

Run the deterministic unit suite from the `backend` directory:

```powershell
..\.venv\Scripts\python.exe -m pytest
```

Run the small BM25 retrieval benchmark from the same directory:

```powershell
..\.venv\Scripts\python.exe -m evaluation.run_retrieval_eval
```

The retrieval cases are manually labeled examples, not a representative production benchmark. There are 17 cases with relevance grades from 1 (somewhat relevant) to 3 (strongly relevant); an empty relevance map means no supported result is expected. The evaluator reports Precision@3, Recall@3, MRR@3, nDCG@3, and abstention accuracy. It makes no network calls.

Run the live routing evaluation only when you want to spend Gemini API quota. It makes one routing call per case (currently six):

```powershell
..\.venv\Scripts\python.exe -m evaluation.run_routing_eval
```

The routing cases are also a small manually labeled smoke set, not a production quality estimate. This checks route selection only; it does not evaluate response grounding or weather API behavior.

Precision@3 uses three as the denominator, so returning fewer than three results lowers the score. nDCG uses graded labels and evaluates ranking order. Both are only meaningful relative to the current hand-labeled cases; use them as regression signals, not a production quality claim. Update the labels when the curated dataset or intended product behavior changes.
