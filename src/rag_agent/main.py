
import typer

from rag_agent.config.settings import get_settings
from rag_agent.cli.commands import chat_cmd, config_cmd
from rag_agent.utils.logging import setup_logging

setup_logging()

settings = get_settings()

app = typer.Typer(
    name = "rag-agent",
    help = "RAG Agent CLI",
    add_completion = False,
)

app.add_typer(chat_cmd.app, name="chat",help="交互式对话模式")
app.add_typer(config_cmd.app, name="config",help="配置管理")
# app.add_typer(index_cmd.app, name="index",help="文档索引")

if __name__ == "__main__":
    app()