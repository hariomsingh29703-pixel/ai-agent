# AgentFirst - Autonomous AI Agentic Workspace 🤖✨

**AgentFirst** is a production-ready, full-stack AI-agent platform that generates fully functional websites, calculators, dashboards, and portfolios from simple conversational prompts. The application is built on a high-performance **Python/FastAPI** backend that dynamically compiles, manages sessions, parses file sandboxes, and interacts directly with autonomous AI agents.

---

## 🌟 Key Features

### 🧠 Autonomous Code Generation Agent
* **LangChain & LangGraph Orchestration**: Executes agentic loops with dynamic tool-calling via local Playwright browser actions and Groq LLMs.
* **Auto-augmentation**: Detects coding intents and appends structured parsing formats to prompt templates to ensure clean outputs.
* **Discrete Code File Sandbox**: Parses raw LLM text into isolated web files (e.g. `index.html`, `style.css`, `script.js`) and presents them in clean, tabbed editor views.

### 🎨 Premium HSL CSS & Design System
* **Stunning Glassmorphism**: Tailored modern dark mode visual system.
* **Interactive Dashboard**: Provides a project count grid, responsive favorite stars, and real-time status trackers.
* **Dynamic Onboarding**: Collects user roles, goals, and experience levels to adapt future agent generations.

### 🔒 Core Platform & Infrastructure
* **NeDB Compatible Persistence**: Built with a custom Python data access wrapper (`utils/db.py`) to support NeDB JSON files.
* **Starlette Session Management**: Retains secure user authentication, signup validations, onboarding, and favorite states.
* **CORS & Static Asset Serving**: Fast, integrated serving of compiled Tailwind CSS files and static media fallback routes.

---

## 🛠️ Tech Stack

### Backend & API
* **Runtime**: Python 3.12+
* **Framework**: FastAPI (ASGI)
* **Session Handler**: Starlette Session Middleware
* **Template Engine**: Jinja2 Templates
* **Security & Authentication**: bcrypt (12 salt rounds) & itsdangerous for secure cookies

### AI Agent Engine
* **Orchestration**: LangChain, LangGraph
* **Browser Automation**: Playwright (Sync API)
* **LLM Provider**: LangChain-Groq (Groq API Key)

### Frontend & Styles
* **Markup**: Semantic HTML5 / Jinja2 dynamic views
* **Styling**: Tailwind CSS v3 & HSL variable CSS
* **Build System**: Node.js & npm (scripts execution bridge)

---

## 📦 Installation & Setup

### 1. Prerequisites
* **Node.js** (v18 or higher)
* **Python** (v3.10 or higher)
* A **Groq API Key** (register at [console.groq.com](https://console.groq.com))

### 2. Sibling Repository Configuration
Ensure that the `antigravity_clone` agent repository is checked out as a sibling directory to this repository:
```
├── antigravity_clone/       # AI Agent state engine and virtual env
└── ai_agent_skill/          # This workspace (FastAPI + Jinja2 templates)
```

### 3. Setup Project Environment
Initialize your local environment file `.env` in the root of `ai_agent_skill`:
```env
PORT=3010
SESSION_SECRET=your-secure-random-session-secret-key
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 4. Install Node.js Dependencies (Tailwind CSS)
```bash
npm install
```

### 5. Launch the Development Server
Run the unified command to watch Tailwind styles and host the FastAPI server:
```bash
npm run dev
```
The server will start running on: **`http://localhost:3010`**

---

## 📁 Project Structure

```
├── ai_backend/                 # Agent executor logic
│   ├── run_single.py          # Entry point for spawning LLM runs
│   └── tools/                 # Browser & search tools
├── data/                       # NeDB compatibility storage
│   ├── users.db               # JSON-delimited user store
│   └── projects.db            # JSON-delimited project store
├── public/                     # Compiled stylesheets and assets
├── utils/                      # Helper modules
│   ├── db.py                  # NeDB Python wrapper
│   └── parser.py              # File-block regex parser
├── views/                      # Jinja2-compatible templates
│   ├── auth/                  # Login & Signup pages
│   ├── projects.html          # Main Dashboard page
│   ├── project-detail.html    # Tabbed code viewer sandbox
│   └── onboarding.html        # Onboarding preferences screen
├── app.py                      # FastAPI Web Application entrypoint
├── package.json                # npm script bindings
└── .gitignore                  # Git exclusion rules
```

---

## 🚀 Deployment

### Backend (Render.com Web Service)
1. Set up a Python Web Service on Render.
2. Add a **Persistent Disk** mounted to `data/` to keep your NeDB database files persistent.
3. Configure the environment variables:
   * `SESSION_SECRET`
   * `GROQ_API_KEY`
   * `CLONE_DIR` (e.g. `./antigravity_clone`)
   * `AGENT_PYTHON_EXE` (e.g. `python`)
