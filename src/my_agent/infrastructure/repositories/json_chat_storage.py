from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from my_agent.infrastructure.repositories.chat_storage import ChatStorageInterface
from my_agent.utils.logging import get_logger
from my_agent.utils.sanitizer import sanitize_arguments

logger = get_logger(__name__)

class JsonChatStorage(ChatStorageInterface):
    def __init__(self, storage_path: str = "./logs/chat"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_id: str, session_data: dict[str, Any]) -> None:
        file_path = self.storage_path / f"{session_id}.json"

        output_data = {
            "session_id": session_id,
            "create_at": session_data.get("create_at", datetime.now().isoformat()),
            "update_at": datetime.now().isoformat(),
            "system_prompt": session_data.get("system_prompt", ""),
            "turns": session_data.get("turns", []),
            "metadata": session_data.get("metadata", {})
        }

        sanitize_turns = []
        for turn in output_data["turns"]:
            sanitize_turn = self._sanitize_turn(turn)
            sanitize_turns.append(sanitize_turn)
        output_data["turns"] = sanitize_turns

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"会话 {session_id} 已保存到 {file_path}")
        except Exception as e:
            logger.error(f"会话保存失败 {e}")

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        file_path = self.storage_path / f"{session_id}.json"

        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            return session_data
        except Exception as e:
            logger.error(f"加载会话失败 {e}")
            return None
        
    def clear_session(self, session_id):
        file_path = self.storage_path / f"{session_id}.json"

        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"会话 {session_id} 已清空")
            except Exception as e:
                logger.error(f"清空会话失败 {e}")

    def export_turn_full_prompt(self, session_id: str, turn_index: int) -> dict[str, Any] | None:
        session_data = self.load_session(session_id)
        if not session_data:
            return None
        
        turns = session_data.get("turns", [])
        if turn_index < 0 or turn_index >= len(turns):
            logger.warning(f"无效的轮次索引: {turn_index}, 总论次数: {len(turns)}")
            return None
        
        messages = self.reconstruct_full_context(
            turns=turns,
            system_prompt=session_data.get("system_prompt", ""),
            target_turn_index=turn_index
        )

        return {
            "session_id": session_id,
            "turn_index": turn_index,
            "messages": messages,
        }

    def _sanitize_turn(self, turn: dict[str, Any]) -> dict[str, Any]:
        sanitized_turn = turn.copy()

        if "iteration" in sanitized_turn:
            sanitized_iterations = []
            for iteration in sanitized_turn["iteration"]:
                sanitized_iteration = iteration.copy()

                if "llm_response" in sanitized_iteration:
                    llm_response = sanitized_iteration["llm_response"]
                    if isinstance(llm_response, dict) and "tool_calls" in llm_response:
                        llm_response["tool_calls"] = [
                            {**tc, "arguments": sanitize_arguments(tc.get("arguments", {}))}
                            if isinstance(tc, dict) else tc
                            for tc in llm_response["tool_calls"]
                        ]

                if "tool_executions" in sanitized_iteration:
                    sanitized_iteration["tool_executions"] = [
                        {**te, "arguments": sanitize_arguments(te.get("arguments", {}))}
                            if isinstance(te, dict) else te
                            for te in sanitized_iteration["tool_executions"]
                    ]

                sanitized_iterations.append(sanitized_iteration)
            sanitized_turn["iteration"] = sanitized_iterations

        return sanitized_turn
    
    @staticmethod
    def reconstruct_full_context(
        turns: list[dict[str, Any]],
        system_prompt: str,
        target_turn_index: int
    ) -> list[dict[str, Any]]:
        messages = [{"role": "system", "content": system_prompt}]

        for i, turn in enumerate(turns):
            if i > target_turn_index:
                break
            added_messages = turn.get("added_messages", [])
            for msg in added_messages:
                messages.append(msg)

        return messages
            