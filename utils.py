from loguru import logger
from pipecat.frames.frames import Frame, TranscriptionFrame, TTSUpdateSettingsFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


# yeah naming is meh
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
