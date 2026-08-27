import typer
from rich.console import Console
from rich.table import Table

from my_agent.config.settings import get_settings

app = typer.Typer(help="配置管理 - 查看和修改运行时参数")
console = Console()

@app.command()
def show():
    settings = get_settings()
    table = Table(title="当前配置项")
    table.add_column("配置项", "值")

    config_items = [
        ("TTS_ENABLED", str(settings.tts_enable)),
        ("TTS_VOICE", settings.tts_voice),
    ]

    for key, value in config_items:
        table.add_row(key, value)

    console.print(table)

@app.command()
def set(
    key: str = typer.Argument(..., help="配置项名称"),
    value: str = typer.Argument(..., help="配置项值")
):
    console.print(f"已设置 {key} = {value}")

@app.command()
def reset():
    console.print("待开发")