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

# --- TOOLS (Capabilities for the AI) ---

def run_terminal_command(command: str):
    """Executes a command in the user's terminal with permission."""
    console.print(Panel(f"[bold yellow]ACTION:[/bold yellow] Run Command\n[white]{command}[/white]", border_style="yellow"))
    if not questionary.confirm("Allow execution?").ask():
        return "Error: User denied permission to run this command."
    
    try:
        # Cross-platform: works on Linux, WSL, and Mac
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def save_to_file(path: str, content: str):
    """Creates a file or writes code to the local system."""
    console.print(Panel(f"[bold cyan]ACTION:[/bold cyan] Create/Update File\n[white]{path}[/white]", border_style="cyan"))
    if not questionary.confirm(f"Allow agent to write to {path}?").ask():
        return "Error: User denied file write permission."
    
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

# Define tools for the Groq API
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute any shell command (ls, git, python, mkdir, etc.)",
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
            "description": "Create a file or write code/text to a specific path.",
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
        subtitle=f"[white]v3.0.0 - Agent Mode ({platform.system()})[/white]", 
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
    table.add_row("Agentic tasks", "Ask: 'Create a python script that logs system info'")
    console.print(table)

# --- CORE LOGIC ---

def chat_agent(client):
    history = [
        {"role": "system", "content": f"You are a Terminal AI Agent running on {platform.system()}. "
                                     "You have permission to create files and run commands via tools. "
                                     "Always explain what you are about to do before calling a tool."}
    ]
    
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(get_header())
    show_help()

    while True:
        user_in = questionary.text("You ❯", qmark="", style=custom_style).ask()
        if not user_in: continue
        
        # Slash Commands
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

        # The Reasoning Loop (The "Gemini" magic)
        while True:
            with console.status("[bold blue]Agent Thinking..."):
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=history,
                    tools=TOOLS,
                    tool_choice="auto"
                )
            
            message = response.choices[0].message
            history.append(message)

            # Print text response if it exists
            if message.content:
                console.print(Panel(Markdown(message.content), title="[blue]Assistant[/blue]", border_style="blue"))

            # Handle Tool Calls
            if not message.tool_calls:
                break # No more actions, wait for user input

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
            # Loop continues so AI can see the result and respond

def main():
    # Show ASCII at the very beginning
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(get_header())

    # Get Client (Auto-connect logic)
    if os.environ.get("GROQ_API_KEY"):
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    elif CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            client = Groq(api_key=json.load(f).get("api_key"))
    else:
        # First-time Setup
        setup_msg = "Go to: [bold cyan]https://console.groq.com/keys[/bold cyan]\nPaste your key to enable Auto-Connect."
        console.print(Panel(setup_msg, title="[yellow]Auth Required[/yellow]", border_style="yellow"))
        key = questionary.password("❯ API Key:").ask()
        if not key: sys.exit(0)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f: json.dump({"api_key": key}, f)
        client = Groq(api_key=key)

    chat_agent(client)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)