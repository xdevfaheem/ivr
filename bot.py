import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.runner.types import RunnerArguments, WebSocketRunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport

load_dotenv(override=True)


# TODO: add interruptions
# https://github.com/pipecat-ai/pipecat/pull/3325
# https://github.com/pipecat-ai/pipecat/pull/3045
# https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/07z-interruptible-sarvam.py
async def run_bot(transport: BaseTransport):
    """Main bot logic."""
    logger.info("Starting bot")

    # Speech-to-Text service
    # auto lang detection!
    # https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe#request.body.language_code.language_code
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/stt.html

    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model=os.getenv("SARVAM_STT_MODEL"),
        # params=SarvamSTTService.InputParams(language="unknown")
    )

    # Text-to-Speech service
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/tts.html
    # TODO: dynamically define language, sarvam stt returns language_id (check the output of code-mixed speech in: https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika#key-capabilities) which i have to figure to use with TTS initialization
    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model=os.getenv("SARVAM_TTS_MODEL"),
        voice_id=os.getenv("SARVAM_TTS_VOICE_ID"),
        params=SarvamTTSService.InputParams(
            language="ta-IN", pitch=0.50, pace=1.0, loudness=1.0, enable_preprocessing=True
        ),
    )

    # LLM service
    llm = OpenAILLMService(model=os.getenv("OPENAI_MODEL"), api_key=os.getenv("OPENAI_API_KEY"))

    messages = [
        {
            "role": "system",
            "content": "You are a friendly IVR AI assistant for indian consumers. Respond naturally and keep your answers conversational, more importantly be sure to respond in their own language.",
        },
    ]

    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    # Pipeline - assembled from reusable components
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):

    transport = None
    match runner_args:
        case WebSocketRunnerArguments():
            # Parse Twilio websocket and fetch call information
            _, call_data = await parse_telephony_websocket(runner_args.websocket)

            serializer = TwilioFrameSerializer(
                stream_sid=call_data["stream_id"],
                call_sid=call_data["call_id"],
                account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            )

            transport = FastAPIWebsocketTransport(
                websocket=runner_args.websocket,
                params=FastAPIWebsocketParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    add_wav_header=False,
                    vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
                    turn_analyzer=LocalSmartTurnAnalyzerV3(),
                    serializer=serializer,
                ),
            )
        case _:
            logger.error(f"Unsupported runner arguments type: {type(runner_args)}")
            return

    await run_bot(transport)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
