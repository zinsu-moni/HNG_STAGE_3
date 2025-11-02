"""Quick verification script to check if the server is responding correctly."""
import httpx
import sys


def check_health(base_url):
    """Check the health endpoint."""
    try:
        resp = httpx.get(f"{base_url}/", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed with status {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def check_jsonrpc(base_url):
    """Check the JSON-RPC endpoint with A2A protocol."""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "verify-123",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Quick test"}],
                    "messageId": "verify-msg"
                },
                "configuration": {
                    "acceptedOutputModes": ["text/plain"],
                    "historyLength": 0,
                    "blocking": False
                }
            }
        }
        
        resp = httpx.post(f"{base_url}/jsonrpc", json=payload, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data and "outputs" in data["result"]:
                outputs = data["result"]["outputs"]
                print(f"✅ JSON-RPC check passed: Received {len(outputs)} outputs")
                return True
        print(f"❌ JSON-RPC check failed with status {resp.status_code}")
        print(f"Response: {resp.text}")
        return False
    except Exception as e:
        print(f"❌ JSON-RPC check error: {e}")
        return False


if __name__ == "__main__":
    # Use provided URL or default to local
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    
    print(f"🔍 Verifying server at: {base_url}")
    print("=" * 60)
    
    health_ok = check_health(base_url)
    jsonrpc_ok = check_jsonrpc(base_url)
    
    print("=" * 60)
    if health_ok and jsonrpc_ok:
        print("✅ All checks passed! Server is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please review the errors above.")
        sys.exit(1)
