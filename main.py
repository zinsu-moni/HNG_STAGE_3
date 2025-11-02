from typing import Any, Dict
import os
import re
import logging
import asyncio

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

from agent import generate_motivation

# Load environment variables from .env file (only in local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Environment loaded from .env file")
except Exception as e:
    # In production (Vercel), env vars are set via dashboard
    print(f"⚠ Could not load .env: {e}")

app = FastAPI(title="A2A JSON-RPC Motivation Agent")

# Log environment configuration on startup
@app.on_event("startup")
async def startup_event():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("A2A_MODEL")
    print("\n" + "="*60)
    print("🚀 A2A Motivation Agent Starting...")
    print("="*60)
    print(f"API Key: {'✓ Configured' if api_key else '✗ Missing'}")
    print(f"Base URL: {base_url or '✗ Missing'}")
    print(f"Model: {model or '✗ Missing'}")
    print("="*60 + "\n")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

logger = logging.getLogger("uvicorn.error")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "A2A JSON-RPC Motivation Agent", "endpoint": "/jsonrpc"}


def jsonrpc_error(code: int, message: str, id_val: Any = None):
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id_val}


async def send_webhook_notification(webhook_url: str, token: str, outputs: list, message_id: str):
    """Send A2A webhook notification for async responses."""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # A2A webhook payload format - Try simplified format with outputs at top level
        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "outputs": outputs,  # Outputs at params level
                "message": {
                    "kind": "message",
                    "role": "agent",
                    "parts": outputs,
                    "messageId": message_id
                }
            },
            "id": message_id
        }
        
        logger.info(f"Sending webhook notification to {webhook_url}")
        logger.info(f"Webhook payload: {payload}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload, headers=headers)
            logger.info(f"Webhook response: {resp.status_code} - {resp.text[:500]}")
            return resp.status_code in [200, 201, 202, 204]
    except Exception as e:
        logger.exception(f"Failed to send webhook notification: {e}")
        return False


@app.post("/jsonrpc")
async def handle_jsonrpc(request: Request, background_tasks: BackgroundTasks):
    logger.info(f"Received request to /jsonrpc from {request.client}")
    
    try:
        payload = await request.json()
        logger.info(f"Request payload: {payload}")
    except Exception as e:
        logger.error(f"Invalid JSON: {e}")
        return JSONResponse(status_code=400, content=jsonrpc_error(-32700, "Parse error", None))

    # Basic JSON-RPC 2.0 validation
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content=jsonrpc_error(-32600, "Invalid Request", None))

    jsonrpc = payload.get("jsonrpc")
    method = payload.get("method")
    params = payload.get("params") or {}
    id_val = payload.get("id")

    if jsonrpc != "2.0":
        return JSONResponse(status_code=400, content=jsonrpc_error(-32600, "Invalid Request: unsupported jsonrpc version", id_val))

    if not method:
        return JSONResponse(status_code=400, content=jsonrpc_error(-32601, "Method not found", id_val))

    # Handle A2A protocol method: "message/send"
    if method == "message/send":
        # Extract user message from A2A protocol format
        user_input = None
        message_id = None
        webhook_config = None
        blocking = True
        
        if isinstance(params, dict):
            # Extract message content
            message_obj = params.get("message", {})
            if isinstance(message_obj, dict):
                message_id = message_obj.get("messageId")
                parts = message_obj.get("parts", [])
                # Extract text from all parts, combining them
                collected_texts = []
                for part in parts:
                    if isinstance(part, dict) and part.get("kind") == "text":
                        text = part.get("text", "").strip()
                        if text:
                            # Strip HTML tags if present
                            text = re.sub(r'<[^>]+>', ' ', text)  # Remove HTML tags
                            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                            text = text.strip()
                            if text and text.lower() not in ['ok', 'more']:  # Skip filler words
                                collected_texts.append(text)
                
                # Use the most meaningful text (longest non-HTML)
                if collected_texts:
                    user_input = max(collected_texts, key=len)
            
            # Extract configuration
            config = params.get("configuration", {})
            if isinstance(config, dict):
                blocking = config.get("blocking", True)
                webhook_config = config.get("pushNotificationConfig")

        if not user_input:
            user_input = "Give me motivation"  # Fallback

        logger.info(f"Processing: '{user_input[:50]}...' | Blocking: {blocking} | MessageID: {message_id}")

        async def process_and_respond():
            """Generate motivation and send webhook if needed."""
            try:
                result = await generate_motivation(user_input)
                motivations = result.get("motivations", [])
                
                # Build A2A outputs
                outputs = [
                    {"kind": "text", "text": motivation}
                    for motivation in motivations
                ]
                
                logger.info(f"Generated {len(motivations)} motivations")
                
                # Send webhook notification if non-blocking
                if not blocking and webhook_config:
                    webhook_url = webhook_config.get("url")
                    token = webhook_config.get("token")
                    if webhook_url and token and message_id:
                        await send_webhook_notification(webhook_url, token, outputs, message_id)
                
                return outputs
            except Exception as e:
                logger.exception("Agent error in process_and_respond")
                return []

        # Non-blocking mode with webhook: return outputs immediately AND send via webhook
        if not blocking and webhook_config and webhook_config.get("url"):
            try:
                # Generate outputs immediately  
                outputs = await process_and_respond()
                
                # Return outputs in the response so UI can display them
                a2a_response = {"outputs": outputs}
                
                logger.info(f"Non-blocking mode: returning {len(outputs)} outputs (webhook also sent)")
                return JSONResponse(status_code=200, content={
                    "jsonrpc": "2.0",
                    "result": a2a_response,
                    "id": id_val
                })
            except Exception as e:
                logger.exception("Agent error")
                return JSONResponse(status_code=500, content=jsonrpc_error(-32000, f"Server error: {str(e)}", id_val))
        
        # Blocking mode OR non-blocking without webhook: wait for response and return directly
        try:
            outputs = await process_and_respond()
            a2a_response = {"outputs": outputs}
            
            logger.info(f"Returning {'blocking' if blocking else 'direct non-blocking'} response with {len(outputs)} outputs")
            return JSONResponse(status_code=200, content={"jsonrpc": "2.0", "result": a2a_response, "id": id_val})
        except Exception as e:
            logger.exception("Agent error")
            return JSONResponse(status_code=500, content=jsonrpc_error(-32000, f"Server error: {str(e)}", id_val))

    # Also support simple "motivate" method for backward compatibility
    elif method == "motivate":
        user_input = None
        if isinstance(params, dict):
            user_input = params.get("input") or params.get("message")
        elif isinstance(params, list) and len(params) > 0:
            user_input = params[0]

        if not user_input:
            return JSONResponse(status_code=400, content=jsonrpc_error(-32602, "Invalid params: 'input' or 'message' is required", id_val))

        try:
            result = await generate_motivation(user_input)
        except Exception as e:
            logger.exception("Agent error")
            return JSONResponse(status_code=500, content=jsonrpc_error(-32000, f"Server error: {str(e)}", id_val))

        return JSONResponse(status_code=200, content={"jsonrpc": "2.0", "result": result, "id": id_val})

    return JSONResponse(status_code=404, content=jsonrpc_error(-32601, f"Method '{method}' not found", id_val))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
