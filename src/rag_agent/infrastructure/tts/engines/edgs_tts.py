import asyncio

import edgs_tts

from rag_agent.config.settings import get_settings
from rag_agent.infrastructure.tts.protocols import TTSEngineProtocol
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

class EdgeTTSEngine(TTSEngineProtocol):
    def __init__(self):
        settings = get_settings()
        self._voice = settings.tts_voice
        self._timeout = settings.tts_timeout

    def initialize(self) -> bool:
        return True
    
    async def synthesize(self, text: str) -> bytes:
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_chunks = []

            async def _stream_with_timeout():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])

            await asyncio.wait_for(_stream_with_timeout(), timeout=timeout)
            return b"".join(audio_chunks)
        
        except asyncio.TimeoutError:
            logger.warning(f"Edge-TTS 请求超时")
            return b""
        except Exception as e:
            logger.warning(f"Edge-TTS合成失败: {e}")
            return b""
        
    def shutdown(self) -> None:
        pass

    def is_available(self) -> bool:
        return True