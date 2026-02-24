from loguru import logger
from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.stt_service import STTService
from pipecat.transcriptions.language import Language


class LanguageDetectorandSwitcher(FrameProcessor):
    """Parse detected language from STT result and updates TTS config to that language."""

    def __init__(
        self,
        stt: STTService,
    ):
        super().__init__()
        self._stt = stt
        self.lang_changed = False
        self.lang_id = Language("en-IN")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            detected_language = frame.language

            # only change the language once
            if not self.lang_changed and detected_language != self.lang_id:
                try:
                    # update stt
                    await self._stt.set_language(detected_language)

                    # update tts target lang
                    # https://github.com/pipecat-ai/pipecat/issues/2989#issuecomment-3718916895
                    # had to pass different voice in-order to trigger the config change to tts connection, otherwise it won't
                    # https://github.com/pipecat-ai/pipecat/blob/10aa78480926fc6ef868e360b3b7e6891a7b256c/src/pipecat/services/sarvam/tts.py#L527
                    await self.push_frame(
                        TTSUpdateSettingsFrame(
                            settings={
                                "target_language_code": detected_language,
                                "voice_id": "simran",
                                "pace": 1.2

                            }
                        ),
                    )


                    self.lang_changed = True
                    self.lang_id = detected_language
                    logger.info(
                        f"Language changed to {detected_language} for this call"
                    )

                except (ValueError, KeyError) as e:
                    logger.warning(
                        f"Could not convert language '{detected_language}': {e}"
                    )
        # always push every frame
        await self.push_frame(frame, direction)
