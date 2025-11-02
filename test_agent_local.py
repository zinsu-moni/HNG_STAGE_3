"""Test the agent locally to verify it's working correctly."""
import httpx
import json
import time

BASE_URL = "http://localhost:8000"

def test_agent(input_text: str):
    """Test the agent with a specific input."""
    print(f"\n{'='*60}")
    print(f"Testing: {input_text}")
    print(f"{'='*60}")
    
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": input_text
                    }
                ],
                "messageId": "test-123"
            },
            "configuration": {
                "blocking": True  # Use blocking mode for easier testing
            }
        },
        "id": 1
    }
    
    start_time = time.time()
    
    try:
        resp = httpx.post(f"{BASE_URL}/jsonrpc", json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Status: {resp.status_code}")
        print(f"⏱️  Response time: {elapsed:.2f}s")
        
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result", {})
            outputs = result.get("outputs", [])
            
            print(f"\n📝 Generated {len(outputs)} motivations:")
            for i, output in enumerate(outputs, 1):
                text = output.get("text", "")
                print(f"  [{i}] {text}")
        else:
            print(f"\n❌ Error: {resp.text}")
            
    except Exception as e:
        print(f"\n❌ Request failed: {e}")

if __name__ == "__main__":
    # Test 1: Exam motivation
    test_agent("Give me motivation to pass my exam")
    
    # Test 2: Programming motivation
    test_agent("I need motivation to keep going in my programming life")
    
    # Test 3: Generic motivation
    test_agent("I'm feeling stuck today")
