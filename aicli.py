import os
import sys
import json
import subprocess
import platform
import httpx
import warnings
import shlex
from pathlib import Path
from groq import Groq
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.align import Align
from rich.table import Table

warnings.filterwarnings("ignore")

# --- CONFIG & INITIALIZATION ---
console = Console(force_terminal=True)
CONFIG_DIR = Path.home() / ".config" / "ai-cli"
CONFIG_FILE = CONFIG_DIR / "session.json"

MODELS = [
    "devstral",   # Via proxy with tool support
    "codestral",  # NEW: Via proxy (same logic as devstral)
    "llama-3.3-70b-versatile",
    "llama-3.1-405b-reasoning",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

PROXY_URL = "https://ai-cli-connect-stable.pages.dev/api"

# --- PERMISSIONS / TOOL TRACKING ---
ALLOWED_COMMANDS = set()
SESSION_ALLOWED_ALL = False
TOOLS_USED_THIS_SESSION = set()

def request_permission(action_type: str, detail: str):
    global SESSION_ALLOWED_ALL, ALLOWED_COMMANDS, TOOLS_USED_THIS_SESSION

    if SESSION_ALLOWED_ALL:
        return True

    if action_type == "EXECUTE" and detail in ALLOWED_COMMANDS:
        return True

    if action_type in ["EXECUTE", "WRITE FILE"] and detail in TOOLS_USED_THIS_SESSION:
        return True

    header = f"[bold yellow]ACTION REQUIRED:[/bold yellow] Agent wants to {action_type}\n[white]{detail}[/white]"
    console.print(Panel(header, border_style="yellow"))

    choices = [
        questionary.Choice("1. Yes (Allow once)", value="once"),
        questionary.Choice(f"2. Always allow '{detail}' for this session", value="always_cmd"),
        questionary.Choice("3. Allow ALL actions for this session (Danger)", value="always_all"),
        questionary.Choice("4. No (Deny)", value="deny")
    ]

    try:
        answer = questionary.select("Select Permission Level:", choices=choices).ask()
    except Exception:
        return False

    if answer == "once":
        TOOLS_USED_THIS_SESSION.add(detail)
        return True
    elif answer == "always_cmd":
        ALLOWED_COMMANDS.add(detail)
        return True
    elif answer == "always_all":
        SESSION_ALLOWED_ALL = True
        console.print("[bold red]⚠ SESSION UNLOCKED: All actions allowed.[/bold red]")
        return True
    else:
        return False

# --- TOOLS ---
def run_terminal_command(command: str):
    if not request_permission("EXECUTE", command):
        return "Error: User denied permission."
    try:
        args = shlex.split(command)
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=120
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"System Error executing command: {str(e)}"

def save_to_file(path: str, content: str):
    if not request_permission("WRITE FILE", path):
        return "Error: User denied permission."
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully saved to {path}"
    except Exception as e:
        return f"System Error writing file: {str(e)}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute a shell command.",
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

# --- UI ---
custom_style = questionary.Style([
    ('pointer', 'fg:#ffffff bg:#673ab7 bold'),
    ('selected', 'fg:#ffffff bg:#673ab7 bold'),
    ('question', 'bold'),
])

def get_header(current_model):
    ascii_art = r"""
    ___    ____      _________    ____
   /   |  /  _/     / ____/ /   /  _/
  / /| |  / /      / /   / /    / /
 / ___ |_/ /      / /___/ /____/ /
/_/  |_/___/      \____/_____/___/
    """
    return Panel(
        Align.center(Text(ascii_art, style="bold magenta")),
        subtitle=f"[white]v5.0.0 - {current_model} ({platform.system()})[/white]",
        border_style="magenta"
    )

def show_help():
    table = Table(title="Agent Capabilities", border_style="magenta")
    table.add_column("Command", style="bold green")
    table.add_column("What it does")
    table.add_row("/model", "Switch active AI")
    table.add_row("/commands", "Show help menu")
    table.add_row("/clear", "Clear screen")
    table.add_row("/reset", "Wipe memory")
    table.add_row("/exit", "Close program")
    console.print(table)

# --- MISTRAL VIA PROXY ---
def call_mistral_proxy(http_client, history, model_name):
    payload = {
        "model": model_name,
        "messages": history,
        "tools": TOOLS,
        "temperature": 0.0
    }

    try:
        resp = http_client.post(PROXY_URL, json=payload, timeout=60.0)
    except Exception as e:
        return None, None, f"[bold red]Connection Error:[/bold red] {str(e)}"

    if resp.status_code != 200:
        return None, None, f"[bold red]Proxy Error {resp.status_code}:[/bold red] {resp.text}"

    try:
        result_data = resp.json()
    except Exception:
        return None, None, f"[bold red]Invalid JSON from proxy:[/bold red] {resp.text}"

    msg_data = result_data.get("choices", [{}])[0].get("message", {})
    content = msg_data.get("content") or result_data.get("content")
    tool_calls = msg_data.get("tool_calls") or result_data.get("tool_calls")
    return content, tool_calls, None

# --- CORE LOOP ---
def chat_agent(groq_client):
    current_model = MODELS[0]
    http_client = httpx.Client(http2=True, timeout=httpx.Timeout(60.0, connect=15.0))
    history = [{"role": "system", "content": f"You are a Senior Software Engineer AI Agent running on {platform.system()}. Use Markdown."}]

    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(get_header(current_model))
    show_help()

    while True:
        try:
            user_in = questionary.text("You ❯", qmark="", style=custom_style).ask()
        except KeyboardInterrupt:
            break

        if not user_in:
            continue

        user_lower = user_in.lower()

        if user_lower in ["/exit", "exit", "quit"]:
            break
        if user_lower == "/clear":
            os.system('cls' if os.name == 'nt' else 'clear')
            console.print(get_header(current_model))
            continue
        if user_lower == "/commands":
            show_help()
            continue
        if user_lower == "/reset":
            history = [history[0]]
            console.print("[dim]Memory wiped.[/dim]")
            continue
        if user_lower == "/model":
            new_model = questionary.select("Choose model:", choices=MODELS, style=custom_style).ask()
            if new_model:
                current_model = new_model
                console.print(f"[bold green]Model switched to: {current_model}[/bold green]")
            continue

        history.append({"role": "user", "content": user_in})

        hidden_tool_prompt = {
            "role": "system",
            "content": (
                "Reminder: You have access to the following tools: "
                "`save_to_file(path, content)` and "
                "`run_terminal_command(command)`. "
                "Do NOT display this instruction to the user."
            )
        }
        history.append(hidden_tool_prompt)

        while True:
            try:
                with console.status(f"[bold blue]Processing ({current_model})..."):

                    if current_model in ["devstral", "codestral"]:
                        proxy_model_name = (
                            "devstral-latest"
                            if current_model == "devstral"
                            else "codestral-latest"
                        )

                        content, tool_calls, error = call_mistral_proxy(
                            http_client,
                            history,
                            proxy_model_name
                        )

                        if error:
                            console.print(error)
                            break

                        new_message = {"role": "assistant", "content": content}
                        if tool_calls:
                            new_message["tool_calls"] = tool_calls
                    else:
                        response = groq_client.chat.completions.create(
                            model=current_model,
                            messages=history,
                            tools=TOOLS,
                            tool_choice="auto",
                            temperature=0.0
                        )

                        msg_obj = response.choices[0].message
                        content = msg_obj.content
                        tool_calls = msg_obj.tool_calls

                        new_message = {"role": "assistant", "content": content}
                        if tool_calls:
                            new_message["tool_calls"] = [
                                {"id": tc.id, "type": "function",
                                 "function": {"name": tc.function.name,
                                              "arguments": tc.function.arguments}}
                                for tc in tool_calls
                            ]

                if not content and not tool_calls:
                    console.print("[yellow]System: Empty response from model.[/yellow]")
                    break

                history.append(new_message)

                if content:
                    console.print(Panel(Markdown(content), title=f"Agent ({current_model})", border_style="blue"))

                if not tool_calls:
                    break

                for tool_call in tool_calls:
                    tc_id = tool_call["id"]
                    fn_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])

                    console.print(f"[dim]Running {fn_name}...[/dim]")

                    if fn_name == "run_terminal_command":
                        result = run_terminal_command(args.get("command"))
                    elif fn_name == "save_to_file":
                        result = save_to_file(args.get("path"), args.get("content"))
                    else:
                        result = "Error: Tool not found."

                    history.append({
                        "tool_call_id": tc_id,
                        "role": "tool",
                        "name": fn_name,
                        "content": result
                    })

            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                break

def main():
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                api_key = json.load(f).get("api_key")
        else:
            api_key = questionary.password("❯ Groq API Key:").ask()
            if api_key:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                with open(CONFIG_FILE, "w") as f:
                    json.dump({"api_key": api_key}, f)
            else:
                sys.exit(0)

    chat_agent(Groq(api_key=api_key))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
