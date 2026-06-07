import os
import json
import time
import asyncio
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils.db import NeDB, normalize_email, format_date
from utils.parser import parse_response_files
import bcrypt

# ── Load Environment Variables ──
from dotenv import load_dotenv
load_dotenv()

PORT = int(os.getenv("PORT", 3010))
SESSION_SECRET = os.getenv("SESSION_SECRET", "KnowledgeGate AI with Complete Coding")

# ── Initialize NeDB Stores ──
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
users_db = NeDB(os.path.join(data_dir, "users.db"))
projects_db = NeDB(os.path.join(data_dir, "projects.db"))

app = FastAPI(title="AgentFirst FastAPI Backend")

# Add CORS Middleware (allow Vercel and localhost origins)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=7 * 24 * 60 * 60, # 7 days
    same_site="lax",
    https_only=False
)

# ── Templates setup ──
_this_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(_this_dir, "views"))

# Custom Jinja2 Filters / Helpers if needed
templates.env.globals.update(len=len)

# ── Auth & Onboarding Guards / Helpers ──
def get_current_user(request: Request):
    if not request.session.get("isLoggedIn") or not request.session.get("user"):
        return None
    return request.session.get("user")

def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=307, detail="Not authenticated")
    return user

def require_onboard(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=307, detail="Not authenticated")
    if not user.get("onboarded", False):
        raise HTTPException(status_code=307, detail="Not onboarded")
    return user

# Custom Exception Handler for redirecting on Auth errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 307:
        if exc.detail == "Not authenticated":
            return RedirectResponse("/login")
        elif exc.detail == "Not onboarded":
            return RedirectResponse("/onboarding")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ── GET / — Landing Page ──
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/projects")
    return templates.TemplateResponse(request, "index.html", {})


# ── GET /login — Login page ──
@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    if get_current_user(request):
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


# ── POST /login — Login action ──
@app.post("/login", response_class=HTMLResponse)
async def post_login(request: Request, email: str = Form(""), password: str = Form("")):
    raw_email = email.strip()
    norm_email = normalize_email(raw_email) or raw_email.lower()
    
    user = users_db.find_one({"email": norm_email})
    if not user:
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "No account found with that email."
        })
        
    # verify password
    hashed_pwd = user.get("password", "")
    try:
        pw_ok = bcrypt.checkpw(password.encode('utf-8'), hashed_pwd.encode('utf-8'))
    except Exception:
        pw_ok = False
        
    if not pw_ok:
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "Incorrect password."
        })
        
    # Start session
    request.session["isLoggedIn"] = True
    request.session["user"] = {
        "_id": user.get("_id"),
        "firstName": user.get("firstName"),
        "lastName": user.get("lastName", ""),
        "email": user.get("email"),
        "role": user.get("role", "other"),
        "experienceLevel": user.get("experienceLevel", "intermediate"),
        "goals": user.get("goals", ""),
        "onboarded": user.get("onboarded", True)
    }
    
    return RedirectResponse("/projects", status_code=303)


# ── GET /signup — Signup page ──
@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    if get_current_user(request):
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "auth/signup.html", {"error": None, "oldInput": {}})


