import base64
import json

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket
from starlette.responses import Response

load_dotenv(override=True)
# log.setup()

app = FastAPI(
    title="Plivo XML Server", description="Serves XML for Plivo WebSocket streaming"
)


def get_websocket_url(host: str, body_data: dict | None = None):
    """Construct WebSocket URL based on environment variables with query parameters."""

    # Build query parameters
    query_params = []

    base_url = f"wss://{host}/ws"

    # Add body data as query parameter
    if body_data:
        body_json = json.dumps(body_data)
        body_encoded = base64.b64encode(body_json.encode("utf-8")).decode("utf-8")
        query_params.append(f"body={body_encoded}")

    # Construct final URL
    if query_params:
        return f"{base_url}?{'&amp;'.join(query_params)}"
    else:
        return base_url


@app.get("/")
async def start_call(
    request: Request,
    # Optional Plivo parameters that are automatically passed by Plivo
    CallUUID: str = Query(None, description="Plivo call UUID"),
    From: str = Query(None, description="Caller's phone number"),
    To: str = Query(None, description="Called phone number"),
):
    """
    Returns XML for Plivo to start WebSocket streaming with call information

    Optional parameters (automatically passed by Plivo):
    - CallUUID, From, To
    """
    print("GET Plivo XML")

    # Create body data with phone numbers only
    body_data = {}

    # Always include phone numbers if available
    if From:
        body_data["from"] = From
    if To:
        body_data["to"] = To

    # Log call details
    if CallUUID:
        print(f"Plivo inbound call: {From} → {To}, UUID: {CallUUID}")
        if body_data:
            print(f"Body data: {body_data}")

    # Get request host and construct WebSocket URL with body data
    host = request.headers.get("host")
    if not host:
        raise HTTPException(status_code=400, detail="Unable to determine server host")

    websocket_url = get_websocket_url(host, body_data if body_data else None)

    # Build XML without extraHeaders (using query parameters instead)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak>Please hold while we connect you.</Speak>
    <Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000">
    {websocket_url}
    </Stream>
</Response>"""
    print(f"Generated XML: {xml}")
    return Response(content=xml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    body: str = Query(None),
    serviceHost: str = Query(None),
):
    """Handle WebSocket connections for inbound calls."""
    await websocket.accept()
    print("WebSocket connection accepted for inbound call")

    print(f"Received query params - body: {body}, serviceHost: {serviceHost}")

    # Decode body parameter if provided
    body_data = {}
    if body:
        try:
            # Base64 decode the JSON (it was base64-encoded in the webhook handler)
            decoded_json = base64.b64decode(body).decode("utf-8")
            body_data = json.loads(decoded_json)
            print(f"Decoded body data: {body_data}")
        except Exception as e:
            print(f"Error decoding body parameter: {e}")
    else:
        print("No body parameter received")

    try:
        # Import the bot function from the bot module
        from pipecat.runner.types import WebSocketRunnerArguments

        from app.bot import bot

        # Create runner arguments and run the bot
        runner_args = WebSocketRunnerArguments(websocket=websocket)
        runner_args.handle_sigint = False

        # TODO: When WebSocketRunnerArguments supports body, add it here:
        # runner_args = WebSocketRunnerArguments(websocket=websocket, body=body_data)

        await bot(runner_args)

    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
        await websocket.close()


if __name__ == "__main__":
    # Run the server on port 7860
    # Use with ngrok: ngrok http 7860
    uvicorn.run(app, host="0.0.0.0", port=7860)
