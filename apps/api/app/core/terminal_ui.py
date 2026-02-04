"""
Terminal UI utilities for console output
"""
from rich.console import Console
from rich.panel import Panel


class TerminalUI:
    """Rich-based terminal UI helper"""

    def __init__(self):
        self.console = Console()

    def info(self, message: str, title: str = ""):
        """Print info message"""
        prefix = f"[{title}] " if title else ""
        self.console.print(f"[blue]ℹ[/blue] {prefix}{message}")

    def success(self, message: str, title: str = ""):
        """Print success message"""
        prefix = f"[{title}] " if title else ""
        self.console.print(f"[green]✓[/green] {prefix}{message}")

    def warning(self, message: str, title: str = ""):
        """Print warning message"""
        prefix = f"[{title}] " if title else ""
        self.console.print(f"[yellow]⚠[/yellow] {prefix}{message}")

    def error(self, message: str, title: str = ""):
        """Print error message"""
        prefix = f"[{title}] " if title else ""
        self.console.print(f"[red]✗[/red] {prefix}{message}")

    def debug(self, message: str, title: str = ""):
        """Print debug message"""
        prefix = f"[{title}] " if title else ""
        self.console.print(f"[dim]🔍 {prefix}{message}[/dim]")

    def panel(self, content: str, title: str = "", style: str = "blue"):
        """Print a panel"""
        self.console.print(Panel(content, title=title, style=style))

    def status_line(self, info: dict):
        """Print status line"""
        items = [f"{k}: {v}" for k, v in info.items()]
        self.console.print(" | ".join(items))

    def ascii_logo(self):
        """Print ASCII logo"""
        logo = """
    _   _                 _   _
   | \\ | |               | | | |
   |  \\| | _____      __ | |_| | ___  _ __ ___  ___
   | . ` |/ _ \\ \\ /\\ / / |  _  |/ _ \\| '__/ __|/ _ \\
   | |\\  |  __/\\ V  V /  | | | | (_) | |  \\__ \\  __/
   |_| \\_|\\___| \\_/\\_/   |_| |_|\\___/|_|  |___/\\___|

        AI Agent Development Platform
        """
        self.console.print(f"[cyan]{logo}[/cyan]")


ui = TerminalUI()
