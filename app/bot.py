import os

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.frames.frames import TTSSpeakFrame
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
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy import (
    TurnAnalyzerUserTurnStopStrategy,
)
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat_flows import ContextStrategy, ContextStrategyConfig, FlowManager

from app.flow import create_initial_node
from app.utils import LanguageDetectorandSwitcher


async def run_bot(transport: BaseTransport, handle_sigint: bool):

    # Speech-to-Text service
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/stt.html
    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model="saaras:v3",
        params=SarvamSTTService.InputParams(
            language=None,  # auto-detect
            vad_signals=True,
            high_vad_sensitivity=True,
            mode="codemix",
        ),
    )

    # language detect and switch on start
    language_switcher = LanguageDetectorandSwitcher(stt)

    # Text-to-Speech service
    # https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/sarvam/tts.html
    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model="bulbul:v3",
        voice_id="neha",
        aggregate_sentences=True,
        params=SarvamTTSService.InputParams(
            language=None,  # en is the default, will be changed once user speaks
            pace=1.4,  # speed of speech
            min_buffer_size=40,
            max_chunk_length=100,
            enable_preprocessing=True,  # improves pronunciation of numbers, dates, abbr, etc.. and mixed-language text.
            output_audio_bitrate="128k",  # lower bitrate for audio stream, good for speech
            temperature=0.5,
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
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
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
            language_switcher,
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
        # observers=[TailObserver()],
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
        await task.queue_frame(TTSSpeakFrame("Hey there! How can I assist you today?"))
        await flow_manager.initialize(create_initial_node())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=handle_sigint, force_gc=True)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):

    transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
    logger.info(f"Auto-detected transport: {transport_type}")

    serializer = PlivoFrameSerializer(
        stream_id=call_data["stream_id"],
        call_id=call_data["call_id"],
        auth_id=os.getenv("PLIVO_AUTH_ID", ""),
        auth_token=os.getenv("PLIVO_AUTH_TOKEN", ""),
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    await run_bot(transport, runner_args.handle_sigint)
