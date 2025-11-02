# A2A JSON-RPC Motivation Agent

This small project implements a JSON-RPC 2.0 endpoint that provides motivational suggestions based on user input. It's intentionally minimal so you can adapt it to call any OpenAI-compatible API (such as openrouter.ai) by configuring environment variables.

## Files
- `main.py` — FastAPI app exposing a `POST /jsonrpc` endpoint; supports method `motivate`.
- `agent.py` — Agent logic: rule-based fallback and optional remote model call if `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set.
- `test_client.py` — Simple client to exercise the JSON-RPC `motivate` method.
- `requirements.txt` — Python dependencies.

## JSON-RPC contract
Request example:
```json
{
  "jsonrpc": "2.0",
  "method": "motivate",
  "params": {"input": "I feel stuck and tired"},
  "id": 1
}
```

Response example (happy path):
```json
{
  "jsonrpc": "2.0",
  "result": {
    "motivations": ["...", "...", "..."],
    "source": "local"
  },
  "id": 1
}
```

## Environment variables
- `OPENAI_API_KEY` (optional) — if set, the server will attempt to call the remote model.
- `OPENAI_BASE_URL` (optional) — base URL for the OpenAI-compatible API (for example `https://openrouter.ai/api/v1`).
- `A2A_MODEL` (optional) — model to request, default `gpt-3.5-turbo`.

**Important**: Do NOT commit your API keys to source control. The examples above show environment variable names only; use your own key locally.

## Run locally

1. Create and activate a virtual environment (Windows PowerShell example):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. (Optional) Set environment variables to enable remote model calls:

```powershell
$env:OPENAI_API_KEY="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"
$env:OPENAI_BASE_URL="https://openrouter.ai/api/v1"
```

3. Start the server:

```powershell
uvicorn main:app --reload
```

4. In another terminal, run the test client:

```powershell
python test_client.py
```

Or use curl to call the JSON-RPC endpoint:

```powershell
curl -X POST http://127.0.0.1:8000/jsonrpc -H "Content-Type: application/json" -d '{\"jsonrpc\":\"2.0\",\"method\":\"motivate\",\"params\":{\"input\":\"I'm stuck\"},\"id\":1}'
```

## Extending
- Add authentication, rate-limiting, or a queue for long-running agent tasks.
- Implement more A2A methods (e.g., summarize, plan, critique) and register them in `main.py`.
- Improve remote model parsing and schema enforcement (return strict JSON).

## Notes
- This project intentionally falls back to local rule-based suggestions if a remote model call fails or is not configured.
- The JSON-RPC 2.0 specification is followed for error codes and response structure.
