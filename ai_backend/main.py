"""
Antigravity Clone — Interactive Chat
Run this to start chatting with your AI coding agent.

Usage:
    python main.py
"""
import sys
import os
import time
import re
from datetime import datetime
from graph import run_agent

# RAG Memory — loads past conversations from MongoDB
try:
    from memory import save_conversation, build_memory_context, get_stats
    MEMORY_ENABLED = True
except Exception as e:
    print(f"⚠️  Memory disabled (install pymongo + sentence-transformers): {e}")
    MEMORY_ENABLED = False


# ── Tee: write output to BOTH terminal and log file ──────────────────
class Tee:
    """Mirrors all print() output to a log file so nothing is lost."""
    def __init__(self, log_path):
        self.terminal = sys.__stdout__
        self.log      = open(log_path, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


LOG_FILE = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
sys.stdout = Tee(LOG_FILE)
print(f"📝 Logging all output to: {LOG_FILE}")


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🚀 ANTIGRAVITY CLONE — AI Coding Agent                  ║
║                                                              ║
║     Commands:                                                ║
║       • Type anything to chat with the agent                 ║
║       • Type 'exit' or 'quit' to stop                        ║
║       • Type 'clear' to clear screen                         ║
║                                                              ║
║     Capabilities:                                            ║
║       📁 Read/Write/Edit files                               ║
║       💻 Run terminal commands                               ║
║       🌐 Control browser (Playwright)                        ║
║       🔍 Search the web                                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


def main():
    print(BANNER)

    # Show memory stats on startup
    if MEMORY_ENABLED:
        stats = get_stats()
        if "error" not in stats:
            print(f"🧠 Memory: {stats['total_conversations']} past conversations loaded from MongoDB\n")
        else:
            print(f"⚠️  MongoDB not connected — memory disabled\n")

    conversation_history = []   # in-session memory (current session)

    while True:
        try:
            user_input = input("\n\033[1;36mYou:\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Goodbye!")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print("\n👋 Goodbye!")
            break

        if user_input.lower() == "clear":
            import os
            os.system("clear" if os.name != "nt" else "cls")
            print(BANNER)
            conversation_history = []
            continue

        # ── RAG: retrieve relevant past conversations ────────────────
        memory_context = ""
        if MEMORY_ENABLED:
            memory_context = build_memory_context(user_input)
            if memory_context:
                print(f"\033[0;35m💭 Found relevant memory from past sessions\033[0m")

        print("\n\033[1;33m🤖 Thinking...\033[0m\n")

        try:
            # Inject memory context into the first user message if available
            prompt_with_memory = (
                f"{memory_context}\n\nCurrent question: {user_input}"
                if memory_context else user_input
            )

            # ── Auto-retry on rate limit (TPM) ───────────────────────
            max_attempts = 3
            response = None
            for attempt in range(max_attempts):
                try:
                    response = run_agent(prompt_with_memory, conversation_history)
                    break   # success — exit retry loop
                except Exception as e:
                    err = str(e)
                    # Check if it's a rate limit error with a wait time
                    wait_match = re.search(r'Please try again in (\d+\.?\d*)s', err)
                    if wait_match and attempt < max_attempts - 1:
                        wait_secs = float(wait_match.group(1)) + 2  # add 2s buffer
                        print(f"\n⏳ Rate limit hit. Auto-retrying in {wait_secs:.0f}s... (attempt {attempt+1}/{max_attempts})")
                        time.sleep(wait_secs)
                    else:
                        raise   # not a rate limit error, or max retries hit

            if response:
                print(f"\033[1;32mAgent:\033[0m {response}")

                # ── Save exchange to MongoDB for future sessions ─────
                if MEMORY_ENABLED:
                    save_conversation(user_input, response)

                # ── Update in-session history ────────────────────────
                conversation_history.append({"role": "user",      "content": user_input})
                conversation_history.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"\n\033[1;31m❌ Error:\033[0m {e}")



if __name__ == "__main__":
    main()
