"""Test what the Railway deployment actually returns."""
import httpx
import json

url = "https://hngstage3-production.up.railway.app/jsonrpc"

# Simulate exactly what the workflow sends
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
            "messageId": "test-msg-123"
        },
        "configuration": {
            "blocking": False,  # Non-blocking like the workflow
            "pushNotificationConfig": {
                "url": "https://example.com/webhook",
                "token": "test-token"
            }
        }
    },
    "id": "test-id-123"
}

print("🔍 Testing Railway deployment response...")
print("="*60)

try:
    response = httpx.post(url, json=payload, timeout=30)
    
    print(f"\n✅ Status Code: {response.status_code}")
    print(f"\n📦 Full Response:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 200:
        data = response.json()
        result = data.get("result", {})
        
        has_outputs = "outputs" in result
        has_message = "message" in result
        
        print(f"\n📊 Response Structure:")
        print(f"  ✓ Has 'outputs': {has_outputs}")
        print(f"  ✓ Has 'message': {has_message}")
        
        if has_outputs:
            outputs = result["outputs"]
            print(f"  ✓ Number of outputs: {len(outputs)}")
            
            if outputs:
                print(f"\n💬 First motivation:")
                print(f"  {outputs[0].get('text', '')}")
        
        if has_message:
            message = result["message"]
            print(f"\n📨 Message structure:")
            print(f"  - role: {message.get('role')}")
            print(f"  - messageId: {message.get('messageId')}")
            print(f"  - parts count: {len(message.get('parts', []))}")
            
except Exception as e:
    print(f"\n❌ Error: {e}")
