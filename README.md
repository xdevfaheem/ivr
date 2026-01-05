<h1 style="text-align:center;">Inbound IVR AI Voice Agent (PoC)</h1>

## Architecture

```
Phone Call <-> Twilio <-> Media Streams (WebSocket) <-> Pipecat <-> AI Services (VAD -> STT -> LLM -> TTS)
```

**Components:**

- **Twilio**: Handles phone call routing and audio transport
- **Media Streams**: Real-time bidirectional audio over WebSocket
- **Pipecat**: Audio processing pipeline and AI service orchestration
- **AI Services**:
    - **STT**: Sarvam
    - **LLM**: OpenAI
    - **TTS**: Sarvam

## Setup

### Setting Up Twilio

#### 1. Create a TwiML Bin 

A TwiML Bin tells Twilio how to handle incoming calls. Basicall it is kinda similar to dialplan, when call comes in twilio look at this XML to know where to find the websocket server to establish a (bi-directional audio) connection to our bot.

1. Go to the [Twilio Console](https://console.twilio.com)
2. Navigate to **TwiML Bins** → **My TwiML Bins**
3. Click the **+** to create a new TwiML Bin
4. Name your bin and add the TwiML:

    ```xml
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Connect>
        <Stream url="wss://our-ngrok-url/ws" />
      </Connect>
    </Response>
    ```

#### 2. Assign TwiML Bin to Your Phone Number

1. Navigate to **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on your Twilio phone number
3. In the "Voice Configuration" section:
   - Set "A call comes in" to **TwiML Bin**
   - Select the TwiML Bin you created
4. Click **Save configuration**

## Server

1. **Install dependencies**:

   ```bash
   uv sync
   ```

2. **Configure environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run the bot**:

   - Run ngrok tunnel (in another terminal): `ngrok http 7860`
   - Run the server: `uv run bot.py --transport twilio --proxy that-ngrok-url`
