from typing import Any, Dict
import os
import logging
import asyncio

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import httpx

from agent import generate_motivation

app = FastAPI(title="A2A JSON-RPC Motivation Agent")

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
        
        # A2A webhook payload format - JSON-RPC wrapped with message/send method
        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
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
            logger.info(f"Webhook response: {resp.status_code} - {resp.text[:200]}")
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
                # Extract text from first text part
                for part in parts:
                    if isinstance(part, dict) and part.get("kind") == "text":
                        text = part.get("text", "")
                        if text and not text.startswith("<"):  # Skip HTML
                            user_input = text.strip()
                            break
            
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

        # Non-blocking mode: return immediately and send webhook later
        if not blocking and webhook_config and webhook_config.get("url"):
            background_tasks.add_task(process_and_respond)
            logger.info("Non-blocking mode: queued background task, will send webhook")
            # Return immediate acknowledgment
            return JSONResponse(status_code=200, content={
                "jsonrpc": "2.0",
                "result": {"status": "processing", "messageId": message_id},
                "id": id_val
            })
        
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
