"""Orchestra command for multi-agent orchestration."""

import asyncio
import typer

from my_agent.core.factory import ServiceFactory

app = typer.Typer(help="多智能体编排模式 - 使用 Planner-Scheduler-Executor 架构执行复杂任务")


@app.command()
def run(request: str = typer.Argument(..., help="用户请求描述")):
    """执行编排任务。
    
    使用 Orchestrator 将用户请求分解为多个子任务，
    通过多个 Sub-Agent 协作完成。
    
    示例:
        rag-agent orchestra "帮我分析退款逻辑"
    """
    orchestrator = ServiceFactory.get_orchestrator()
    
    async def _run() -> None:
        result = await orchestrator.run(request)
        
        if result.success:
            typer.echo(f"✅ 编排执行成功")
            typer.echo(f"会话 ID: {result.state.session_id}")
            typer.echo(f"任务数: {len(result.state.task_dag)}")
            for task_id, node in result.state.task_dag.items():
                typer.echo(f"  - {task_id}: {node.agent} ({node.status})")
        else:
            typer.echo(f"❌ 编排执行失败: {result.error}")
            typer.echo(f"会话 ID: {result.state.session_id}")
    
    asyncio.run(_run())
