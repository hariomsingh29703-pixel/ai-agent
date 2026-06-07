const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const router = express.Router();

const BASE_WORKSPACE = path.join(__dirname, '../workspace');
fs.mkdirSync(BASE_WORKSPACE, { recursive: true });

function getSessionWorkspace(req) {
    if (!req.session.workspaceId) {
        req.session.workspaceId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    }
    const wsPath = path.join(BASE_WORKSPACE, req.session.workspaceId);
    fs.mkdirSync(wsPath, { recursive: true });
    return wsPath;
}

function getPermissions(req) {
    if (!req.session.permissions || !req.session.permissions.granted) {
        req.session.permissions = { files: true, terminal: true, granted: true };
    }
    return req.session.permissions;
}

// ── POST /api/chat ────────────────────────────────────────────────────────────
router.post('/api/chat', (req, res) => {
    const { message } = req.body;
    if (!message) return res.status(400).json({ error: 'Message is required' });

    getPermissions(req); // auto-grant

    // ── Detect whether this is a code/file generation task ──────────────────
    const lower = message.toLowerCase();
    const codeKeywords = [
        'create', 'build', 'make', 'generate', 'develop', 'write code',
        'write a', 'design', 'code a', 'code the', 'implement', 'program',
        'app', 'website', 'web app', 'dashboard', 'portfolio', 'landing page',
        'api', 'script', 'html', 'css', 'javascript', 'python script',
        'react', 'node', 'express', 'todo', 'calculator', 'game', 'ui'
    ];
    const isCodeTask = codeKeywords.some(k => lower.includes(k));

    let augmentedMessage;
    if (isCodeTask) {
        // Inject file-marker format for code generation tasks
        augmentedMessage = message + `

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
- Output ALL files this way, then write a short 2-3 line summary at the end.`;
    } else {
        // General / agentic task — browser search, research, questions etc.
        // Let the agent answer naturally, no file format required
        augmentedMessage = message;
    }

    const scriptPath = path.join(__dirname, '../ai_backend/run_single.py');
    
    // Dynamically find Python executable based on environment
    const localVenv = '/home/saurabh-kumar123/Desktop/Desktop/express/antigravity_clone/venv/bin/python';
    const relativeVenv = path.join(__dirname, '../ai_backend/venv/bin/python');
    let pythonExecutable = 'python3';
    
    if (fs.existsSync(localVenv)) {
        pythonExecutable = localVenv;
    } else if (fs.existsSync(relativeVenv)) {
        pythonExecutable = relativeVenv;
    }

    const pythonProcess = spawn(pythonExecutable, [scriptPath, augmentedMessage], {
        cwd: path.join(__dirname, '../ai_backend'),
        env: { ...process.env }
    });

    let dataString = '';
    pythonProcess.stdout.on('data', d => { dataString += d.toString(); });
    pythonProcess.stderr.on('data', d => console.error('AI stderr:', d.toString()));

    pythonProcess.on('close', () => {
        try {
            const lines = dataString.trim().split('\n');
            let jsonResponse = null;
            for (let i = lines.length - 1; i >= 0; i--) {
                try {
                    const p = JSON.parse(lines[i]);
                    if (p.response !== undefined || p.error) { jsonResponse = p; break; }
                } catch(e) {}
            }
            if (jsonResponse && jsonResponse.response) {
                res.json({ response: jsonResponse.response });
            } else if (jsonResponse && jsonResponse.error) {
                res.status(500).json({ error: jsonResponse.error });
            } else {
                res.status(500).json({ error: 'Could not parse AI response.' });
            }
        } catch(e) {
            res.status(500).json({ error: 'Failed to parse AI output.' });
        }
    });
});

// ── GET /api/session-info ────────────────────────────────────────────────────
router.get('/api/session-info', (req, res) => {
    res.json({ hasPermissions: true, permissions: getPermissions(req) });
});

// ── POST /api/permissions ────────────────────────────────────────────────────
router.post('/api/permissions', (req, res) => {
    req.session.permissions = { files: true, terminal: true, granted: true };
    res.json({ success: true, permissions: req.session.permissions });
});

// ── GET /api/workspace ───────────────────────────────────────────────────────
router.get('/api/workspace', (req, res) => {
    res.json({ files: [], noPermission: false });
});

module.exports = router;
