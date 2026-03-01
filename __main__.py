import os
import sys
import json
import datetime
from pathlib import Path
from groq import Groq
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.align import Align
from rich.table import Table

console = Console(force_terminal=True)

# --- AUTO-CONNECT CONFIG ---
# Just like Gemini CLI, we store the session in a hidden config folder
CONFIG_DIR = Path.home() / ".config" / "ai-cli"
CONFIG_FILE = CONFIG_DIR / "session.json"

def get_session_client():
    """Attempts to auto-connect or guides the user through a 10-second setup."""
    # 1. Automatic Discovery (Environment Variable)
    if os.environ.get("GROQ_API_KEY"):
        return Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # 2. Automatic Discovery (Saved Local Session)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return Groq(api_key=data.get("api_key"))
        except:
            pass

    # 3. If no key found, provide a clickable link and setup
    console.print(get_header())
    setup_msg = (
        "[bold white]No Active Session Found.[/bold white]\n\n"
        "1. Go to: [bold cyan]https://console.groq.com/keys[/bold cyan]\n"
        "2. Create an API Key.\n"
        "3. Paste it below to enable [bold magenta]ai-cli[/bold magenta] permanently."
    )
    console.print(Panel(setup_msg, title="[bold yellow]Automatic Setup[/bold yellow]", border_style="yellow"))
    
    key = questionary.password("❯ Paste your API Key here:").ask()
    
    if key and key.startswith("gsk_"):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"api_key": key, "date": str(datetime.date.today())}, f)
        console.print("[bold green]✔ Authorized! Auto-connect is now enabled.[/bold green]\n")
        return Groq(api_key=key)
    else:
        console.print("[bold red]Error:[/bold red] Invalid key. Please restart and paste a valid Groq key.")
        sys.exit(1)

# --- UI STYLING ---
custom_style = questionary.Style([
    ('pointer', 'fg:#ffffff bg:#673ab7 bold'), 
    ('selected', 'fg:#ffffff bg:#673ab7 bold'), 
])

def get_header():
    ascii_art = r"""
    ___    ____      _________    ____
   /   |  /  _/     / ____/ /   /  _/
  / /| |  / /      / /   / /    / /  
 / ___ |_/ /      / /___/ /____/ /   
/_/  |_/___/      \____/_____/___/   
    """
    return Panel(Align.center(Text(ascii_art, style="bold magenta")), subtitle="[white]v2.5.0 - Pro Engine[/white]", border_style="magenta")

def show_commands():
    table = Table(title="Slash Commands", border_style="magenta")
    table.add_column("Command", style="bold green")
    table.add_column("Function")
    table.add_row("/commands", "List all commands")
    table.add_row("/clear", "Clear screen (keep context)")
    table.add_row("/reset", "Wipe AI memory")
    table.add_row("/save", "Save chat to file")
    table.add_row("/exit", "Back to main menu")
    console.print(table)

def chat_loop(client, model_id):
    history = [{"role": "system", "content": "You are a helpful AI. Format with Markdown."}]
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(get_header())
    console.print(f"[bold yellow]Authenticated:[/bold yellow] {model_id}\n")

    while True:
        user_in = questionary.text("You ❯", qmark="", style=custom_style).ask()
        
        if user_in is None or user_in.lower() == "/exit": break
        
        if user_in.lower() == "/commands":
            show_commands()
            continue
        elif user_in.lower() == "/clear":
            os.system('cls' if os.name == 'nt' else 'clear')
            console.print(get_header())
            continue
        elif user_in.lower() == "/reset":
            history = [{"role": "system", "content": "You are a helpful AI."}]
            console.print("[dim]Memory reset.[/dim]")
            continue

        if not user_in.strip(): continue

        history.append({"role": "user", "content": user_in})
        try:
            with console.status(f"[bold green]Processing..."):
                completion = client.chat.completions.create(messages=history, model=model_id)
                resp = completion.choices[0].message.content
            
            history.append({"role": "assistant", "content": resp})
            console.print(Panel(Markdown(resp), title=f"[blue]{model_id}[/blue]", border_style="blue", padding=(1,2)))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

def main():
    # Attempt automatic connection
    client = get_session_client()
    
    while True:
        action = questionary.select(
            "ai-cli Control Panel:",
            choices=['Chat', 'Logout', 'Exit'],
            style=custom_style,
            pointer='❯ '
        ).ask()

        if action == 'Chat':
            model = questionary.select(
                "Select Engine:",
                choices=[
                    questionary.Choice("Llama 3.3 70B", value="llama-3.3-70b-versatile"),
                    questionary.Choice("Llama 3.1 8B", value="llama-3.1-8b-instant"),
                    "Back"
                ],
                style=custom_style
            ).ask()
            if model != "Back": chat_loop(client, model)
        
        elif action == 'Logout':
            if CONFIG_FILE.exists():
                os.remove(CONFIG_FILE)
                console.print("[yellow]Logged out. Key removed from local storage.[/yellow]")
                sys.exit(0)
        
        elif action in ['Exit', None]:
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)