from functools import lru_cache

from my_agent.config.settings import get_settings
from my_agent.infrastructure.llm.sync_client import SyncLLMClient

from my_agent.core.services.prompt_registry import PromptRegistry

from my_agent.infrastructure.repositories.json_chat_storage import JsonChatStorage

from my_agent.infrastructure.memory import DefaultConversationMemory

class ServiceFactory:
    @staticmethod
    def get_prompt_registry() -> PromptRegistry:
        return PromptRegistry.get_instance()

    @staticmethod
    @lru_cache(maxsize=1)
    def get_llm_client() -> SyncLLMClient:
        settings = get_settings()
        return SyncLLMClient(
            api_key=settings.api_key,
            base_url=settings.base_url)

    @staticmethod
    def get_chat_service():
        from my_agent.core.services.chat_service import ChatService

        prompt_registry = ServiceFactory.get_prompt_registry()

        llm_client = ServiceFactory.get_llm_client()
        storage = JsonChatStorage()
        memory = DefaultConversationMemory(
            llm_client=llm_client,
            token_budget=4000,
            waterline_ratio=0.8,
            system_prompt=prompt_registry.get_no_raise("compress"),
        )

        return ChatService(llm_client=llm_client, storage=storage, memory=memory, system_prompt=prompt_registry.get_current())



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