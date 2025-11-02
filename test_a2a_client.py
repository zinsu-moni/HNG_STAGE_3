"""Test client for A2A protocol message/send method."""
import httpx
import json


def test_a2a_protocol():
    """Test the A2A protocol format with message/send method."""
    url = "http://127.0.0.1:8000/jsonrpc"
    
    # A2A protocol format
    payload = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Give me motivation to pass my exam"
                    }
                ],
                "messageId": "test-message-id"
            },
            "configuration": {
                "acceptedOutputModes": ["text/plain"],
                "historyLength": 0,
                "blocking": False
            }
        }
    }

    print("Sending A2A protocol request...")
    print(f"Request: {json.dumps(payload, indent=2)}\n")

    resp = httpx.post(url, json=payload, timeout=10.0)
    
    print(f"Response status: {resp.status_code}")
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2)}\n")

    if "result" in data:
        result = data["result"]
        outputs = result.get("outputs", [])
        print(f"✅ Success! Received {len(outputs)} motivational outputs:\n")
        for i, output in enumerate(outputs, 1):
            if output.get("kind") == "text":
                print(f"{i}. {output.get('text')}\n")
    else:
        print(f"❌ Error: {data}")


def test_simple_motivate():
    """Test the backward-compatible 'motivate' method."""
    url = "http://127.0.0.1:8000/jsonrpc"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "motivate",
        "params": {"input": "I'm feeling stressed about work"},
        "id": 1,
    }

    print("\n" + "="*60)
    print("Testing backward-compatible 'motivate' method...")
    print("="*60 + "\n")

    resp = httpx.post(url, json=payload, timeout=10.0)
    data = resp.json()
    
    print(f"Response status: {resp.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}\n")

    if "result" in data:
        motivations = data["result"].get("motivations", [])
        print(f"✅ Success! Received {len(motivations)} motivations:\n")
        for i, m in enumerate(motivations, 1):
            print(f"{i}. {m}\n")


if __name__ == "__main__":
    print("="*60)
    print("A2A Protocol Test Suite")
    print("="*60 + "\n")
    
    try:
        test_a2a_protocol()
        test_simple_motivate()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
