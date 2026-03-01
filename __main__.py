import os
import sys
import json
import subprocess
import platform
from pathlib import Path
from groq import Groq
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.align import Align
from rich.table import Table

# --- CONFIG & INITIALIZATION ---
console = Console(force_terminal=True)
CONFIG_DIR = Path.home() / ".config" / "ai-cli"
CONFIG_FILE = CONFIG_DIR / "session.json"
MODEL = "llama-3.3-70b-versatile"

# Session-level permissions memory
ALLOWED_COMMANDS = set()
SESSION_ALLOWED_ALL = False

# --- PERMISSION ENGINE ---

def request_permission(action_type: str, detail: str):
    """
    Advanced multi-option permission handler.
    Navigable via Arrow Keys or Numbers (1, 2, 3, 4).
    """
    global SESSION_ALLOWED_ALL, ALLOWED_COMMANDS

    if SESSION_ALLOWED_ALL:
        return True

    if action_type == "EXECUTE" and detail in ALLOWED_COMMANDS:
        return True

    # Clear any active status/spinners before prompting to prevent terminal crashes
    header = f"[bold yellow]ACTION REQUIRED:[/bold yellow] Agent wants to {action_type}\n[white]{detail}[/white]"
    console.print(Panel(header, border_style="yellow"))

    choices = [
        questionary.Choice("1. Yes (Allow once)", value="once"),
        questionary.Choice(f"2. Always allow '{detail}' for this session", value="always_cmd"),
        questionary.Choice("3. Allow ALL actions for this session (Danger)", value="always_all"),
        questionary.Choice("4. No (Deny)", value="deny")
    ]

    try:
        answer = questionary.select(
            "Select Permission Level:",
            choices=choices,
            style=questionary.Style([('selected', 'fg:#ffffff bg:#673ab7 bold')])
        ).ask()
    except Exception:
        # Fallback if questionary fails in a specific terminal env
        return False

    if answer == "once":
        return True
    elif answer == "always_cmd":
        if action_type == "EXECUTE":
            ALLOWED_COMMANDS.add(detail)
        return True
    elif answer == "always_all":
        SESSION_ALLOWED_ALL = True
        console.print("[bold red]⚠ SESSION UNLOCKED:[/bold red] All actions allowed until exit.")
        return True
    else:
        return False

# --- TOOLS ---

def run_terminal_command(command: str):
    if not request_permission("EXECUTE", command):
        return "Error: User denied permission."
    try:
        # Using a slightly longer timeout and explicit shell
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def save_to_file(path: str, content: str):
    if not request_permission("WRITE FILE", path):
        return "Error: User denied permission."
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute a shell command on the host OS.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_file",
            "description": "Create or modify a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    }
]

# --- UI STYLING ---
custom_style = questionary.Style([
    ('pointer', 'fg:#ffffff bg:#673ab7 bold'), 
    ('selected', 'fg:#ffffff bg:#673ab7 bold'), 
    ('question', 'bold'),
])

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
        subtitle=f"[white]v4.3.0 - Hardened Agent ({platform.system()})[/white]", 
        border_style="magenta"
    )

def show_help():
    table = Table(title="Agent Capabilities", border_style="magenta")
    table.add_column("Command", style="bold green")
    table.add_column("What it does")
    table.add_row("/commands", "Show this help menu")
    table.add_row("/clear", "Clear screen")
    table.add_row("/reset", "Wipe AI memory")
    table.add_row("/exit", "Close program")
    console.print(table)

# --- CORE LOGIC ---

def chat_agent(client):
    # REBALANCED SYSTEM PROMPT: 
    # Tells the AI it is a conversational assistant that HAS tools, 
    # not a tool-only engine.
    history = [
        {"role": "system", "content": (
            f"You are a helpful and intelligent Terminal AI Agent running on {platform.system()}. "
            "You can talk to the user and perform tasks using your tools. "
            "ONLY use a tool if the user explicitly asks for an action (like running a command or saving a file). "
            "For greetings or general questions, respond naturally without calling any tools. "
            "When you DO use a tool, do not wrap it in tags or explain the code first; just trigger the tool."
        )}
    ]
    
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(get_header())
    show_help()

    while True:
        try:
            user_in = questionary.text("You ❯", qmark="", style=custom_style).ask()
        except KeyboardInterrupt:
            break
            
        if not user_in: continue
        
        if user_in.lower() == "/exit": break
        if user_in.lower() == "/clear":
            os.system('cls' if os.name == 'nt' else 'clear')
            console.print(get_header())
            continue
        if user_in.lower() == "/commands":
            show_help()
            continue
        if user_in.lower() == "/reset":
            history = [history[0]]
            console.print("[dim]Memory wiped.[/dim]")
            continue

        history.append({"role": "user", "content": user_in})

        while True:
            try:
                with console.status("[bold blue]Thinking...") as status:
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=history,
                        tools=TOOLS,
                        tool_choice="auto",
                        temperature=0.1
                    )
                
                message = response.choices[0].message
                history.append(message)

                # If there's content, print it (this fixes the 'can you respond' issue)
                if message.content:
                    console.print(Panel(Markdown(message.content), title="[blue]Assistant[/blue]", border_style="blue"))

                if not message.tool_calls:
                    break

                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    if fn_name == "run_terminal_command":
                        result = run_terminal_command(args.get("command"))
                    elif fn_name == "save_to_file":
                        result = save_to_file(args.get("path"), args.get("content"))
                    else:
                        result = "Error: Tool not found."

                    history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": fn_name,
                        "content": result
                    })
            except Exception as e:
                err_str = str(e)
                if "tool_use_failed" in err_str:
                    if len(history) > 0: history.pop()
                    history.append({"role": "user", "content": "The tool call failed. If you were just trying to talk, please respond with text only. If you were trying to use a tool, please format the JSON correctly."})
                    continue
                
                console.print(f"[bold red]Error:[/bold red] {err_str}")
                break

def main():
    if os.environ.get("GROQ_API_KEY"):
        api_key = os.environ.get("GROQ_API_KEY")
    elif CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            api_key = json.load(f).get("api_key")
    else:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(get_header())
        setup_msg = "Go to: [bold cyan]https://console.groq.com/keys[/bold cyan]\nPaste your key to enable Auto-Connect."
        console.print(Panel(setup_msg, title="[yellow]Auth Required[/yellow]", border_style="yellow"))
        api_key = questionary.password("❯ API Key:").ask()
        if not api_key: sys.exit(0)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f: json.dump({"api_key": api_key}, f)

    chat_agent(Groq(api_key=api_key))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Exiting...[/dim]")
        sys.exit(0)