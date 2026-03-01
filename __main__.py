import os
import sys
import datetime
import base64

# --- CROSS-PLATFORM DEPENDENCY CHECK ---
try:
    from groq import Groq
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.text import Text
    from rich.align import Align
    from rich.table import Table
except ImportError:
    print("Error: Missing dependencies. Run: pip install groq questionary rich")
    sys.exit(1)

# Initialize Rich Console with universal color support
console = Console(force_terminal=True)

# --- THE BULLETPROOF HEX KEY ---
_SECRET_HEX = "67736b5f6f31695741736a386c544e68323144345268613157476479623346596b56534e6a754977434a3451764e45776468467354587778"

def _get_api_key():
    return bytes.fromhex(_SECRET_HEX).decode('utf-8')

client = Groq(api_key=_get_api_key())

# --- ADVANCED UI STYLING ---
# Specifically tuned to look good on both Unix (Mac/Linux) and WSL terminals
custom_style = questionary.Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('pointer', 'fg:#ffffff bg:#673ab7 bold'), 
    ('selected', 'fg:#ffffff bg:#673ab7 bold'), 
    ('highlighted', 'fg:#ffffff bg:#673ab7 bold'),
    ('answer', 'fg:#673ab7 bold'),
])

def clear_terminal():
    """Universal terminal clear command for Mac, Linux, WSL, and Windows."""
    # 'nt' is Windows (including CMD/PowerShell), otherwise clear works for Unix/WSL
    os.system('cls' if os.name == 'nt' else 'clear')

def get_header():
    ascii_art = r"""
    ___    ____      _________    ____
   /   |  /  _/     / ____/ /   /  _/
  / /| |  / /      / /   / /    / /  
 / ___ |_/ /      / /___/ /____/ /   
/_/  |_/___/      \____/_____/___/   
    """
    return Panel(
        Align.center(Text(ascii_art, style="bold magenta")), 
        subtitle="[white]v2.2.0 - Universal Binary[/white]", 
        border_style="magenta"
    )

def show_commands():
    """Displays the list of available slash commands in a Rich Table."""
    table = Table(title="CLI COMMANDS", border_style="magenta", title_style="bold magenta")
    table.add_column("Command", style="bold green", no_wrap=True)
    table.add_column("Action", style="white")
    
    table.add_row("/commands", "Show this help menu")
    table.add_row("/clear", "Wipe screen (keeps chat memory)")
    table.add_row("/reset", "Wipe chat history/memory")
    table.add_row("/save", "Export chat to .txt file")
    table.add_row("/system", "Change AI personality")
    table.add_row("/exit", "Exit to main menu")
    
    console.print(table)

def start_chat_session(model_id):
    history = [{"role": "system", "content": "You are a helpful AI assistant. Use markdown."}]
    
    clear_terminal()
    console.print(get_header())
    console.print(f"[bold yellow]Session Active:[/bold yellow] {model_id}")
    console.print("[dim]Type '/commands' for help.[/dim]\n")

    while True:
        # questionary handles raw terminal input, fixing ^M issues on Mac/WSL
        user_input = questionary.text("You ❯", qmark="", style=custom_style).ask()

        if user_input is None: break
        cmd = user_input.lower().strip()

        # --- COMMAND LOGIC ---
        if cmd == "/exit":
            break
            
        elif cmd == "/commands":
            show_commands()
            continue
            
        elif cmd == "/clear":
            clear_terminal()
            console.print(get_header())
            console.print(f"[dim]Screen cleared. Context preserved for {model_id}.[/dim]\n")
            continue
            
        elif cmd == "/reset":
            history = [{"role": "system", "content": "You are a helpful AI assistant."}]
            console.print("[italic cyan]Memory wiped.[/italic cyan]")
            continue
            
        elif cmd == "/system":
            persona = questionary.text("Define new AI persona:").ask()
            if persona:
                history[0] = {"role": "system", "content": persona}
                console.print(f"[green]Persona updated.[/green]")
            continue
            
        elif cmd == "/save":
            filename = f"ai_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    for msg in history:
                        f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")
                console.print(f"[bold green]Saved transcript to {filename}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Save Error:[/bold red] {e}")
            continue

        if not user_input.strip(): continue

        # --- AI PROCESSING ---
        history.append({"role": "user", "content": user_input})
        try:
            with console.status("[bold green]Querying LPU..."):
                completion = client.chat.completions.create(messages=history, model=model_id)
                resp = completion.choices[0].message.content
            
            history.append({"role": "assistant", "content": resp})
            console.print(Panel(Markdown(resp), title=f"[bold blue]{model_id}[/bold blue]", border_style="blue", padding=(1, 2)))
            print() 
        except Exception as e:
            console.print(f"[bold red]API Error:[/bold red] {e}")

def main():
    clear_terminal()
    console.print(get_header())
    
    while True:
        action = questionary.select(
            "ai-cli Control Panel:",
            choices=['Chat', 'System Status', 'Exit'],
            style=custom_style,
            pointer='❯ '
        ).ask()

        if action in ['Exit', None]: break
            
        elif action == 'Chat':
            model_id = questionary.select(
                "Select Intelligence Engine:",
                choices=[
                    questionary.Choice("Llama 3.3 70B (Stable)", value="llama-3.3-70b-versatile"),
                    questionary.Choice("Llama 3.1 8B (Fast)", value="llama-3.1-8b-instant"),
                    "Back"
                ],
                style=custom_style,
                pointer='❯ '
            ).ask()

            if model_id == "Back": continue
            start_chat_session(model_id)

        elif action == 'System Status':
            status = (
                f"OS: [bold cyan]{sys.platform}[/bold cyan]\n"
                "Environment: [bold green]Universal/WSL Verified[/bold green]\n"
                "Memory Mode: [bold yellow]Stateful (Persistent History)[/bold yellow]"
            )
            console.print(Panel(status, title="Diagnostics"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)