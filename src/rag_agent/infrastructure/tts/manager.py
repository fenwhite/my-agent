from rag_agent.infrastructure.tts.engines.edgs_tts import EdgeTTSEngine
from rag_agent.infrastructure.tts.playback_thread import TTSPlaybackThread
from rag_agent.infrastructure.tts.strategies import TextCleaningStrategy,TextTruncationStrategy
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

class TTSManager:

    def __init__(self):
        self._enable = False
        self._task_counter = 0

        self._engine = EdgeTTSEngine()

        self._playback_thread = TTSPlaybackThread()

    def enable(self):
        if not self._enable:
            if not self._engine.initialize():
                logger.warning("TTS 引擎初始化失败，语音功能不可用")
                print("⚠ TTS 引擎初始化失败，请检查服务是否运行")

            self._enable = True
            if not self._playback_thread.is_alive():
                self._playback_thread.start()

            logger.info("语音输出已启用")
            print("√ 语音输出已启用")
        else:
            print("√ 语音当前已启用")

    def disable(self):
        if self._enable:
            self._enable = False
            logger.info("语音输出已禁用")
            print("√ 语音输出已禁用")
        else:
            print("√ 语音当前已禁用")

    @property
    def is_enable(self) -> bool:
        return self._enable
    
    async def speak(self, text: str):
        if not self._enable or not text.strip():
            return
        
        cleaned_text = TextCleaningStrategy.clean(text)
        truncated_text = TextTruncationStrategy.truncate(cleaned_text)

        self._task_counter += 1
        task_id = f"task_{self._task_counter}"

        audio_data = await self._engine.synthesize(truncated_text)

        if not audio_data:
            logger.warning(f"音频合成失败,跳过播放 [task_id={task_id}]")
            print("⚠ 音频合成失败")
            return
        
        self._playback_thread.submit(audio_data, task_id)

    def shutdown(self):
        if self._playback_thread.is_alive():
            self._playback_thread.shutdown()
        self._engine.shutdown()