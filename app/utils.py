from loguru import logger
from pipecat.frames.frames import (
    Frame,
    LLMMessagesAppendFrame,
    STTUpdateSettingsFrame,
    TranscriptionFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transcriptions.language import Language
import pycountry

# yeah naming is meh
class LanguageDetectorandSwitcher(FrameProcessor):
    """Parse detected language from STT result and updates TTS config to that language."""

    def __init__(
        self,
    ):
        super().__init__()
        self.lang_changed = False
        self.lang = Language("en-IN")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            detected_language = frame.language
            # only change the language once
            if (
                not self.lang_changed and detected_language != self.lang
            ):  # english it the initial langugage
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
                    # update stt
                    await self.push_frame(
                        STTUpdateSettingsFrame(settings={"language": detected_language})
                    )

                    # update llm
                    lang_name = pycountry.languages.get(alpha_2=str(detected_language).split("-")[0]).name
                    await self.push_frame(
                        LLMMessagesAppendFrame(
                            [
                                {
                                    "role": "system",
                                    "content": f"Respond to the user in {str(lang_name)} from now on.",
                                }
                            ]
                        )
                    )

                    self.lang_changed = True
                    self.lang = detected_language
                    logger.info(
                        f"Language changed to {detected_language} for this call"
                    )

                except (ValueError, KeyError) as e:
                    logger.warning(
                        f"Could not convert language '{detected_language}': {e}"
                    )

        await self.push_frame(frame, direction)
