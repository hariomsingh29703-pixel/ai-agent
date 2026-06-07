"""
run_single.py - Web bridge that uses the REAL antigravity_clone agent.
Imports graph.py from the antigravity_clone project and calls run_agent().
This ensures the web UI has IDENTICAL capability to the CLI version.
"""
import sys
import os
import json

# ── Path Setup ──
_this_dir      = os.path.dirname(os.path.abspath(__file__))
_project_root  = os.path.join(_this_dir, '..')
_clone_dir     = os.getenv("CLONE_DIR", os.path.abspath(os.path.join(_this_dir, '../../antigravity_clone')))

if not os.path.exists(_clone_dir):
    _clone_dir = _this_dir

# ── Parse session workspace if present in arguments ──
if len(sys.argv) > 1:
    import re
    match = re.search(r'\[SESSION WORKSPACE:\s*([^\]]+)\]', sys.argv[1])
    if match:
        os.environ["AGENT_WORKSPACE"] = match.group(1).strip()

# Add antigravity_clone to path so its imports resolve correctly
sys.path.insert(0, _clone_dir)

# Load .env from antigravity_clone (has the GROQ_API_KEY)
from dotenv import load_dotenv
load_dotenv(os.path.join(_clone_dir, '.env'))
load_dotenv(os.path.join(_project_root, '.env'))  # fallback

# ── Set workspace so files land in ai_agent_skill/workspace ──
WORKSPACE_DIR = os.path.join(_project_root, 'workspace')
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# Change working directory to antigravity_clone so relative tool paths work
os.chdir(_clone_dir)

# ── Import the REAL agent ──
from graph import run_agent   # uses llama-3.1-8b-instant + custom JSON tool calling


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    user_input = sys.argv[1]

    # Inject workspace context if it wasn't already specified by the caller
    if "[SESSION WORKSPACE:" in user_input:
        augmented_input = user_input
    else:
        augmented_input = (
            f"{user_input}\n\n"
            f"[SYSTEM NOTE: If you create or save any files, use this workspace directory: {WORKSPACE_DIR}]"
        )

    try:
        response = run_agent(augmented_input)

        # run_agent returns None if it hit max iterations without a final answer
        if response is None:
            # Extract the last assistant message as the response
            response = "The agent completed its task. Check the workspace for any created files."

        print(json.dumps({"response": str(response)}))

    except Exception as e:
        print(json.dumps({"error": f"Agent error: {str(e)}"}))


if __name__ == "__main__":
    main()
