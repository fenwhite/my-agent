这是一个经过完整优化的、基于 Python 的 **Agent 技能动态加载与执行框架技术方案**。

本方案严格遵循 **PEP 428** 规范（全面采用 `pathlib` 优雅替代 `os` 模块），并实现了**懒加载（Lazy Loading）**与**瞬态执行（Transient Execution）**机制。需要首先澄清一个工程判断：本框架的懒加载与瞬态执行**并非为节省本地内存而设计**——百级技能的完整定义（含详尽描述与 Schema）序列化后仅数百 KB 至 1-2 MB，相对 Python 进程数十 MB 的基线占用、向量数据库数百 MB 至 GB 级的内存索引、本地 Embedding/Reranker 模型 GB 级的显存占用，完全可忽略不计；为节省这部分内存而设计复杂的加载/卸载机制属于典型的过度设计（Over-engineering）。LLM 应用的计算瓶颈在云端（GPU/Token 与上下文窗口），而非本地内存条。因此，懒加载的真正价值在于**规避启动期执行任意代码与 import 副作用**，瞬态执行的真正价值在于**执行隔离与无状态性**。同时，方案将 **Sub-agent 设计为角色化的任务执行单元**（而非普通 Skill），由 Master Agent 进行统一的拆解与编排。面向大规模技能场景，方案进一步引入**基于 HyDE 检索语料与 Reflection 重路由机制的轻量级技能路由器**，完成 L0→L1 的候选晋升，使上下文开销在技能规模化后依然保持恒定。

---

### 一、 系统架构图与目录结构

#### 1. 架构流向图
```text
  [ Master Agent ] (分析任务)
         │
         ├──► 1. 查询 [Agent Registry] 获取所有子智能体元数据 (AgentMetadata)
         ├──► 2. 决策任务拆解，指派任务给指定的 Sub-Agent
         │
  [ Skill Router ] (轻量级路由，技能规模超过阈值时自动启用)
         │
         ├──► 1. 权限硬过滤 (bound_skills) -> 2. 语义检索 Top-K -> 3. 晋升至 L1 披露
         │
  [ Sub-Agent (例如: Coder) ] (执行特定任务)
         │
         ├──► 1. 从路由候选中获取自己绑定的 Skill 列表 (Top-K)
         ├──► 2. 做出工具调用决策 (Tool Calling)，候选不匹配时触发 Reflection 重路由
         │
  [ Transient Executor ] (瞬态执行)
         │
         ├──► 1. 披露说明 (读取 instruction.md 注入上下文，不加载代码)
         ├──► 2. 动态加载 (importlib) -> 载入指定 Skill 的 .py 代码
         ├──► 3. 执行 -> 输出校验 -> 返回结果
         └──► 4. 卸载 (Purge sys.modules) -> 执行隔离收尾，杜绝跨技能状态泄漏
```

#### 1.1 渐进式披露的三级信息层次 (Progressive Disclosure)

本框架将 Skill 的信息按**决策阶段所需的认知成本**分层，LLM 逐层加深理解，而非一次性全量暴露。技能规模较小时为 L1→L2→L3 三级披露；技能规模化后引入 L0 全量注册表与 Skill Router，形成 L0→L1 的晋升机制：

```text
┌─────────────────────────────────────────────────────────────────────┐
│ L0 全量注册表 (不可见)  全部 SkillReference 常驻内存，不进入 LLM 上下文 │
│   载体: Registry + 向量索引  用途: 供 Skill Router 检索，规模化后启用  │
├─────────────────────────────────────────────────────────────────────┤
│ L1 元数据层 (可见)      name / description / schema 摘要             │
│   载体: *.json        成本: 极低，仅 JSON 文本，随 Registry 常驻      │
│   用途: LLM 判断"要不要用这个 Skill"（规模化时仅披露路由 Top-K）      │
├─────────────────────────────────────────────────────────────────────┤
│ L2 说明层 (按需披露)  详细用法 / 参数示例 / 边界约束 / 失败模式       │
│   载体: instruction.md 成本: 中等，纯文本注入上下文，不加载任何代码   │
│   用途: LLM 在决定调用后、执行前，深化"怎么正确用"的认知              │
├─────────────────────────────────────────────────────────────────────┤
│ L3 实现层 (瞬态执行)  实际业务代码                                   │
│   载体: *.py          成本: 最高，importlib 载入虚拟机，执行后即卸载  │
│   用途: 真正产生执行结果                                             │
└─────────────────────────────────────────────────────────────────────┘
```

