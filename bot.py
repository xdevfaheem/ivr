import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    TTSSpeakFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport

load_dotenv(override=True)

# TODO: add interruptions, waiting for v.0.0.99 to be released, which includes standardized way to implement turn taking (https://github.com/pipecat-ai/pipecat/pull/3045#issuecomment-3712696317)
# https://github.com/pipecat-ai/pipecat/pull/3325
# https://github.com/pipecat-ai/pipecat/pull/3045
# https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/07z-interruptible-sarvam.py


# yeah naming sucks
class LanguageDetectorandSwitcher(FrameProcessor):
    """Parse detected language from STT result and updates TTS config to that language."""

    def __init__(
        self,
    ):
        super().__init__()
        self.lang_changed = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            detected_language = frame.language
            # only change the language once
            if not self.lang_changed and detected_language != "en-IN":
                try:
                    # update tts target lang
                    # https://github.com/pipecat-ai/pipecat/issues/2989#issuecomment-3718916895
                    # had to pass different voice in-order to trigger the config change to tts connection, otherwise it won't, it must a bug ig
                    # https://github.com/pipecat-ai/pipecat/blob/10aa78480926fc6ef868e360b3b7e6891a7b256c/src/pipecat/services/sarvam/tts.py#L527
                    await self.push_frame(
                        TTSUpdateSettingsFrame(
                            settings={
                                "target_language_code": detected_language,
                                "voice_id": "manisha",
                            }
                        ),
                        FrameDirection.DOWNSTREAM,
                    )

                    self.lang_changed = True
                    logger.info(f"Language changed to {detected_language} for this call")

                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not convert language '{detected_language}': {e}")

        await self.push_frame(frame, direction)


async def run_bot(transport: BaseTransport):
    """Main bot logic."""
    logger.info("Starting bot")

    # Speech-to-Text service
    # sarvam does auto lid by default
    # https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe#request.body.language_code.language_code
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/stt.html

    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model=os.getenv("SARVAM_STT_MODEL"),
    )

    # Text-to-Speech service
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/tts.html
    # TODO: dynamically define target language, sarvam stt returns language_id (check the output of code-mixed speech in: https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika#key-capabilities) which i have to figure to use with TTS initialization
    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model=os.getenv("SARVAM_TTS_MODEL"),
        voice_id=os.getenv("SARVAM_TTS_VOICE_ID"),
        aggregate_sentences=False,
        params=SarvamTTSService.InputParams(
            language=None,  # en is the default, will be changed once user speaks
            pitch=0.30,  # slightly sharper. 0.0 - neutral, deeper<0.0>sharper
            pace=0.9,  # speed of speech
            loudness=1.2,  # volume level
            enable_preprocessing=True,  # improves pronunciation of numbers, dates, abbr, etc.. and mixed-language text.
        ),
    )

    # LLM service
    # pipecat defaults thinking mode to none, that's what we want!
    llm = GoogleLLMService(model=os.getenv("LLM_ID"), api_key=os.getenv("LLM_API_KEY"))

    system_prompt = """\
You are a helpful AI assistant in an audio call. Have a natural conversation with the user in the language they are speaking in, though you can mix-in words or phrase from any other languages where needed. And also, your output will be converted into audio, so don't include special characters in your answers that can't easily be spoken, such as emojii, asterisk, bullet points, etc.
"""

    context = LLMContext([{"role": "system", "content": system_prompt}])
    context_aggregator = LLMContextAggregatorPair(context)

    # Pipeline - assembled from reusable components
    pipeline = Pipeline([
        transport.input(),
        stt,
        LanguageDetectorandSwitcher(),
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
        await task.queue_frame(TTSSpeakFrame("Welcome to IVR Demo."))

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):

    # Parse Twilio websocket and fetch call information
    _, call_data = await parse_telephony_websocket(runner_args.websocket)

    serializer = TwilioFrameSerializer(
        stream_sid=call_data["stream_id"],
        call_sid=call_data["call_id"],
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        params=TwilioFrameSerializer.InputParams(auto_hang_up=True),
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

    await run_bot(transport)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
