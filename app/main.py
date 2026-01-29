import os

from dotenv import load_dotenv
from flow import create_initial_node
from loguru import logger
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy import (
    TurnAnalyzerUserTurnStopStrategy,
)
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat_flows import ContextStrategy, ContextStrategyConfig, FlowManager
from pipecat_tail.observer import TailObserver
from utils import LanguageDetectorandSwitcher

load_dotenv(override=True)

async def bot(runner_args: RunnerArguments):
    """Main bot logic."""
    logger.info("Starting bot")
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
            serializer=serializer,
        ),
    )

    # Speech-to-Text service
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/stt.html
    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model=os.getenv("SARVAM_STT_MODEL"),
        # params=SarvamSTTService.InputParams(vad_signal=True, high_vad_sensitivity=True),
    )

    # Text-to-Speech service
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/tts.html
    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model=os.getenv("SARVAM_TTS_MODEL"),
        voice_id=os.getenv("SARVAM_TTS_VOICE_ID"),
        aggregate_sentences=True,
        params=SarvamTTSService.InputParams(
            language=None,  # en is the default, will be changed once user speaks
            pitch=0.20,  # slightly sharper. 0.0 - neutral, deeper<0.0>sharper
            pace=0.85,  # speed of speech
            loudness=1.1,  # volume level
            enable_preprocessing=True,  # improves pronunciation of numbers, dates, abbr, etc.. and mixed-language text.
            output_audio_bitrate="64k",  # lower bitrate for audio stream, good for speech
        ),
    )

    # LLM service
    # pipecat defaults thinking mode to none, that's what we want!
    llm = GoogleLLMService(
        model=os.getenv("LLM_ID"),
        api_key=os.getenv("LLM_API_KEY"),
    )

    context = LLMContext()
    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                stop=[
                    TurnAnalyzerUserTurnStopStrategy(
                        turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams())
                    )
                ]
            ),
        ),
    )

    # Pipeline - assembled from reusable components
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            LanguageDetectorandSwitcher(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=16000,  # recommened by sarvam
            audio_out_sample_rate=16000,
        ),
        observers=[TailObserver()],
    )

    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        context_strategy=ContextStrategyConfig(
            strategy=ContextStrategy.APPEND,
        ),
        transport=transport,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        await flow_manager.initialize(create_initial_node())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