对应的目录约定：每个 Skill 由**同名三件套**组成，其中 `instruction.md` 为可选文件，缺省时自动退化为两级披露。

```text
skills/
├── web_search.json            # L1: 元数据
├── web_search.md              # L2: 详细说明 (可选)
├── web_search.py              # L3: 实现代码
└── ...
```

#### 2. 包分层结构设计
```text
agent_framework/
│
├── core/
│   ├── __init__.py
│   ├── base_skill.py            # 技能接口定义
│   ├── base_agent.py            # 智能体接口定义
│   ├── context.py               # 运行时上下文定义
│   └── metadata.py              # Pydantic 元数据定义 (Pathlib 兼容)
│
├── registry/
│   ├── __init__.py
│   ├── skill_registry.py        # 内存仅保存 Skill 路径和元数据引用
│   └── agent_registry.py        # 子智能体注册表
│
├── loader/
│   ├── __init__.py
│   └── lazy_loader.py           # PEP 428 标准的轻量级 JSON 扫描器
│
├── executor/
│   ├── __init__.py
│   └── transient_executor.py    # 瞬态执行器（按需加载、彻底释放）
│
└── router/
    ├── __init__.py
    ├── skill_router.py          # 轻量级路由器（权限过滤 -> 语义检索 Top-K -> 晋升 L1）
    └── retrieval_corpus.py      # HyDE 检索语料构建器（离线生成假设性问题）
```

---

### 二、 核心代码实现

#### 1. 核心上下文与元数据层 (`core/context.py`, `core/metadata.py`)

##### `core/context.py`
```python
from pydantic import BaseModel, Field
from typing import Dict, Any

class AgentContext(BaseModel):
    """
    贯穿整个执行链路的上下文环境，不持有任何执行体，仅持有纯数据。
    """
    session_id: str
    trace_id: str
    current_agent_id: str                          # 当前正在执行任务的 Agent ID
    variables: Dict[str, Any] = Field(default_factory=dict) # 跨节点传递的共享变量
```

##### `core/metadata.py`
```python
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional

class SkillMetadata(BaseModel):
    """
    提供给 LLM 决策时使用的 Skill 轻量级 Schema
    """
    name: str = Field(..., description="技能唯一标识")
    description: str = Field(..., description="技能功能描述，LLM 依赖此描述决定是否调用")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema 格式的输入参数定义")
    output_schema: Dict[str, Any] = Field(..., description="JSON Schema 格式的输出结果定义")
    pinned: bool = Field(default=False, description="是否钉住：为 True 时绕过路由，始终对 LLM 可见（用于关键技能兜底召回）")

class SkillReference(BaseModel):
    """
    Skill 的静态物理引用，内存中仅常驻此对象，不加载实际代码。
    """
    model_config = ConfigDict(arbitrary_types_allowed=True) # 允许使用 Pathlib.Path 类型

    metadata: SkillMetadata
    file_path: Path              # PEP 428 Path 对象，指向具体的 .py 代码文件 (L3)
    class_name: str              # 该 .py 文件中对应技能实现类的名称
    instruction_path: Optional[Path] = None  # L2 详细说明文档路径，缺省表示该 Skill 无说明层

class AgentMetadata(BaseModel):
    """
    Sub-agent 的元数据定义，用于 Master Agent 拆解任务时进行决策
    """
    agent_id: str = Field(..., description="唯一子智能体 ID")
    role: str = Field(..., description="子智能体角色定位 (e.g., Searcher, Developer)")
    description: str = Field(..., description="该智能体擅长解决的场景描述")
    bound_skills: List[str] = Field(default_factory=list)  # 该 Agent 被允许调用的 Skill 名称列表
```

#### 2. 基类抽象层 (`core/base_skill.py`, `core/base_agent.py`)

##### `core/base_skill.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from core.metadata import SkillMetadata
from core.context import AgentContext

