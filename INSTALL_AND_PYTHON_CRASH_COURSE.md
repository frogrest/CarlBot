# Install Guide + Tiny Python Crash Course

This guide is written for someone who is **not a Python developer** and is starting on a fresh Windows 11 PC.

The easiest path is:

**Windows 11 → Git → Docker Desktop → Python → project → tests → Docker → browser**

You do not need to become a Python programmer before working on this project. You only need enough Python knowledge to understand what the files are doing and how to run the project.

---

## 1. What you are building

You are building a safe replica/lab of a CCTV technical-support helpdesk:

```text
                         ┌──────────────────────┐
                         │   Helpdesk Web UI    │
                         │ tickets + chatbot    │
                         └──────────┬───────────┘
                                    │
                                    v
                         ┌──────────────────────┐
                         │  Agent Orchestrator  │
                         │ supervisor/router    │
                         └──────────┬───────────┘
                                    │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              v                    v                    v
        Network Agent        RTSP Agent          Helpdesk Agent
              │                    │                    │
              └──────────────┬─────┴────────────────────┘
                             v
                    Evidence / Knowledge
                             │
                             v
                 Fake Portal + Fake Helpdesk
```

The AI does the repetitive investigation. Humans remain responsible for physical repairs, consequential changes, approvals, and final judgement.

---

## 2. Install these programs

### Required

1. **Git** — downloads/updates project source.
2. **Docker Desktop** — runs the fake services in isolated containers.
3. **Python 3.13+** — runs local tests and development utilities.
4. **A code editor** — VS Code is the simplest choice; an AI coding agent can also edit the repository.

### Needed later for the frontend

5. **Node.js LTS** — used for the React/Vite frontend when that part of the project is built.

Install the current official Windows installers from:

- Git: https://git-scm.com/download/win
- Docker Desktop: https://www.docker.com/products/docker-desktop/
- Python: https://www.python.org/downloads/windows/
- Node.js: https://nodejs.org/
- VS Code: https://code.visualstudio.com/download

During Python installation, enable **Add Python to PATH**.

For Docker Desktop on Windows, use its normal WSL2/Windows setup and reboot if the installer asks you to.

---

## 3. Verify the installation

Open **PowerShell** and run these commands one at a time:

```powershell
python --version
python -m pip --version
git --version
docker --version
docker compose version
node --version
npm --version
```

You should see version information for each command.

Do not worry if the version numbers are different from examples you may see online. The project is written to use current supported releases rather than one exact patch number.

---

## 4. Put the project somewhere simple

For example:

```text
C:\AI-Helpdesk-Agent
```

Open PowerShell and run:

```powershell
cd C:\
mkdir AI-Helpdesk-Agent
cd AI-Helpdesk-Agent
```

Copy/extract the project package there.

You should eventually have:

```text
C:\AI-Helpdesk-Agent
│  AGENTS.md
│  README.md
│  PROJECT_INDEX.md
│  INSTALL_AND_PYTHON_CRASH_COURSE.md
│  PROJECT_WORKFLOW.md
│  ONE_SHOT_BUILD_PROMPT.md
│  docker-compose.yml
│  requirements.txt
│
├─ docs
├─ prompts
├─ reference
├─ services
├─ tests
└─ data
```

---

## 5. Create Python's virtual environment

A Python virtual environment is simply a private folder containing this project's Python packages.

From the project folder:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If your organization blocks PowerShell script execution, do **not** change policy just for this project. Use Command Prompt instead and run:

```cmd
.venv\Scripts\activate.bat
```

After activation, your prompt may show something like:

```text
(.venv) PS C:\AI-Helpdesk-Agent>
```

That means the environment is active.

---

## 6. Install the Python packages

Run:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The project currently uses Python packages for the API services, agent, and testing. Docker will still be the main runtime.

---

## 7. First test

Run:

```powershell
python -m compileall services tests
python -m pytest -q
```

A successful test run is more important than memorizing Python syntax.

---

## 8. Start the lab with Docker

From the project root:

```powershell
docker compose up --build -d
```

Check the containers:

```powershell
docker compose ps
```

The included lab exposes:

| Service | URL |
|---|---|
| Helpdesk API | http://localhost:8000/docs |
| Operations Portal | http://localhost:8001/docs |
| Agent | http://localhost:8002/docs |

When the frontend replica is added, it will get its own frontend port.

---

## 9. Stop the lab

```powershell
docker compose down
```

Start again later with:

```powershell
docker compose up -d
```

After code changes, use:

```powershell
docker compose up --build -d
```

---

## 10. See what's happening

View all logs:

```powershell
docker compose logs --tail=200
```

Watch only the agent:

```powershell
docker compose logs -f agent
```

Stop following with `Ctrl+C`.

---

## 11. Your first simulated failure

Inject a fake RTSP failure:

```powershell
curl.exe -X POST http://localhost:8001/api/simulate/fault `
  -H "Content-Type: application/json" `
  -d '{"asset_id":"CAM-027","fault":"rtsp_down"}'
```

The exact shell escaping can look ugly on Windows; that is normal.

The expected flow is:

```text
fake RTSP failure
      ↓
portal reports fault
      ↓
agent notices it
      ↓
ticket is created/updated
      ↓
diagnostics run
      ↓
historical tickets/docs are searched
      ↓
agent proposes a diagnosis
      ↓
simulated reconnect is allowed
      ↓
verification runs
      ↓
ticket is resolved
```

---

## 12. Tiny Python crash course

### What is Python?

Python is the programming language used for the backend services and agent.

A Python file ends in:

```text
.py
```

For example:

```text
services/agent/core.py
```

### Variables

A variable is just a name holding a value:

```python
name = "CAM-027"
port = 554
healthy = True
```

### Lists

