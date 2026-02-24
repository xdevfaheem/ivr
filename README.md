# Smilo's Voice Agent for Hospital Appointment

## How It Works

When someone calls your Plivo number:

1. **Plivo calls your webhook**: `GET https://your-server.com/` with call info (From, To, CallUUID)
2. **Server returns XML**: Tells Plivo to start a WebSocket stream to your bot
3. **WebSocket connection**: Audio streams between caller and your bot
4. **Call information**: Phone numbers are passed via query parameters in the WebSocket URL to your bot

## Setup

1. Set up a virtual environment and install dependencies:
   Once inside the directory,
   
   ```sh
   uv sync
   ```

3. Create an .env file and add API keys:

   ```sh
   cp env.example .env
   ```

   Get Plivo's credential from the its console.

## To run:

### Configure Plivo URLs

1. Start ngrok:
   In a new terminal, start ngrok to tunnel the local server:

   ```sh
   ngrok http 7860
   ```

2. Update the Plivo Application:

   - Go to your Plivo console and navigate to Voice > Applications > XML
   - Select "Add New Application" or edit an existing one
   - Set the Primary Answer URL to your ngrok URL: `https://your-subdomain.ngrok.io/`
   - Ensure the Answer Method is set to GET (not POST)
   - Save the application
   - Configure your number to use the newly created (or updated) application:
     - Go to Phone Numbers > Your Numbers
     - Edit your Plivo number
     - Select Application Type: XML Application
     - Plivo Application: Your application
     - Click "Update" to save

The bot automatically receives the caller's and called phone numbers for personalized responses via the body parameter.

### Run the Local Server

`server.py` runs a FastAPI server, which Plivo uses to coordinate the inbound call. Run the server using:

```bash
uv run server.py
```

### Call your Bot

Now we can call the number associated with the bot. The bot will answer and start the conversation.