class BaseSkill(ABC):
    """
    所有本地执行技能的基类。所有动态加载的技能必须继承此类。
    """
    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        技能具体业务逻辑的异步执行入口。
        """
        pass
```

##### `core/base_agent.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from core.metadata import AgentMetadata
from core.context import AgentContext

class BaseAgent(ABC):
    """
    所有智能体（包括 Master 和 Sub-Agent）的抽象基类。
    """
    def __init__(self, metadata: AgentMetadata):
        self.metadata = metadata

    @abstractmethod
    async def run(self, task_description: str, context: AgentContext) -> Dict[str, Any]:
        """
        智能体执行任务的入口。
        - Sub-Agent: 在内部规划如何调用绑定的 Skill 来完成此任务。
        - Master Agent: 调用 AgentRegistry 分析子 Agent 角色，拆解任务，然后下发任务给 Sub-Agent。
        """
        pass
```

#### 3. 注册表层 (`registry/skill_registry.py`, `registry/agent_registry.py`)

##### `registry/skill_registry.py`
```python
from typing import Dict, List, Optional
from core.metadata import SkillReference, SkillMetadata

class LocalSkillRegistry:
    """
    本地技能注册表。内存中仅持有 SkillReference，不持有 BaseSkill 的执行实例。
    """
    def __init__(self):
        self._references: Dict[str, SkillReference] = {}

    def register_reference(self, ref: SkillReference) -> None:
        self._references[ref.metadata.name] = ref

    def get_reference(self, name: str) -> Optional[SkillReference]:
        return self._references.get(name)

    def list_metadata_for_agent(self, bound_skill_names: List[str]) -> List[SkillMetadata]:
        """
        根据 Sub-agent 绑定的技能范围，仅返回该 Agent 拥有权限的技能元数据。
        """
        return [
            self._references[name].metadata 
            for name in bound_skill_names 
            if name in self._references
        ]

    def list_all_references(self) -> List[SkillReference]:
        """
        返回全部已注册的技能引用，供路由语料离线构建（L0 层）使用。
        """
        return list(self._references.values())
```

##### `registry/agent_registry.py`
```python
from typing import Dict, List, Optional
from core.base_agent import BaseAgent
from core.metadata import AgentMetadata

class LocalAgentRegistry:
    """
    子智能体注册表，供 Master Agent 发现可调度的 Sub-agents。
    """
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.metadata.agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def list_agent_metadata(self) -> List[AgentMetadata]:
        """
        供 Master Agent 决策时获取所有的子角色设定
        """
        return [agent.metadata for agent in self._agents.values()]
```

#### 4. 本地懒加载器 (`loader/lazy_loader.py`)

##### `loader/lazy_loader.py`
```python
import json
from pathlib import Path
from typing import List, Union
from core.metadata import SkillMetadata, SkillReference

class LazySkillLoader:
    """
    懒加载器：遵循 PEP 428 规范，只扫描和读取配置文件，绝不提前 import python 文件。
    """
    def __init__(self, skills_dir: Union[str, Path]):
        # 统一转为绝对路径的 Path 对象
        self.skills_dir = Path(skills_dir).resolve()

    def discover_skills(self) -> List[SkillReference]:
        discovered_references: List[SkillReference] = []
        
        if not self.skills_dir.is_dir():
            raise FileNotFoundError(f"技能目录不存在: {self.skills_dir}")

        # 使用 pathlib 的优雅迭代：只查找描述元数据的 .json 文件
        for json_path in self.skills_dir.glob("*.json"):
            # 优雅地寻找同名且后缀为 .py 的执行文件
            py_path = json_path.with_suffix(".py")
            
            if py_path.is_file():
                # 仅读取静态 JSON，完全不载入 Python 虚拟机内存
                with json_path.open('r', encoding='utf-8') as f:
                    config = json.load(f)
                
                metadata = SkillMetadata(**config["metadata"])

                # L2 说明层探测：同名 .md 存在则登记路径，但此时绝不读取其内容
                instruction_path = json_path.with_suffix(".md")
                ref = SkillReference(
                    metadata=metadata,
                    file_path=py_path,
                    class_name=config["class_name"],
                    instruction_path=instruction_path if instruction_path.is_file() else None
                )
                discovered_references.append(ref)
                
        return discovered_references
```

#### 5. 瞬态执行器 (`executor/transient_executor.py`)

##### `executor/transient_executor.py`
```python
import sys
import gc
import importlib.util
from typing import Dict, Any, Optional
from core.base_skill import BaseSkill
from core.context import AgentContext
from core.metadata import SkillReference

class TransientSkillExecutor:
    """
    瞬态执行器：实现 披露说明 -> 载入 -> 实例化 -> 执行 -> 销毁 -> 卸载 的完整闭环。
    """
    
    def __init__(self):
        self._current_module_name: str | None = None

    def disclose_instruction(self, ref: SkillReference) -> Optional[str]:
        """
        L2 按需披露：在加载任何代码之前，仅以纯文本形式读取说明文档并注入上下文。
        让 LLM 在付出 L3 执行成本前，先以极低成本深化对该 Skill 用法的认知。
        """
        if ref.instruction_path is None or not ref.instruction_path.is_file():
            return None
        return ref.instruction_path.read_text(encoding="utf-8")

    def _load_and_instantiate(self, ref: SkillReference) -> BaseSkill:
        """
        利用 importlib 动态加载独立文件，防止模块在系统中产生残留
        """
        # 构造虚拟模块名称，防止冲突
        self._current_module_name = f"dynamic_skill_{ref.metadata.name}"
        
        # 兼容 PEP 428：转换 Pathlib 路径为 spec 识别的绝对路径字符串
        file_path_str = str(ref.file_path.resolve())
        
        spec = importlib.util.spec_from_file_location(self._current_module_name, file_path_str)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法为技能文件生成 Spec: {file_path_str}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 取得模块中的实现类并实例化
        skill_class = getattr(module, ref.class_name)
        skill_instance: BaseSkill = skill_class(metadata=ref.metadata)
        
        return skill_instance

    def _cleanup_memory(self):
        """
        执行隔离收尾：从 sys.modules 卸载动态模块并触发垃圾回收。
        目的不是节省内存（元数据常驻成本可忽略），而是杜绝技能代码污染
        全局命名空间、避免跨技能状态泄漏，并保证技能代码热更新即时生效。
        """
        if self._current_module_name:
            # 1. 从 Python 模块缓存中移除它
            if self._current_module_name in sys.modules:
                del sys.modules[self._current_module_name]
            self._current_module_name = None
            
            # 2. 强制触发垃圾回收器回收未被引用的动态加载类与内存
            gc.collect()

    async def execute(self, ref: SkillReference, arguments: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        瞬态执行全生命周期
        """
        skill_instance: BaseSkill | None = None
        try:
            # 1. L2 披露：先注入说明文档，供调用方校验参数与用法（无代码成本）
            instruction = self.disclose_instruction(ref)
            if instruction:
                context.variables[f"skill_instruction:{ref.metadata.name}"] = instruction

            # 2. L3 动态载入代码并实例化（开始占用代码内存）
            skill_instance = self._load_and_instantiate(ref)
            
            # 3. 异步执行实际业务
            result = await skill_instance.execute(arguments, context)
            return result
            
        finally:
            # 4. 显式解除实例绑定，并清理本次披露注入的说明文本
            context.variables.pop(f"skill_instruction:{ref.metadata.name}", None)
            if skill_instance:
                del skill_instance
            # 5. 执行隔离收尾：卸载动态模块，杜绝跨技能状态泄漏
            self._cleanup_memory()
