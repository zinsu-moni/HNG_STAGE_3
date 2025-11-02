from typing import Any, Dict
import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent import generate_motivation

app = FastAPI(title="A2A JSON-RPC Motivation Agent")

logger = logging.getLogger("uvicorn.error")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "A2A JSON-RPC Motivation Agent", "endpoint": "/jsonrpc"}


def jsonrpc_error(code: int, message: str, id_val: Any = None):
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id_val}


@app.post("/jsonrpc")
async def handle_jsonrpc(request: Request):
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
        if isinstance(params, dict):
            message_obj = params.get("message", {})
            if isinstance(message_obj, dict):
                parts = message_obj.get("parts", [])
                # Extract text from first text part
                for part in parts:
                    if isinstance(part, dict) and part.get("kind") == "text":
                        text = part.get("text", "")
                        if text and not text.startswith("<"):  # Skip HTML
                            user_input = text.strip()
                            break

        if not user_input:
            user_input = "Give me motivation"  # Fallback

        try:
            result = await generate_motivation(user_input)
            motivations = result.get("motivations", [])
            
            # Return A2A-compatible response with outputs array
            a2a_response = {
                "outputs": [
                    {
                        "kind": "text",
                        "text": motivation
                    }
                    for motivation in motivations
                ]
            }
            
            logger.info(f"Returning A2A response with {len(motivations)} motivations")
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