# ── POST /signup — Signup action ──
@app.post("/signup", response_class=HTMLResponse)
async def post_signup(
    request: Request,
    firstName: str = Form(""),
    lastName: str = Form(""),
    email: str = Form(""),
    password: str = Form("")
):
    firstName = firstName.strip()
    lastName = lastName.strip()
    email_val = email.strip()
    
    errors = []
    if len(firstName) < 2:
        errors.append("First name must be at least 2 characters.")
    if "@" not in email_val or "." not in email_val:
        errors.append("Enter a valid email.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
        
    old_input = {"firstName": firstName, "lastName": lastName, "email": email_val}
    
    if errors:
        return templates.TemplateResponse(request, "auth/signup.html", {
            "error": errors[0],
            "oldInput": old_input
        })
        
    norm_email = normalize_email(email_val)
    existing = users_db.find_one({"email": norm_email})
    if existing:
        return templates.TemplateResponse(request, "auth/signup.html", {
            "error": "An account with this email already exists.",
            "oldInput": old_input
        })
        
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    
    new_user = users_db.insert({
        "firstName": firstName,
        "lastName": lastName,
        "email": norm_email,
        "password": hashed,
        "authProvider": "local",
        "role": "other",
        "experienceLevel": "intermediate",
        "goals": "",
        "onboarded": True,
        "createdAt": {"$$date": int(time.time() * 1000)}
    })
    
    # login session
    request.session["isLoggedIn"] = True
    request.session["user"] = {
        "_id": new_user.get("_id"),
        "firstName": new_user.get("firstName"),
        "lastName": new_user.get("lastName", ""),
        "email": new_user.get("email"),
        "role": "other",
        "experienceLevel": "intermediate",
        "goals": "",
        "onboarded": True
    }
    
    return RedirectResponse("/projects", status_code=303)


# ── GET /onboarding — Onboarding page ──
@app.get("/onboarding", response_class=HTMLResponse)
async def get_onboarding(request: Request):
    user = require_auth(request)
    return templates.TemplateResponse(request, "onboarding.html", {
        "userName": user.get("firstName")
    })


# ── POST /onboarding — Onboarding action ──
@app.post("/onboarding")
async def post_onboarding(
    request: Request,
    role: str = Form("other"),
    goals: str = Form(""),
    level: str = Form("intermediate")
):
    user = require_auth(request)
    uid = user.get("_id")
    
    users_db.update(
        {"_id": uid},
        {"$set": {
            "role": role,
            "goals": goals,
            "experienceLevel": level,
            "onboarded": True
        }}
    )
    
    # Update current session user object
    request.session["user"]["role"] = role
    request.session["user"]["goals"] = goals
    request.session["user"]["experienceLevel"] = level
    request.session["user"]["onboarded"] = True
    
    return RedirectResponse("/projects", status_code=303)


# ── GET /logout — Logout ──
@app.get("/logout")
async def get_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


# ── GET /projects — List user's projects ──
@app.get("/projects", response_class=HTMLResponse)
async def get_projects(request: Request):
    user = require_onboard(request)
    uid = user.get("_id")
    
    projects = projects_db.find({"userId": uid})
    
    # Helper lambda to safely get the date timestamp
    def get_created_time(p):
        created = p.get("createdAt")
        if isinstance(created, dict) and "$$date" in created:
            return created["$$date"]
        return 0
        
    sorted_projects = sorted(projects, key=get_created_time, reverse=True)
    
    return templates.TemplateResponse(request, "projects.html", {
        "userName": user.get("firstName"),
        "userRole": user.get("role", "other"),
        "userLevel": user.get("experienceLevel", "intermediate"),
        "currentPage": "projects",
        "projects": sorted_projects
    })


# ── GET /favourites — List user's favourites ──
@app.get("/favourites", response_class=HTMLResponse)
async def get_favourites(request: Request):
    user = require_onboard(request)
    uid = user.get("_id")
    
    projects = projects_db.find({"userId": uid, "isFavourite": True})
    
    def get_created_time(p):
        created = p.get("createdAt")
        if isinstance(created, dict) and "$$date" in created:
            return created["$$date"]
        return 0
        
    sorted_projects = sorted(projects, key=get_created_time, reverse=True)
    
    return templates.TemplateResponse(request, "favourites.html", {
        "userName": user.get("firstName"),
        "userRole": user.get("role", "other"),
        "userLevel": user.get("experienceLevel", "intermediate"),
        "currentPage": "favourites",
        "projects": sorted_projects
    })


# ── GET /projects/{id} — Single project details ──
@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def get_project_detail(project_id: str, request: Request):
    user = require_onboard(request)
    uid = user.get("_id")
    
    project = projects_db.find_one({"_id": project_id, "userId": uid})
    if not project:
        return RedirectResponse("/projects")
        
    formatted_date = format_date(project.get("createdAt"))
    files, summary_text = parse_response_files(project.get("response", ""))
    
    return templates.TemplateResponse(request, "project-detail.html", {
        "userName": user.get("firstName"),
        "userRole": user.get("role", "other"),
        "userLevel": user.get("experienceLevel", "intermediate"),
        "currentPage": "projects",
        "project": project,
        "formattedCreatedAt": formatted_date,
        "files": files,
        "summaryText": summary_text
    })


# ── API: POST /api/chat — Chat / Agentic workflow execution ──
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def post_api_chat(payload: ChatRequest, request: Request):
    user = require_onboard(request)
    message = payload.message.strip()
    if not message:
        return JSONResponse(status_code=400, content={"error": "Message is required"})
        
    # Detect code generation task
    lower = message.lower()
    code_keywords = [
        'create', 'build', 'make', 'generate', 'develop', 'write code',
        'write a', 'design', 'code a', 'code the', 'implement', 'program',
        'app', 'website', 'web app', 'dashboard', 'portfolio', 'landing page',
        'api', 'script', 'html', 'css', 'javascript', 'python script',
        'react', 'node', 'express', 'todo', 'calculator', 'game', 'ui'
    ]
    is_code_task = any(k in lower for k in code_keywords)
    
    if is_code_task:
        augmented_message = message + """

CRITICAL OUTPUT FORMAT — YOU MUST FOLLOW THIS EXACTLY:
For every file you create (index.html, style.css, script.js, app.py, etc.), output the COMPLETE file contents wrapped like this:

=== FILE: index.html ===
<!DOCTYPE html>
... full html code ...
=== END FILE ===

=== FILE: style.css ===
... full css code ...
=== END FILE ===

Rules:
- ALWAYS include the COMPLETE code. Never truncate or use placeholders like "// add more code here".
- Use this EXACT format with === FILE: filename === and === END FILE === delimiters.
- Output ALL files this way, then write a short 2-3 line summary at the end."""
    else:
        augmented_message = message

    # Python executable resolution
    python_exe = os.getenv("AGENT_PYTHON_EXE", "/home/saurabh-kumar123/Desktop/Desktop/express/antigravity_clone/venv/bin/python")
    if not os.path.exists(python_exe):
        python_exe = "python3"
        
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_backend", "run_single.py")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            python_exe, script_path, augmented_message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_backend")
        )
        
        stdout, stderr = await proc.communicate()
        
        if stderr:
            print("AI agent stderr:", stderr.decode(errors='replace'))
            
        stdout_str = stdout.decode(errors='replace').strip()
        lines = stdout_str.split('\n')
        
        # Traverse backwards to find the JSON response block printed by run_single.py
        for line in reversed(lines):
            try:
                res = json.loads(line)
                if "response" in res:
                    return {"response": res["response"]}
                elif "error" in res:
                    return JSONResponse(status_code=500, content={"error": res["error"]})
            except Exception:
                continue
                
        return JSONResponse(status_code=500, content={"error": "Could not parse AI response from stdout."})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal agent execution error: {str(e)}"})


