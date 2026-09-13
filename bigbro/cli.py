"""Terminal chat with BigBro:  python -m bigbro.cli  (or: python -m bigbro.cli --once "build me X")"""

import argparse
import os
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .config import load_config
from .core import BigBro

console = Console()

BANNER = """[bold cyan]🕶️  BIGBRO[/bold cyan] — your personal full-stack developer agent
[dim]web · mobile · integration · backend — for you only[/dim]"""


def main():
    ap = argparse.ArgumentParser(description="Chat with BigBro in your terminal")
    ap.add_argument("--once", metavar="MESSAGE", help="Send one message, print the result, and exit")
    ap.add_argument("--provider", help="Override BIGBRO_PROVIDER (openai/anthropic/gemini/ollama/mock)")
    args = ap.parse_args()

    if args.provider:
        os.environ["BIGBRO_PROVIDER"] = args.provider

    cfg = load_config()
    try:
        bb = BigBro(cfg)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    console.print(Panel(BANNER, border_style="cyan"))
    console.print(
        f"[dim]brain: {cfg.provider}/{bb.provider.model} · workspace: {cfg.workspace} · "
        f"capabilities: {len(bb.caps)}[/dim]\n"
    )

    history = []

    def respond(message: str):
        nonlocal history
        history, reply, events = bb.run(message, history, session_id=bb.new_session_id() if not history else "")
        for ev in events:
            console.print(f"  [yellow]⚙ {ev.name}[/yellow] [dim]{(ev.detail or '').splitlines()[0][:140]}[/dim]")
        console.print(Markdown(reply))
        console.print()

    if args.once:
        respond(args.once)
        return

    while True:
        try:
            user = Prompt.ask("[bold]you[/bold]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]BigBro out. 🕶️[/dim]")
            break
        if not user.strip():
            continue
        if user.startswith("/"):
            if user in ("/exit", "/quit"):
                console.print("[dim]BigBro out. 🕶️[/dim]")
                break
            if user == "/new":
                history = []
                console.print("[dim]session cleared[/dim]")
            elif user == "/caps":
                t = Table(title="Capabilities")
                t.add_column("name", style="cyan")
                t.add_column("description")
                for c in bb.caps:
                    t.add_row(c.name, c.description[:100])
                console.print(t)
            else:
                console.print("[dim]commands: /new · /caps · /exit[/dim]")
            continue
        respond(user)


if __name__ == "__main__":
    main()