```

#### 6. 轻量级技能路由器 (`router/retrieval_corpus.py`, `router/skill_router.py`)

路由器负责 L0→L1 的候选晋升，遵循两条不变式：**权限硬过滤永远先于语义软排序**（扩池只在授权范围内发生）；**成本守恒**（技能数低于阈值时全量披露的 Token 成本更低，路由自动关闭）。`EmbeddingProvider` / `VectorIndex` / `LLMClient` 均为协议抽象，具体适配器落位于 `infrastructure` 层，与 RAG 知识检索共用同一套检索基建。

##### `router/retrieval_corpus.py`
```python
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable
from pydantic import BaseModel, Field
from core.metadata import SkillReference

@runtime_checkable
class EmbeddingProvider(Protocol):
    """Embedding 服务抽象，具体适配器落位于 infrastructure 层。"""
    async def embed(self, texts: List[str]) -> List[List[float]]: ...

@runtime_checkable
class LLMClient(Protocol):
    """LLM 调用抽象，用于离线生成假设性问题。"""
    async def complete(self, prompt: str) -> str: ...

@runtime_checkable
class VectorIndex(Protocol):
    """向量索引抽象。条目按文本维度存储，一个技能对应多条语料条目。"""
    def upsert(self, entries: List["CorpusEntry"]) -> None: ...
    def search(self, query_vector: List[float], top_k: int,
               allowed_skill_names: Optional[List[str]] = None) -> List[Tuple[str, float]]: ...

