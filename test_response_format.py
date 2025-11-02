"""Quick test to verify response format."""
import httpx
import json

# Test with Railway deployment
url = "https://hngstage3-production.up.railway.app/jsonrpc"

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
                    "text": "Give me motivation to pass my exam"
                }
            ],
            "messageId": "test-123"
        },
        "configuration": {
            "blocking": True  # Test blocking mode first
        }
    },
    "id": 1
}

print("Testing agent response format...")
print("="*60)

try:
    resp = httpx.post(url, json=payload, timeout=30)
    print(f"Status: {resp.status_code}\n")
    
    if resp.status_code == 200:
        data = resp.json()
        print("Full Response:")
        print(json.dumps(data, indent=2))
        
        result = data.get("result", {})
        outputs = result.get("outputs", [])
        message = result.get("message", {})
        
        print(f"\n✅ Has 'outputs': {len(outputs) > 0}")
        print(f"✅ Has 'message': {'messageId' in message}")
        
        if outputs:
            print(f"\nMotivations received:")
            for i, output in enumerate(outputs, 1):
                print(f"  [{i}] {output.get('text', '')[:80]}...")
    else:
        print(f"❌ Error: {resp.text}")
        
except Exception as e:
    print(f"❌ Failed: {e}")
