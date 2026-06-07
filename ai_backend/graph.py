"""
Antigravity Clone — LangGraph Agent
Same architecture as ai_agent/graph.py but with:
  - Direct LLM tool calling (NOT create_react_agent — it breaks on Groq)
  - ALL tools (files, terminal, browser, search)
  - Self-correction: loops until task is done
"""
import os
import json
import time
import re
from dotenv import load_dotenv
load_dotenv()

from langchain_core.globals import set_debug, set_verbose
set_debug(True)    # prints every LLM call input/output in full detail
set_verbose(True)  # prints chain start/end with timing

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from prompts import agent_system_prompt

# ── Import all tools ──
from tools.file_tools import read_file, write_file, edit_file, list_files, search_in_files, delete_file
from tools.terminal_tools import run_command
from tools.search_tools import web_search

# Browser tools loaded lazily
try:
    from tools.browser_tools import open_url, click_element, type_text, screenshot, get_page_text, scroll_page, wait_seconds
    BROWSER_TOOLS = [open_url, click_element, type_text, screenshot, get_page_text, scroll_page, wait_seconds]
except Exception:
    BROWSER_TOOLS = []
    print("⚠️  Browser tools unavailable (run: playwright install chromium)")
33
# ── LLM Setup ──
llm = ChatGroq(
    model="llama-3.1-8b-instant",   # 500k tokens/day (was llama-3.3-70b: 100k/day)
    max_retries=0,   # fail fast on rate limit — no silent waiting
)

# ── Tool registry ──
ALL_TOOLS = [
    read_file, write_file, edit_file, list_files, search_in_files, delete_file,
    run_command, web_search,
] + BROWSER_TOOLS

# Build a name→function lookup
TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# Build tool descriptions for the system prompt
def _tool_descriptions() -> str:
    lines = []
    for t in ALL_TOOLS:
        schema = t.get_input_schema().model_json_schema()
        props = schema.get("properties", {})
        params = ", ".join(f"{k}: {v.get('type', 'str')}" for k, v in props.items())
        lines.append(f"  • {t.name}({params}) — {t.description}")
    result = "\n".join(lines)
   
    return result

