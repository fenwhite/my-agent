from typing import TypeAlias

Document: TypeAlias = dict[str, str | float | list[float]]
Embedding: TypeAlias = list[float]