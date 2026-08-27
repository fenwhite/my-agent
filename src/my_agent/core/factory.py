from functools import lru_cache

from my_agent.config.settings import get_settings
from my_agent.infrastructure.llm.sync_client import SyncLLMClient


class ServiceFactory:

    @staticmethod
    @lru_cache(maxsize=1)
    def get_llm_client():
        settings = get_settings()
        return SyncLLMClient(
            api_key=settings.api_key,
            base_url=settings.base_url)

    @staticmethod
    def get_chat_service():
        from my_agent.core.services.chat_service import ChatService

        llm_client = ServiceFactory.get_llm_client()

        return ChatService(llm_client=llm_client)

    @staticmethod
    def get_query_service():
        from my_agent.core.services.query_service import QueryService

        llm_client = ServiceFactory.get_llm_client()

        return QueryService(llm_client=llm_client)

    @staticmethod
    def get_orchestrator():
        """获取编排器实例。"""
        from rag_agent.core.orchestra.orchestrator import Orchestrator
        
        llm_client = ServiceFactory.get_llm_client()
        
        return Orchestrator(llm_client=llm_client)