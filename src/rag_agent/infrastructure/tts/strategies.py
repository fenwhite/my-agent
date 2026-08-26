from abc import ABC, abstractmethod

from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

class TextProcessingStrategy(ABC):

    @abstractmethod
    def process(self, text: str) -> str:
        pass


class TextTruncationStrategy(TextProcessingStrategy):
    MAX_LENGTH = 800

    @classmethod
    def truncate(cls, text: str) -> str:
        instance = cls()
        return instance.process(text)
    
    def process(self, text: str) -> str:
        if len(text) <= self.MAX_LENGTH:
            return text
        
        truncated = text[:self.MAX_LENGTH]
        logger.waring(f"文本过长 ({len(text)} 字符)， 已截断到 {self.MAX_LENGTH} 字符")
        return truncated + "..."


class TextCleaningStrategy(TextProcessingStrategy):
    CHARS_TO_REMOVE = ["*"]

    @classmethod
    def clean(cls, text: str) -> str:
        instance = cls()
        return instance.process(text)
    
    def process(self, text: str) -> str:
        cleaned_text = text
        for char in self.CHARS_TO_REMOVE:
            cleaned_text = cleaned_text.replace(char, "")

        return cleaned_text