# ── Agent node: thinks + decides what tool to use ──
def agent_node(state: dict) -> dict:
    messages  = state.get("messages", [])
    iteration = state.get("iteration", 0)
    
    # ── DRY RUN PRINT: Iteration header ──────────────────────────────
    # print(f"\n{'='*60}")
    # print(f"  🔁 ITERATION {iteration + 1}")
    # print(f"{'='*60}")
    # print(f"  📥 state['iteration']      = {iteration}")
    # print(f"  📥 state['is_complete']    = {state.get('is_complete', False)}")
    # print(f"  📥 state['messages'] count = {len(messages)}")
    for i, m in enumerate(messages):
        preview = m['content'][:80].replace('\n', '↵')
        print(f"      messages[{i}] role={m['role']!r:12} content={preview!r}")
    print()

    # Build the prompt with tool info
    system = (
        agent_system_prompt() + "\n\n"
        "AVAILABLE TOOLS:\n" + _tool_descriptions() + "\n\n"
        "TO USE A TOOL, respond with ONLY this JSON (nothing else before or after):\n"
        '{"tool": "tool_name", "args": {"param1": "value1"}}\n\n'
        "RULES:\n"
        "- Send ONLY the JSON object when using a tool. No explanation text.\n"
        "- Use ONE tool per response.\n"
        "- After each tool result, decide: use another tool OR give your final answer.\n"
        "- When DONE, respond with a plain text summary (no JSON)."
    )

    # ── DRY RUN PRINT: System prompt summary ─────────────────────────
    print(f"  📝 SYSTEM PROMPT built ({len(system)} chars)")
    print(f"      First 120 chars: {system[:120].replace(chr(10), '↵')!r}")
    print()

    # Build LLM messages
    llm_messages = [SystemMessage(content=system)]

    # ── DRY RUN PRINT: Message conversion loop ────────────────────────
    print(f"  🔄 Converting {len(messages)} state messages → LangChain objects:")
    for i, msg in enumerate(messages):
        if msg["role"] == "user":
            llm_messages.append(HumanMessage(content=msg["content"]))
            print(f"      Pass {i+1}: role='user'      → HumanMessage('{msg['content'][:60]}')")
        elif msg["role"] == "assistant":
            llm_messages.append(AIMessage(content=msg["content"]))
            print(f"      Pass {i+1}: role='assistant' → AIMessage('{msg['content'][:60]}')")
        elif msg["role"] == "tool":
            llm_messages.append(HumanMessage(content=f"[Tool Result]: {msg['content']}"))
            print(f"      Pass {i+1}: role='tool'      → HumanMessage('[Tool Result]: {msg['content'][:50]}')")

    print(f"\n  📦 llm_messages ready: {len(llm_messages)} objects")
    for i, m in enumerate(llm_messages):
        mtype = type(m).__name__
        preview = m.content[:60].replace('\n', '↵')
        print(f"      [{i}] {mtype:15} ({len(m.content)} chars) → {preview!r}")
    print()

    # ── LLM call with auto-retry on rate limit ───────────────────────
    resp = None
    for attempt in range(4):   # up to 4 attempts
        try:
            resp = llm.invoke(llm_messages)
            break   # success
        except Exception as e:
            err_str = str(e)
            wait_match = re.search(r'Please try again in (\d+\.?\d*)s', err_str)
            if wait_match and attempt < 3:
                wait_secs = float(wait_match.group(1)) + 2
                print(f"\n  ⏳ Rate limit hit. Auto-retrying in {wait_secs:.0f}s (attempt {attempt+1}/4)...")
                time.sleep(wait_secs)
            else:
                raise   # not rate limit, or exhausted retries
    content = resp.content.strip()

    # Extract JSON tool call from anywhere in the response
    tool_call = _extract_tool_call(content)

    # ── DRY RUN PRINT: Tool call extraction ──────────────────────────
    if tool_call:
        print(f"  🔍 _extract_tool_call() → found JSON tool call:")
        print(f"      tool_call = {tool_call}")
        print(f"      tool_name = {tool_call['tool']!r}")
        print(f"      tool_args = {tool_call.get('args', {})}")
    else:
        print(f"  🔍 _extract_tool_call() → None (plain text — final answer!)")
    print()

    new_messages = messages.copy()

    if tool_call:
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})

        # Execute the tool
        if tool_name in TOOL_MAP:
            print(f"  🔧 Executing tool: {tool_name}")
            print(f"      TOOL_MAP[{tool_name!r}].invoke({tool_args})")
            try:
                result = TOOL_MAP[tool_name].invoke(tool_args)
            except Exception as e:
                result = f"❌ Tool error: {e}"
            print(f"\n  ✅ Tool result:")
            result_str = str(result)
            # Print result line by line for readability
            for line in result_str[:500].split('\n'):
                print(f"      {line}")
            if len(result_str) > 500:
                print(f"      ... ({len(result_str)} chars total, truncated)")
        else:
            result = f"❌ Unknown tool: {tool_name}. Available: {list(TOOL_MAP.keys())}"
            print(f"  ❌ Unknown tool: {tool_name}")

        # ── DRY RUN PRINT: Appending messages ────────────────────────
        print(f"\n  📎 Appending to new_messages:")
        assistant_msg = {"role": "assistant", "content": json.dumps(tool_call)}
        tool_msg      = {"role": "tool",      "content": str(result)}

        print(f"      +1 assistant: {json.dumps(tool_call)[:80]!r}")
        new_messages.append(assistant_msg)

        print(f"      +2 tool:      {str(result)[:80]!r}")
        new_messages.append(tool_msg)

        print(f"\n      new_messages length: {len(messages)} → {len(new_messages)}")

        # ── DRY RUN PRINT: Return state ───────────────────────────────
        print(f"\n  📤 Returning state:")
        print(f"      messages    : {len(new_messages)} messages")
        print(f"      iteration   : {iteration} → {iteration + 1}")
        print(f"      is_complete : False  (tool was called → loop again)")
        print(f"      response    : None")
        print(f"\n  ➡️  should_continue() will be called next...")

        return {
            "messages":    new_messages,
            "iteration":   iteration + 1,
            "is_complete": False,
            "response":    None,
        }
    else:
        # Not a tool call — this is the final response
        new_messages.append({"role": "assistant", "content": content})

        # ── DRY RUN PRINT: Final answer ───────────────────────────────
        print(f"  🏁 FINAL ANSWER (no tool call detected)")
        print(f"      Appending assistant message to new_messages")
        print(f"      new_messages length: {len(messages)} → {len(new_messages)}")
        print(f"\n  📤 Returning state:")
        print(f"      messages    : {len(new_messages)} messages")
        print(f"      iteration   : {iteration} → {iteration + 1}")
        print(f"      is_complete : True  ← this stops the loop!")
        print(f"      response    : {content[:100]!r}")
        print(f"\n  ➡️  should_continue() will return 'done'")

        return {
            "messages":    new_messages,
            "iteration":   iteration + 1,
            "is_complete": True,
            "response":    content,
        }


