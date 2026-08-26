import asyncio
import queue
import threading
import io

import edge_tts
import pygame

from rag_agent.config.settings import get_settings
from rag_agent.utils.logging import get_logger
from rag_agent.infrastructure.tts.strategies import TextCleaningStrategy, TextTruncationStrategy

logger = get_logger(__name__)

class TTSEngine(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="TTS-Engine")
        self._task_queue = queue.Queue(maxsize=5)
        self._stop_event = threading.Event()
        self._current_task = None

    def start(self):
        pygame.mixer.init(frequency=24000, size=-16, channels=1)
        super().start()

    def submit(self, text: str, task_id: str):
        try:
            self._current_task = task_id
            self._task_queue.put_nowait((text, task_id))
            logger.info(f"提交TTS任务 [task_id={task_id}]")
        except queue.Full:
            logger.warning("TTS 任务队列已满， 丢弃最旧任务")

    def run(self):
        while not self._stop_event.is_set():
            try:
                text, task_id = self._task_queue.get(timeout=1.0)

                if task_id != self._current_task:
                    continue
                
                self._play(text, task_id)
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"TTS 引擎异常: {e}")

    def _play(self, text: str, task_id: str):
        try:
            cleaned_text = TextCleaningStrategy.clean(text)
            processed_text = TextTruncationStrategy.truncate(text)

            settings = get_settings()
            audio_data = asyncio.run(self._fetch_audio(processed_text, settings.tts_voice, settings.tts_timeout))

            if task_id != self._current_task:
                return

            self._playback(audio_data, task_id)

        except asyncio.TimeoutError:
            logger.warning(f"TTS 请求超时 [task_id={task_id}]")
        except Exception as e:
            logger.warning(f"TTS 播放失败 [task]_id={task_id}]: {e}")
    
    async def _fetch_audio(self, text: str, voice: str, timeout: float) -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        audio_chunks = []

        async def _stream_with_timeout():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

        await asyncio.wait_for(_stream_with_timeout(), timeout=timeout)
        return b"".join(audio_chunks)

    def _playback(self, audio_data: bytes, task_id: str):
        if not audio_data:
            return
        
        try:
            audio_stream = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_stream)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                if task_id != self._current_task:
                    logger.info(f"检测到新任务，中断当前播放 [task_id={task_id}]")
                    pygame.mixer.music.stop()
                    break
                clock.tick(10)
        except Exception as e:
            logger.warning(f"音频播放失败: {e}")

    def shutdown(self):
        self._stop_event.set()
        try:
            pygame.mixer.music.stop()
        except:
            pass
        self.join(timeout=5)
        pygame.mixer.quit()