class CorpusEntry(BaseModel):
    """单条语料条目：同一 skill_name 下的多条条目（描述 + 假设性问题）映射到同一技能。"""
    skill_name: str
    text: str                              # 参与 Embedding 的原文
    vector: List[float] = Field(default_factory=list)

_HYDE_PROMPT_TEMPLATE = """你是工具检索语料构建助手。请为以下技能生成 {count} 个用户可能会问的假设性问题。
技能名称: {name}
技能描述: {description}

要求:
1. 问题必须口语化且表达多样，覆盖同义词、边缘场景与同一意图的不同问法；
2. 不要直接复述技能描述原文；
3. 仅输出 JSON 字符串数组，不含任何其他内容，例如: ["问题1", "问题2"]
"""

class RetrievalCorpusBuilder:
    """
    HyDE 检索语料构建器：注册期离线为每个技能生成假设性问题并构建向量语料，
    弥合"用户口语化提问"与"技能技术性描述"之间的语义鸿沟，提升路由首次召回率。
    语料按元数据内容哈希增量缓存，未变更的技能不重复调用 LLM。
    构建完成后统一 upsert 至向量索引，完成"语料生成 -> 向量化 -> 索引注册"闭环。
    """
    def __init__(self, llm_client: LLMClient, embedding_provider: EmbeddingProvider,
                 vector_index: VectorIndex, cache_path: Path, question_count: int = 5):
        self.llm_client = llm_client
        self.embedding_provider = embedding_provider
        self.vector_index = vector_index
        self.cache_path = Path(cache_path).resolve()
        self.question_count = question_count

    def _content_hash(self, ref: SkillReference) -> str:
        raw = f"{ref.metadata.name}|{ref.metadata.description}|{ref.class_name}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _load_cache(self) -> Dict[str, dict]:
        if self.cache_path.is_file():
            with self.cache_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self, cache: Dict[str, dict]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    def _parse_questions(self, raw_output: str) -> List[str]:
        try:
            parsed = json.loads(raw_output)
            if isinstance(parsed, list):
                return [str(question).strip() for question in parsed if str(question).strip()]
        except json.JSONDecodeError:
            pass
        # LLM 未遵循 JSON 格式时的兜底：按行提取非空文本
        return [line.strip(" -\t") for line in raw_output.splitlines() if line.strip(" -\t")]

    async def _generate_questions(self, ref: SkillReference) -> List[str]:
        prompt = _HYDE_PROMPT_TEMPLATE.format(
            count=self.question_count,
            name=ref.metadata.name,
            description=ref.metadata.description,
        )
        raw_output = await self.llm_client.complete(prompt)
        questions = self._parse_questions(raw_output)[: self.question_count]
        # 优雅降级：生成失败时以描述本身作为唯一语料文本，保证路由链路始终可用
        return questions if questions else [ref.metadata.description]

    async def build(self, references: List[SkillReference]) -> List[CorpusEntry]:
        """
        增量构建：LLM 生成按内容哈希增量执行（昂贵步骤），Embedding 对全量语料文本
        批量计算，随后统一 upsert 至向量索引，使路由检索链路即时可用。
        """
        cache = self._load_cache()
        current_skill_names = {ref.metadata.name for ref in references}

        # 清理已注销技能的陈旧语料，避免索引中残留不可达条目
        for stale_name in list(cache.keys()):
            if stale_name not in current_skill_names:
                del cache[stale_name]

        for ref in references:
            digest = self._content_hash(ref)
            cached = cache.get(ref.metadata.name)
            if cached and cached.get("hash") == digest:
                continue
            questions = await self._generate_questions(ref)
            cache[ref.metadata.name] = {
                "hash": digest,
                "texts": [ref.metadata.description, *questions],
            }

        texts_to_embed: List[Tuple[str, str]] = [
            (skill_name, text)
            for skill_name, record in cache.items()
            for text in record["texts"]
        ]
        vectors = await self.embedding_provider.embed([text for _, text in texts_to_embed])

        entries = [
            CorpusEntry(skill_name=skill_name, text=text, vector=vector)
            for (skill_name, text), vector in zip(texts_to_embed, vectors)
        ]
        self.vector_index.upsert(entries)
        self._save_cache(cache)
        return entries
```

##### `router/skill_router.py`
```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from core.context import AgentContext
from core.metadata import SkillMetadata, SkillReference
from registry.skill_registry import LocalSkillRegistry
from router.retrieval_corpus import EmbeddingProvider, VectorIndex

