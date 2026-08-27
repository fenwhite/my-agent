from __future__ import annotations

import copy
from typing import Any, Optional

from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class Blackboard:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def _get_key_name(self, agent_name: str, output_key: str) -> str:
        return f"{agent_name}:{output_key}"

    def write(self, agent_name: str, output_key: str, value: Any) -> None:
        key = self._get_key_name(agent_name, output_key)

        if key in self._data:
            self._merge(key, value)
        else:
            self._data[key] = copy.deepcopy(value)

        logger.debug(f"Blackboard updated: {key} = {self._data[key]}")

    def read(self, agent_name: str, output_key: str) -> Optional[Any]:
        key = self._get_key_name(agent_name, output_key)
        value = self._data.get(key)

        if value is not None:
            return copy.deepcopy(value)
        return None

    def read_by_key(self, key: str) -> Optional[Any]:
        value = self._data.get(key)
        if value is not None:
            return copy.deepcopy(value)
        return None

    def has_key(self, key: str) -> bool:
        return key in self._data

    def get_all_data(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def get_keys_by_agent(self, agent_name: str) -> list[str]:
        prefix = f"{agent_name}:"
        return [key for key in self._data.keys() if key.startswith(prefix)]

    def _merge(self, key: str, new_value: Any) -> None:
        old_value = self._data[key]

        if isinstance(old_value, dict) and isinstance(new_value, dict):
            for k, v in new_value.items():
                if k in old_value:
                    old_val = old_value[k]
                    if isinstance(old_val, dict) and isinstance(v, dict):
                        self._merge_dicts(old_val, v)
                    elif isinstance(old_val, list) and isinstance(v, list):
                        old_value[k] = old_val + v
                    else:
                        old_value[k] = v
                else:
                    old_value[k] = copy.deepcopy(v)
        elif isinstance(old_value, list) and isinstance(new_value, list):
            self._data[key] = old_value + copy.deepcopy(new_value)
        else:
            self._data[key] = [old_value, copy.deepcopy(new_value)]

    def _merge_dicts(self, old_dict: dict, new_dict: dict) -> dict:
        merged = copy.deepcopy(old_dict)
        for k, v in new_dict.items():
            if k in merged:
                old_val = merged[k]
                if isinstance(old_val, dict) and isinstance(v, dict):
                    merged[k] = self._merge_dicts(old_val, v)
                elif isinstance(old_val, list) and isinstance(v, list):
                    merged[k] = old_val + v
                else:
                    merged[k] = v
            else:
                merged[k] = copy.deepcopy(v)

        return merged