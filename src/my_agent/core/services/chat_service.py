
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, List
from datetime import datetime

from my_agent.core.services.prompt_registry import PromptRegistry
from my_agent.infrastructure.repositories.chat_storage import ChatStorageInterface
from my_agent.infrastructure.llm.sync_client import SyncLLMClient
from my_agent.core.tools.executor import ToolExecutor
from my_agent.core.tools.tool_registry import ToolRegistry
from my_agent.infrastructure.memory import (Message, ConversationMemory)
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class ChatService:
    """聊天服务，处理多轮对话和上下文管理。"""

    def __init__(
        self,
        llm_client: SyncLLMClient,
        storage: ChatStorageInterface,
        memory: ConversationMemory,
        system_prompt: str,
    ) -> None:
        from my_agent.core.tools.executor import ToolExecutor
        from my_agent.core.tools.tool_registry import ToolRegistry
        
        self._llm_client = llm_client
        self._storage = storage 
        self._session_id = str(uuid.uuid4())
        self._system_prompt = system_prompt
        self._turns: list[dict[str, Any]] = []
        self._turn_count = 0
        
        # 工具执行器
        self._tool_executor = ToolExecutor()
        self._tool_registry = ToolRegistry.get_instance()
        
        # 循环控制配置
        self._max_tool_iterations = 200          # 最大工具调用轮次
        self._max_same_tool_calls = 50          # 同一工具最多连续调用次数
        self._tool_call_history: List[dict] = []  # 记录工具调用历史
        
        # 记忆管理器
        self._memory = memory
    
    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def turn_count(self) -> int:
        return self._turn_count

    def chat(
        self,
        user_input: str,
        max_turns: int = 20,
    ) -> dict[str, Any]:
        """执行一轮聊天对话（支持工具调用）。"""
        # 检查是否达到轮次上限
        if self._turn_count >= max_turns:
            msg = "本轮对话已达到长度限制，建议开启新会话以保持最佳性能。"
            self._save_session()
            return {"content": msg, "tool_calls": [], "session_ended": True}

        # 初始化当前轮次的数据结构
        turn_data = {
            "turn_index": self._turn_count,
            "timestamp": datetime.now().isoformat(),
            "iterations": [],
            "added_messages": [],
        }
        
        # 添加用户消息到 Memory
        user_msg = Message(role="user", content=user_input)
        self._memory.add_message(user_msg)
        
        # 添加用户消息到 turn_data（用于持久化）
        turn_data["added_messages"].append({"role": "user", "content": user_input})
        
        self._turn_count += 1

        # 重置工具调用历史
        self._tool_call_history = []
        
        # 使用 Memory 获取上下文消息
        context_messages_obj = self._memory.get_context_messages()
        context_messages = [msg.to_dict() for msg in context_messages_obj]
        tools = self._get_available_tools()

        # 工具执行循环
        baseline_message_count = len(context_messages)
        
        for iteration in range(self._max_tool_iterations):
            try:
                # 记录 LLM 请求（只存储新增消息）
                new_messages = context_messages[baseline_message_count:]
                llm_request = {
                    "new_messages": new_messages,
                }
                
                # 调用 LLM（传入工具定义）
                response = self._llm_client.chat_completion(
                    messages=context_messages,
                    tools=tools if tools else None
                )
                
                ai_content = self._llm_client.get_response_content(response)
                tool_calls = self._extract_tool_calls(response)
                
                # 记录 LLM 响应
                llm_response = {
                    "content": ai_content,
                    "tool_calls": tool_calls,
                }
                
                # 如果没有工具调用，直接返回
                if not tool_calls:
                    assistant_message = {"role": "assistant", "content": ai_content}
                    turn_data["added_messages"].append(assistant_message)
                    
                    # 添加助手回复到 Memory
                    assistant_msg = Message(role="assistant", content=ai_content)
                    self._memory.add_message(assistant_msg)
                    
                    # 保存当前轮次数据
                    self._turns.append(turn_data)
                    self._save_session()
                    
                    return {
                        "content": ai_content,
                        "tool_calls": [],
                        "session_ended": False,
                    }
                
                # 检测是否会陷入循环
                if self._detect_loop(tool_calls):
                    logger.warning("检测到潜在的工具调用循环，终止执行")
                    final_answer = self._generate_fallback_answer(ai_content, tool_calls)
                    assistant_message = {"role": "assistant", "content": final_answer}
                    turn_data["added_messages"].append(assistant_message)
                    
                    # 添加助手回复到 Memory
                    assistant_msg = Message(role="assistant", content=final_answer)
                    self._memory.add_message(assistant_msg)
                    
                    # 保存当前轮次数据
                    self._turns.append(turn_data)
                    self._save_session()
                    
                    return {
                        "content": final_answer,
                        "tool_calls": tool_calls,
                        "session_ended": False,
                    }
                
                # 执行工具调用
                tool_executions = []
                for tc in tool_calls:
                    # 记录调用历史
                    self._record_tool_call(tc)
                    
                    result = asyncio.run(self._tool_executor.execute_tool_call(tc))
                    tool_executions.append({
                        "tool_name": tc["name"],
                        "arguments": tc.get("arguments", {}),
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                    })
                
                # 记录当前迭代
                iteration_data = {
                    "iteration_index": iteration,
                    "llm_request": llm_request,
                    "llm_response": llm_response,
                    "tool_executions": tool_executions,
                }
                turn_data["iterations"].append(iteration_data)
                
                # 将工具结果加入上下文，让 LLM 基于结果生成最终回答
                tool_result_message = self._format_tool_results(tool_executions)
                context_messages.append({"role": "assistant", "content": ai_content})
                context_messages.append({
                    "role": "user", 
                    "content": f"工具执行结果：\n{tool_result_message}\n\n请基于以上结果继续回答用户问题。如果工具执行失败，请分析原因并给出建议，不要重复调用相同的工具。"
                })
                
                # 继续迭代，让 LLM 基于工具结果生成最终回答
                baseline_message_count = len(context_messages)
                continue
                
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}")
                error_content = f"抱歉，处理您的请求时出现错误：{str(e)}"
                error_message = {"role": "assistant", "content": error_content}
                turn_data["added_messages"].append(error_message)
                
                # 添加助手回复到 Memory
                assistant_msg = Message(role="assistant", content=error_content)
                self._memory.add_message(assistant_msg)
                
                # 保存当前轮次数据
                self._turns.append(turn_data)
                self._save_session()
                
                return {
                    "content": error_content,
                    "tool_calls": [],
                    "session_ended": False,
                }
        
        # 达到最大迭代次数
        fallback_content = "抱歉，经过多次尝试仍无法完成请求。可能是工具使用方式有误，请重新描述您的需求。"
        fallback_message = {"role": "assistant", "content": fallback_content}
        turn_data["added_messages"].append(fallback_message)
        
        # 添加助手回复到 Memory
        assistant_msg = Message(role="assistant", content=fallback_content)
        self._memory.add_message(assistant_msg)
        
        # 保存当前轮次数据
        self._turns.append(turn_data)
        self._save_session()
        
        return {
            "content": fallback_content,
            "tool_calls": [],
            "session_ended": False,
        }

    def _get_available_tools(self) -> List[dict]:
        """获取可用的工具列表（OpenAI 格式）。"""
        return self._tool_registry.get_openai_tools_format()

    def _extract_tool_calls(self, response) -> list[dict[str, Any]]:
        """从 LLM 响应中提取工具调用信息。"""
        tool_calls = []
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name if hasattr(tc, 'function') else "unknown",
                    "arguments": tc.function.arguments if hasattr(tc, 'function') else "{}",
                })
        return tool_calls

    def _detect_loop(self, current_tool_calls: list) -> bool:
        """检测是否可能陷入循环。
        
        策略：
        1. 同一工具被连续调用超过阈值
        2. 相同参数的工具被重复调用
        """
        for tc in current_tool_calls:
            tool_signature = {
                "name": tc["name"],
                "args_hash": hash(json.dumps(tc.get("arguments", {}), sort_keys=True) if isinstance(tc.get("arguments"), dict) else tc.get("arguments", ""))
            }
            
            # 检查最近 N 次调用中是否有相同签名
            recent_calls = self._tool_call_history[-5:]  # 看最近 5 次
            match_count = sum(
                1 for h in recent_calls 
                if h["name"] == tool_signature["name"] and h["args_hash"] == tool_signature["args_hash"]
            )
            
            if match_count >= self._max_same_tool_calls:
                logger.warning(
                    f"检测到重复调用: {tc['name']} 已调用 {match_count} 次"
                )
                return True
        
        return False

    def _record_tool_call(self, tool_call: dict):
        """记录工具调用历史。"""
        args = tool_call.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        
        self._tool_call_history.append({
            "name": tool_call["name"],
            "args_hash": hash(json.dumps(args, sort_keys=True)),
            "timestamp": time.time(),
        })
        
        # 保持历史记录不超过 20 条
        if len(self._tool_call_history) > 20:
            self._tool_call_history = self._tool_call_history[-20:]

    def _format_tool_results(self, results: List[dict]) -> str:
        """格式化工具执行结果为 LLM 可读的消息。"""
        parts = []
        for r in results:
            if r["success"]:
                parts.append(f"✅ 工具 '{r['tool_name']}' 执行成功:\n{r['output']}")
            else:
                parts.append(f"❌ 工具 '{r['tool_name']}' 执行失败: {r['error']}")
        return "\n\n".join(parts)

    def _generate_fallback_answer(self, ai_content: str, tool_calls: list) -> str:
        """当检测到循环时，生成降级回答。"""
        tool_names = [tc["name"] for tc in tool_calls]
        return (
            f"我尝试执行以下操作但遇到了问题：{', '.join(tool_names)}。\n\n"
            f"可能的原因：\n"
            f"1. 文件路径不正确或文件不存在\n"
            f"2. 权限不足\n"
            f"3. 工具参数有误\n\n"
            f"原始回复：{ai_content}\n\n"
            f"建议您检查路径是否正确，或提供更详细的信息。"
        )

    def _save_session(self):
        """持久化当前会话数据。"""
        try:
            # 计算元数据
            total_tool_calls = sum(
                len(iteration.get("tool_executions", []))
                for turn in self._turns
                for iteration in turn.get("iterations", [])
            )
            
            # 获取记忆状态
            compressed_summary = ""
            if self._memory:
                compressed_summary, _ = self._memory.get_state()
            
            session_data = {
                "created_at": datetime.now().isoformat(),
                "system_prompt": self._system_prompt,
                "available_tools": self._get_available_tools(),
                "turns": self._turns,
                "compressed_summary": compressed_summary,
                "metadata": {
                    "total_turns": len(self._turns),
                    "total_tool_calls": total_tool_calls,
                },
            }
            
            self._storage.save_session(self._session_id, session_data)
        except Exception as e:
            logger.warning(f"保存会话数据失败: {e}")
    
    def load_session(self, session_id: str) -> bool:
        """从持久化存储加载会话状态。
        
        Args:
            session_id: 要加载的会话 ID
            
        Returns:
            是否成功加载
        """
        try:
            session_data = self._storage.load_session(session_id)
            if not session_data:
                logger.warning(f"会话 {session_id} 不存在")
                return False
            
            # 恢复基本状态
            self._session_id = session_id
            self._system_prompt = session_data.get("system_prompt", "")
            self._turns = session_data.get("turns", [])
            self._turn_count = len(self._turns)
            
            # 恢复记忆状态
            if self._memory:
                compressed_summary = session_data.get("compressed_summary", "")
                
                # 从 turns 中重建活动窗口（取最后几条消息）
                active_window = self._rebuild_active_window_from_turns(self._turns)
                
                self._memory.load_state(compressed_summary, active_window)
                self._memory.system_prompt = self._system_prompt
            
            logger.info(f"会话 {session_id} 已加载")
            return True
            
        except Exception as e:
            logger.error(f"加载会话失败: {e}")
            return False
    
    def _rebuild_active_window_from_turns(self, turns: list[dict]) -> list[Message]:
        """从历史轮次中重建活动窗口消息。
        
        Args:
            turns: 历史轮次列表
            
        Returns:
            活动窗口消息列表
        """
        messages = []
        
        # 从每个轮次的 added_messages 中提取最近的消息
        for turn in turns[-3:]:  # 只取最后 3 轮
            for msg_dict in turn.get("added_messages", []):
                messages.append(Message.from_dict(msg_dict))
        
        return messages

    def clear_history(self):
        """清空对话历史。"""
        self._turns.clear()
        self._turn_count = 0
        self._system_prompt = ""
        
        # 清空记忆
        if self._memory:
            self._memory.clear()
        
        self._storage.clear_session(self._session_id)
        # 生成新的会话 ID
        self._session_id = str(uuid.uuid4())
        logger.info(f"新会话 {self._session_id} 已创建")