class RoutingStrategy(str, Enum):
    REFORMULATE = "reformulate"   # 改写检索意图，同 K 重路由
    EXPAND_POOL = "expand_pool"   # 扩大候选池 (K -> K * expand_factor)
    FULL_SCAN = "full_scan"       # 全量披露授权技能（终局兜底，每任务仅一次）

class RerouteRequest(BaseModel):
    """
    结构化重路由信号：LLM 必须以显式工具调用表达"候选不匹配"，
    使 Reflection 过程可审计、可计数，而非从自由文本中猜测意图。
    """
    reason: str = Field(..., description="当前候选不匹配的原因")
    reformulated_query: Optional[str] = Field(default=None, description="改写后的检索意图")
    strategy: RoutingStrategy = Field(default=RoutingStrategy.REFORMULATE)

class RoutingExhaustedError(RuntimeError):
    """重路由手段耗尽仍未找到合适技能。调用方应向用户明确报告，严禁静默降级到错误技能。"""

@dataclass
class RouterConfig:
    routing_threshold: int = 30   # 授权技能数不超过该值时关闭路由（全量披露成本更低）
    top_k: int = 8
    expand_factor: int = 3
    max_reroute_attempts: int = 2

class SkillRouter:
    """
    轻量级技能路由器：完成 L0 -> L1 晋升。
    不变式一：权限硬过滤永远先于语义软排序；
    不变式二：成本守恒，小规模技能集合自动绕过路由。
    """
    def __init__(self, registry: LocalSkillRegistry, embedding_provider: EmbeddingProvider,
                 vector_index: VectorIndex, config: Optional[RouterConfig] = None):
        self.registry = registry
        self.embedding_provider = embedding_provider
        self.vector_index = vector_index
        self.config = config or RouterConfig()

    def _authorized_references(self, bound_skill_names: List[str]) -> List[SkillReference]:
        references: List[SkillReference] = []
        for name in bound_skill_names:
            ref = self.registry.get_reference(name)
            if ref is not None:
                references.append(ref)
        return references

    def _reroute_counter_key(self, context: AgentContext) -> str:
        return f"skill_reroute_count:{context.current_agent_id}"

    def _full_scan_used_key(self, context: AgentContext) -> str:
        return f"skill_full_scan_used:{context.current_agent_id}"

    def reset_reroute_state(self, context: AgentContext) -> None:
        """新任务下发前由编排层调用，重置重路由计数与兜底标记。"""
        context.variables.pop(self._reroute_counter_key(context), None)
        context.variables.pop(self._full_scan_used_key(context), None)

    async def route(self, query: str, bound_skill_names: List[str]) -> List[SkillMetadata]:
        """首次路由：权限硬过滤 -> 钉住技能直通 -> 语义检索 Top-K。"""
        authorized = self._authorized_references(bound_skill_names)
        pinned = [ref.metadata for ref in authorized if ref.metadata.pinned]

        # 成本守恒：技能规模未超阈值时，全量披露的 Token 成本低于路由成本
        if len(authorized) <= self.config.routing_threshold:
            return [ref.metadata for ref in authorized]

        routable = [ref for ref in authorized if not ref.metadata.pinned]
        routed = await self._search_top_k(query, routable, self.config.top_k)
        return pinned + routed

    async def reroute(self, query: str, bound_skill_names: List[str],
                      request: RerouteRequest, context: AgentContext) -> List[SkillMetadata]:
        """
        Reflection 重路由升级阶梯：
        1. REFORMULATE: 采用 LLM 改写后的检索意图，同 K 重路由；
        2. EXPAND_POOL: 候选池扩大为 K * expand_factor；
        3. FULL_SCAN: 全量披露授权技能，终局兜底，每任务仅允许一次。
        前两级受 max_reroute_attempts 计数限制，防止"重路由->仍不匹配"死循环。
        """
        authorized = self._authorized_references(bound_skill_names)
        pinned = [ref.metadata for ref in authorized if ref.metadata.pinned]

        if request.strategy is RoutingStrategy.FULL_SCAN:
            if context.variables.get(self._full_scan_used_key(context), False):
                raise RoutingExhaustedError("全量兜底已使用过，仍未找到合适技能")
            context.variables[self._full_scan_used_key(context)] = True
            return [ref.metadata for ref in authorized]

        counter_key = self._reroute_counter_key(context)
        attempts = int(context.variables.get(counter_key, 0))
        if attempts >= self.config.max_reroute_attempts:
            raise RoutingExhaustedError(
                f"重路由次数已耗尽 ({self.config.max_reroute_attempts})，未找到合适技能: {request.reason}"
            )
        context.variables[counter_key] = attempts + 1

        effective_query = request.reformulated_query or query
        top_k = self.config.top_k
        if request.strategy is RoutingStrategy.EXPAND_POOL:
            top_k = self.config.top_k * self.config.expand_factor

        routable = [ref for ref in authorized if not ref.metadata.pinned]
        routed = await self._search_top_k(effective_query, routable, top_k)
        return pinned + routed

    async def _search_top_k(self, query: str, candidates: List[SkillReference],
                            top_k: int) -> List[SkillMetadata]:
        if not candidates:
            return []
        query_vector = (await self.embedding_provider.embed([query]))[0]
        allowed_names = [ref.metadata.name for ref in candidates]
        hits = self.vector_index.search(query_vector, top_k, allowed_skill_names=allowed_names)

        # 一个技能对应多条语料条目：按技能维度归并，取最高分后降序排列
        best_scores: Dict[str, float] = {}
        for skill_name, score in hits:
            if score > best_scores.get(skill_name, float("-inf")):
                best_scores[skill_name] = score

        ranked_names = sorted(best_scores, key=best_scores.get, reverse=True)[:top_k]
        metadata_by_name = {ref.metadata.name: ref.metadata for ref in candidates}
        return [metadata_by_name[name] for name in ranked_names if name in metadata_by_name]
