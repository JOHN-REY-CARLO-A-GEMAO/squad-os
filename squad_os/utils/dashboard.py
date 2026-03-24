import sys
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.logging import RichHandler
import logging

console = Console()

class Dashboard:
    def __init__(self):
        self.console = console
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        self.layout["body"].split_row(
            Layout(name="main", ratio=2),
            Layout(name="status", ratio=1)
        )

        self.header_panel = Panel(Text("SquadOS Mission Control", style="bold magenta", justify="center"))
        self.footer_panel = Panel(Text("Ready", style="dim", justify="center"))
        self.main_content = Text()
        self.status_content = Text()

    def update_header(self, mission_goal: str):
        self.header_panel = Panel(Text(f"Mission: {mission_goal}", style="bold cyan", justify="center"))

    def log_thought(self, agent_role: str, thought: str):
        self.main_content.append(f"\n[{agent_role}] Thinking: ", style="bold yellow")
        self.main_content.append(f"{thought}\n", style="italic white")

    def log_tool_call(self, agent_role: str, tool_name: str, args: str):
        self.main_content.append(f"[{agent_role}] Calling Tool: ", style="bold green")
        self.main_content.append(f"{tool_name}({args})\n", style="cyan")

    def log_status(self, agent_role: str, status: str):
        self.status_content.append(f"• {agent_role}: {status}\n", style="bold blue")

    def get_layout(self):
        self.layout["header"].update(self.header_panel)
        self.layout["main"].update(Panel(self.main_content, title="Mission Progress"))
        self.layout["status"].update(Panel(self.status_content, title="Agent Status"))
        self.layout["footer"].update(self.footer_panel)
        return self.layout

dashboard = Dashboard()

def setup_rich_logging():
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)]
    )