def _extract_tool_call(text: str):
    """Extract a JSON tool call from LLM text, even if surrounded by other text."""
    import re

    # Method 1: Try parsing the whole text as JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "tool" in parsed:
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # Method 2: Find JSON object with "tool" key anywhere in text
    matches = re.findall(r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^{}]*\}[^{}]*\}', text)
    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, dict) and "tool" in parsed:
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # Method 3: Find any JSON object containing "tool"
    for i, ch in enumerate(text):
        if ch == '{':
            depth = 0
            for j in range(i, len(text)):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                if depth == 0:
                    candidate = text[i:j+1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and "tool" in parsed:
                            return parsed
                    except (json.JSONDecodeError, TypeError):
                        pass
                    break

    return None


# ── Router: should we loop or stop? ──
def should_continue(state: dict) -> str:
    is_complete = state.get("is_complete", False)
    iteration   = state.get("iteration", 0)
    max_iter    = state.get("max_iterations", 15)

    # ── DRY RUN PRINT: should_continue ───────────────────────────────
    print(f"\n  🔀 should_continue() called:")
    print(f"      is_complete = {is_complete}")
    print(f"      iteration   = {iteration} / {max_iter}")

    if is_complete:
        print(f"      → 'done'  (is_complete=True)")
        return "done"
    if iteration >= max_iter:
        print(f"      → 'done'  (iteration {iteration} >= max {max_iter})")
        return "done"

    print(f"      → 'continue'  (looping back to agent_node)")
    return "continue"


# ── Build the graph ──
graph = StateGraph(dict)
graph.add_node("agent", agent_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {
    "continue": "agent",
    "done": END,
})
agent = graph.compile()


def run_agent(user_message: str, conversation_history: list = None) -> str:
    """Run the agent with a user message and return the response."""

    print(f"\n{'#'*60}")
    print(f"  🚀 run_agent() called")
    print(f"{'#'*60}")
    print(f"  user_message = {user_message!r}")
    print(f"  history msgs = {len(conversation_history) if conversation_history else 0}")

    # Build messages: previous history + new user message
    history = conversation_history or []
    messages = history + [{"role": "user", "content": user_message}]

    initial_state = {
        "messages":       messages,
        "iteration":      0,
        "max_iterations": 15,
        "is_complete":    False,
        "response":       None,
    }

    # ── DRY RUN PRINT: Initial state ─────────────────────────────────
    print(f"\n  📦 Initial state passed to agent.invoke():")
    print(f"      messages       = [{{'role': 'user', 'content': {user_message!r}}}]")
    print(f"      iteration      = 0")
    print(f"      max_iterations = 15")
    print(f"      is_complete    = False")
    print(f"      response       = None")
    print(f"\n  ▶️  Starting LangGraph execution...\n")

    result = agent.invoke(initial_state)

    # ── DRY RUN PRINT: Final result ───────────────────────────────────
    print(f"\n{'#'*60}")
    print(f"  ✅ LangGraph execution COMPLETE")
    print(f"{'#'*60}")
    print(f"  Total iterations  : {result.get('iteration', '?')}")
    print(f"  Total messages    : {len(result.get('messages', []))}")
    print(f"  is_complete       : {result.get('is_complete')}")
    print(f"  response preview  : {str(result.get('response', ''))[:100]!r}")
    print()

    return result.get("response", "Agent completed but produced no response.")


if __name__ == "__main__":
    response = run_agent("What tools do you have available? List them all.")
    print(f"\n{'='*60}\n{response}")