```

---

### 三、 框架优势总结

1. **渐进式披露 (Progressive Disclosure)**：
   * 信息按决策阶段分三级暴露：L1 元数据常驻供 LLM 判断"要不要用"；L2 说明文档在调用决策后、代码加载前以纯文本注入，供 LLM 深化"怎么正确用"；L3 实现代码仅在真正执行时瞬态载入。
   * 认知成本与执行成本解耦：LLM 可以在不付出任何 `import` 代价的前提下获取完整用法说明，避免了"想深入了解就必须执行"的两级跳变。
2. **执行隔离与无状态性（拒绝内存维度的过度设计）**：
   * 本框架明确拒绝"为节省本地内存而设计加载/卸载机制"的过度设计：百级技能的完整定义序列化后仅数百 KB 至 1-2 MB，相对 Python 进程数十 MB 基线、向量数据库数百 MB 至 GB 级索引、本地 Embedding/Reranker 模型 GB 级显存占用可忽略不计。LLM 应用的计算瓶颈在云端（GPU/Token），而非本地内存条。
   * 懒加载的真正价值：启动期通过 `LazySkillLoader` 仅读取 `.json` 元数据，不 `import` 任何技能代码，规避 import 副作用与启动期执行任意代码的安全风险，同时保证启动速度不随技能数量退化。
   * 瞬态执行的真正价值：通过 `TransientSkillExecutor` 在每次执行后从 `sys.modules` 卸载动态模块并执行 `gc.collect()`，杜绝技能代码污染全局命名空间与跨技能状态泄漏，并保证技能代码热更新即时生效——这是正确性与可维护性收益，而非内存收益。
3. **Sub-agent 的非工具化**：
   * Sub-agents 作为独立角色被注册在 `LocalAgentRegistry`，其行为和角色分工清晰地暴露给 Master Agent 用于做任务规划。
   * 每个 Sub-agent 与其被允许使用的 `bound_skills` 在静态元数据上进行了绑定。执行器在接收到调用申请时，会校验当前 `current_agent_id` 的调用权限，确保了多智能体环境下的隔离和安全性。
4. **轻量级路由与自愈式重路由**：
   * 技能规模超过阈值后自动启用 L0→L1 路由：权限硬过滤前置、语义软排序后置，仅 Top-K 候选进入 LLM 上下文，使上下文开销在千级技能规模下依然恒定；关键技能通过 `pinned` 钉住绕过路由，兜底召回。
   * 离线 HyDE 语料（LLM 生成的假设性问题）弥合口语化提问与技术性描述的语义鸿沟，提升首次召回率；在线三级 Reflection 重路由阶梯（改写查询→扩大候选池→全量兜底）配合重试计数上限与结构化信号，确保重路由可审计且不陷入死循环。