A list stores multiple values:

```python
faults = ["rtsp_down", "poe_off", "auth_failure"]
```

### Dictionaries

A dictionary stores named fields:

```python
asset = {
    "id": "CAM-027",
    "type": "camera",
    "port": 554,
    "online": True,
}
```

This is extremely common in API/AI code because JSON looks almost the same.

### Functions

A function is reusable logic:

```python
def check_camera(asset):
    return asset["online"]
```

Then:

```python
result = check_camera(asset)
```

### Conditions

```python
if asset["online"]:
    print("Camera is reachable")
else:
    print("Camera is offline")
```

### Loops

```python
for fault in faults:
    print(fault)
```

### Classes

A class is a blueprint for a type of object:

```python
class Ticket:
    def __init__(self, ticket_id, title):
        self.ticket_id = ticket_id
        self.title = title
```

You do not need to master classes immediately. Just know they group related data and behavior.

### Imports

```python
from services.agent.core import Agent
```

This means one Python file is using code from another file.

### Exceptions

```python
try:
    result = do_something()
except Exception as exc:
    print(exc)
```

This is how programs handle failures instead of crashing blindly.

---

## 13. The important Python idea for this project

Think of Python files as small workers.

For example:

```text
services/helpdesk/app.py
```

is the Helpdesk API worker.

```text
services/portal/app.py
```

is the fake CCTV/operations environment worker.

```text
services/agent/core.py
```

contains agent logic.

The orchestrator will eventually coordinate specialist workers rather than putting every decision in one giant file.

---

## 14. What FastAPI means here

The project uses web APIs.

An API is just a way for one program to ask another program for something.

For example:

```text
Frontend → "show me ticket 123"
          ↓
Helpdesk API
          ↓
JSON response
          ↓
Frontend displays ticket
```

FastAPI is the Python framework used to build those HTTP endpoints.

That is why URLs such as:

```text
http://localhost:8000/docs
```

show an interactive API page.

---

## 15. What Docker means here

You can think of Docker containers as small sealed computers running on your PC.

Instead of installing every service separately, Docker runs:

```text
Helpdesk container
Portal container
Agent container
Future frontend container
```

They communicate over a private Docker network.

That is why this command is so useful:

```powershell
docker compose up --build
```

It means roughly:

> Build the project's containers and start the whole lab together.

---

## 16. What the AI agent actually does

The agent is **not** one magical Python file.

The intended architecture is:

```text
1. Observe
2. Understand the ticket
3. Gather live diagnostics
4. Search previous tickets
5. Search documentation
6. Ask specialist agents for domain-specific analysis
7. Combine evidence
8. Form a diagnosis
9. Check policy
10. Recommend or execute a permitted simulated action
11. Verify
12. Update the ticket
13. Hand off to a technician when required
```

---

## 17. What an LLM does vs what Python does

The LLM is good at:

- reading evidence
- comparing symptoms
- explaining likely causes
- selecting useful next diagnostic steps
- writing technician-friendly summaries

Python is good at:

- calling APIs
- storing state
- validating data
- enforcing rules
- running tools
- retries and timeouts
- logging
- tests

The safest design is therefore:

```text
LLM = reasoning
Python = control
Policy = permission
Tools = action
```

Do not let the language model become the security boundary.

---

## 18. How the sub-agents fit in

A specialist agent does **one type of reasoning well**.

Example:

```text
Ticket:
"Camera 7 shows no video."

Orchestrator
   ↓
Network Agent → checks reachability/subnet clues
   ↓
RTSP Agent → checks RTSP/554/path/auth clues
   ↓
Camera/NVR Agent → checks recorder-side conditions
   ↓
Knowledge Agent → finds similar historical incidents
   ↓
Evidence Agent → checks whether the conclusion is actually supported
```

The orchestrator is the supervisor. A specialist should not secretly take control of the whole system.

---

## 19. What `/clear` means

The chatbot will behave like a normal assistant conversation, but `/clear` resets only the **chat conversation context** for that UI session.

It should not delete:

- tickets
- historical incidents
- knowledge documents
- audit records
- agent state

That distinction is important.

```text
/chat context      → temporary conversation
project memory     → ticket/history/knowledge storage
```

---

## 20. How the frontend should be built

Do not start by inventing a random modern dashboard.

The frontend agent should first inspect the supplied helpdesk screenshots (`reference/screenshots/reference.pdf`, 6 pages) and recreate the visual language:

- layout
- navigation
- hierarchy
- colors
- typography
- list/table patterns
- status indicators
- search/filter behavior
- ticket layout
- device/camera tree

Then add the AI assistant as a natural part of that interface.

The final experience should feel like:

```text
REALISTIC HELPdesk UI
        +
AI diagnostic copilot
        +
Evidence panel
        +
Suggested actions
        +
Human approval/handoff
```

---

## 21. Recommended development order

Do not ask an AI coding agent to build everything at once and hope for the best.

Use this order:

```text
Phase 1  → get the current lab running
Phase 2  → make tests reliable
Phase 3  → add orchestrator/state machine
Phase 4  → add specialist agents
Phase 5  → add knowledge/RAG layer
Phase 6  → add LLM reasoning
Phase 7  → build helpdesk frontend replica
Phase 8  → embed chatbot/copilot
Phase 9  → run scenario evaluation
```

---

## 22. When something breaks

Do not randomly reinstall everything.

Run:

```powershell
docker compose ps
docker compose logs --tail=200
python -m pytest -q
```

Then identify whether the failure is:

```text
installation
or
container startup
or
API
or
agent logic
or
frontend
or
LLM integration
```

Fix the smallest layer first.

---

## 23. The one command you should remember

From the project root:

```powershell
docker compose up --build
```

That is the normal way to bring the lab to life during development.
