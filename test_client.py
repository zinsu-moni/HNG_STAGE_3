"""Simple test client for the JSON-RPC motivate method.

Run the server first (e.g. `uvicorn main:app --reload`) then run this file.
"""
import httpx


def run_test():
    url = "http://127.0.0.1:8000/jsonrpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "motivate",
        "params": {"input": "I'm feeling stuck and a bit tired with my work"},
        "id": 1,
    }

    resp = httpx.post(url, json=payload, timeout=10.0)
    try:
        data = resp.json()
    except Exception:
        print("Non-JSON response:", resp.text)
        raise

    print("Response status:", resp.status_code)
    print("Response JSON:\n", data)

    if "result" not in data:
        raise AssertionError("Expected 'result' in JSON-RPC response")

    result = data["result"]
    motivations = result.get("motivations") if isinstance(result, dict) else None
    if not motivations:
        raise AssertionError("No motivations returned")

    print("\nMotivations:")
    for i, m in enumerate(motivations, start=1):
        print(f"{i}. {m}")


if __name__ == "__main__":
    run_test()
