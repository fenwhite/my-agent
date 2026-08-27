import io
import queue
import threading

import pygame

from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class TTSPlaybackThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="TTS-Playback")
        self._task_queue = queue.Queue(maxsize=5)
        self._stop_event = threading.Event()
        self._current_task_id = None

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
                
                self._playback(text, task_id)
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"TTS 引擎异常: {e}")

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