# ── API: POST /api/projects/save ──
class SaveRequest(BaseModel):
    title: Optional[str] = None
    prompt: str
    response: str

@app.post("/api/projects/save")
async def post_api_save_project(payload: SaveRequest, request: Request):
    user = require_onboard(request)
    uid = user.get("_id")
    
    title = payload.title or ""
    if not title:
        title = payload.prompt[:60] + ("..." if len(payload.prompt) > 60 else "")
        
    new_proj = projects_db.insert({
        "userId": uid,
        "title": title,
        "prompt": payload.prompt,
        "response": payload.response,
        "isFavourite": False,
        "createdAt": {"$$date": int(time.time() * 1000)}
    })
    
    return {"success": True, "project": new_proj}


# ── API: POST /api/projects/{id}/favourite ──
@app.post("/api/projects/{project_id}/favourite")
async def post_api_favourite(project_id: str, request: Request):
    user = require_auth(request)
    uid = user.get("_id")
    
    project = projects_db.find_one({"_id": project_id, "userId": uid})
    if not project:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})
        
    new_fav_state = not project.get("isFavourite", False)
    projects_db.update({"_id": project_id}, {"$set": {"isFavourite": new_fav_state}})
    
    return {"success": True, "isFavourite": new_fav_state}


# ── API: DELETE /api/projects/{id} ──
@app.delete("/api/projects/{project_id}")
async def delete_api_project(project_id: str, request: Request):
    user = require_auth(request)
    uid = user.get("_id")
    
    removed = projects_db.remove({"_id": project_id, "userId": uid})
    if removed > 0:
        return {"success": True}
    return JSONResponse(status_code=404, content={"success": False, "error": "Project not found or not owned"})


# ── Catch-all / Static files fallback ──
@app.get("/{file_path:path}")
async def serve_static_or_not_found(file_path: str):
    # Try serving from public folder (static files like home.css or output.css)
    public_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public", file_path)
    if os.path.isfile(public_path):
        return FileResponse(public_path)
        
    # Try serving from uploads folder
    uploads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", file_path)
    if os.path.isfile(uploads_path):
        return FileResponse(uploads_path)
        
    # Else raise 404
    raise HTTPException(status_code=404, detail="Page not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)
