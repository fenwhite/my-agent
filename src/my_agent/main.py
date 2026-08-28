
import typer

from my_agent.cli.commands import chat_cmd, config_cmd, orchestra_cmd
from my_agent.config.settings import get_settings
from my_agent.core.services.prompt_registry import PromptRegistry
from my_agent.utils.logging import setup_logging

setup_logging()

settings = get_settings()


# 初始化 PromptRegistry
settings = get_settings()
registry = PromptRegistry.get_instance()
registry.initialize(prompts_dir=__import__('pathlib').Path(settings.prompt_dir), default_prompt=settings.default_prompt)

# 初始化工具系统
if settings.enable_tools:
    from my_agent.core.tools import initialize_tools
    initialize_tools()


app = typer.Typer(
    name = "my-agent",
    help = "Agent CLI",
    add_completion = False,
)

app.add_typer(orchestra_cmd.app, name="orchestra", help="多智能体编排模式")
app.add_typer(chat_cmd.app, name="chat",help="交互式对话模式")
app.add_typer(config_cmd.app, name="config",help="配置管理")
# app.add_typer(index_cmd.app, name="index",help="文档索引")

if __name__ == "__main__":
    app()