"""
Terminal tools — run shell commands.
This is what makes the agent able to: npm install, git, python, etc.
"""
import subprocess
from langchain_core.tools import tool


@tool
def run_command(command: str) -> str:
    """Run a shell command and return its output (stdout + stderr).
    Use this for: installing packages, running scripts, git operations, etc.
    The working directory is the workspace folder."""
    import pathlib
    workspace = pathlib.Path(__file__).parent.parent / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Block dangerous commands
    dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb"]
    for d in dangerous:
        if d in command:
            return f"❌ BLOCKED: Dangerous command detected: {command}"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(workspace)
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        if not output:
            output = "(command completed with no output)"
        # Truncate very long output
        if len(output) > 5000:
            output = output[:2500] + "\n\n... (truncated) ...\n\n" + output[-2500:]
        return f"$ {command}\n{output}\nExit code: {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"❌ Command timed out after 60 seconds: {command}"
    except Exception as e:
        return f"❌ Error running command: {e}"
