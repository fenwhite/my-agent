
import signal
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from rag_agent.core.factory import ServiceFactory
from rag_agent.core.services.prompt_registry import PromptRegistry
from rag_agent.infrastructure.tts import TTSManager

app = typer.Typer(help="交互式对话模式")
console = Console()

tts_manager = TTSManager()

def singal_handler(sig, frame):
    console.print("\n[yellow]⚠ 会话已中断。输入 /exit 彻底退出，或直接开始新对话。 [/yellow]")
    global chat_service
    chat_service = ServiceFactory.get_chat_service()


@app.command()
def start():

    global chat_service
    chat_service = ServiceFactory.get_chat_service()

    signal.signal(singal.SIGINT, singal_handler)

    console.print("\n[bold cyan]╓══════════════════════════╖[/bold cyan]")
    console.print("[bold cyan]║    RAG Agent Chat mode   ║[/bold cyan]")
    console.print("[bold cyan]║                          ║[/bold cyan]")
    console.print("[bold cyan]╙══════════════════════════╜[/bold cyan]")

    should_exit = False

    while not should_exit:
        try:
            voice_status = "[🔊ON]" if tts_manager.is_enableed else "[🔈OFF]"
            user_input = Prompt.ask(f"{voice_status} >>>")

            if user_input.start_with('/'):
                cmd_result = handler_command(user_input.strip())
                if cmd_result == 'exit':
                    should_exit = True
                continue

            if not user_input.strip():
                continue
            
            result = chat_service.chat(user_input)

            if result.get("session_ended"):
                console.print(f"\n[bold yellow]{result['content']}[/bold yellow]")
                chat_service.clear_history()
                continue

            console.print("\n[bold green]AI:[/bold green]")
            console.print(result["content"])

            if result["tool_calls"]:
                console.print("\n[yellow]🛠 工具调用:[/yellow]")
                for tc in result["tool_calls"]:
                    console.print(f"  - {tc['name']}: {tc['arguments']}")

            if tts_manager.is_enableed:
                tts_manager.speak(result["content"])

        except EOFError:
            console.print("\n再见!👋")
            break
        except Exception as e:
            console.print(f"[red]错误:[/red] {e}")

def handler_command(cmd: str) -> str:
    parts = cmd.split()
    command = parts[0].lower()

    if command == '/voice':
        if len(parts) < 2:
            console.print("用法: /voice on | /voice off")
            return 'continue'
            
        action = parts[1].lower()
        if action == 'on':
            tts_manager.enable()
        elif action == 'off':
            tts_manager.disable()
        else:
            console.print("用法: /voice on | /voice off")
    elif command == '/session':
        console.print(f"当前会话 ID: {chat_service.session_id}")

    elif command == '/clear':
        chat_service.clear_history()
        console.print("[green]√ 对话历史已清空[/green]")

    elif command == '/help':
        show_help()

    elif command == '/prompt':
        return handle_prompt_command(parts)

    elif command == '/exit' or  command == '/quit':
        console.print("再见!👋")
        tts_manager.shutdown()
        return 'exit'

    else:
        console.print(f"[red]未知命令:[/red] {command}, 输入 /help 查看帮助")

    return 'continue'

def handle_prompt_command(parts: list[str]) -> str:
    if len(parts) < 2:
        console.print("用法:")
        console.print(" /prompt list             - 列出所有可用的 prompt")
        console.print(" /prompt show <name>      - 显示指定 prompt 内容")
        console.print(" /prompt switch <name>    - 切换到指定 prompt")
        console.print(" /prompt current          - 显示当前激活的 prompt")

        subcmd = parts[1].lower()

        try:
            registry = PromptRegistry.get_instance()
            if subcmd == 'list':
                available = registry.list_available()
                current = registry.current_name

                if not available:
                    console.print("[yellow]警告:[/yellow] 没有可用的 prompt")
                    return 'continue'
                
                table = Table(title="可用 prompt 列表")
                table.add_column("名称", style="cyan")
                table.add_column("状态", style="green")

                for name in available:
                    status = "√ 当前" if name == current else ""
                    table.add_row(name, status)
                
                console.print(table)

            elif subcmd == 'show':
                if len(parts) < 3:
                    console.print("[red]错误:[/red] 请指定 prompt 名称")
                    console.print("用法: /prompt show <name>")
                    return 'continue'
                
                name = parts[2]
                content = registry.get(name)
                console.print(f"\n[bold cyan]Prompt: {name}[/bold cyan]\n")
                console.print(content)
                console.print()

            elif subcmd == 'switch':
                if len(parts) < 3:
                    console.print("[red]错误:[/red] 请指定要切换的 prompt 名称")
                    console.print("用法: /prompt switch <name>")
                    return 'continue'
                
                name = parts[2]
                registry.switch(name)
                console.print(f"[green]√[/green] 已切换到 prompt: [bold] {name} [/bold]")

            elif subcmd == 'current':
                current = registry.current_name
                console.print(f"当前 prompt:[bold green]{current}[/bold green]")

            else:
                console.print(f"[red]未知子命令:[/red] {subcmd}")
                console.print("可用子命令: list, show, switch, current")

        except Exception as e:
            console.print(f"[red]错误:[/red] {str(e)}")

        return 'continue'
        

def show_help():
    console.print("\n[bold]可用命令:[/bold]")
    console.print("[cyan]/voice on[/cyan]               - 启用语音输出")
    console.print("[cyan]/voice off[/cyan]              - 禁用语音输出")
    console.print("[cyan]/session[/cyan]                - 显示当前会话ID")
    console.print("[cyan]/clear[/cyan]                  - 清空对话历史")
    console.print("[cyan]/help[/cyan]                   - 显示此帮助信息")
    console.print("[cyan]/prompt list[/cyan]            - 列出所有可用的 prompt")
    console.print("[cyan]/prompt show <name>[/cyan]     - 显示指定 prompt 内容")
    console.print("[cyan]/prompt switch <name>[/cyan]   - 切换到指定 prompt")
    console.print("[cyan]/prompt current[/cyan]         - 显示当前激活的 prompt")
    console.print("[cyan]/exit[/cyan]                   - 退出程序")
    console.print()