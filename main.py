from typing import Any, Dict
import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent import generate_motivation

app = FastAPI(title="A2A JSON-RPC Motivation Agent")

logger = logging.getLogger("uvicorn.error")


def jsonrpc_error(code: int, message: str, id_val: Any = None):
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id_val}


@app.post("/jsonrpc")
async def handle_jsonrpc(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        logger.debug("Invalid JSON: %s", e)
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

    # Only one method implemented for now: "motivate"
    if method == "motivate":
        user_input = None
        if isinstance(params, dict):
            user_input = params.get("input")
        elif isinstance(params, list) and len(params) > 0:
            user_input = params[0]

        if not user_input:
            return JSONResponse(status_code=400, content=jsonrpc_error(-32602, "Invalid params: 'input' is required", id_val))

        try:
            result = await generate_motivation(user_input)
        except Exception as e:
            logger.exception("Agent error")
            return JSONResponse(status_code=500, content=jsonrpc_error(-32000, f"Server error: {str(e)}", id_val))

        return JSONResponse(status_code=200, content={"jsonrpc": "2.0", "result": result, "id": id_val})

    return JSONResponse(status_code=404, content=jsonrpc_error(-32601, "Method not found", id_val))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
