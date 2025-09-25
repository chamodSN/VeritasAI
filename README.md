## VeritasAI – Multi‑Agent Legal Research System

VeritasAI is a multi‑agent system for legal case research. It orchestrates four microservices to parse queries, search cases, summarize opinions from full text, extract legal citations, and find related precedents. A React frontend provides an interactive UI for exploration.

### Architecture
- Orchestrator (FastAPI, port 8000): entrypoint that coordinates all agents
- Case Finder Agent (FastAPI, port 8001): query understanding + CourtListener search
- Summary Agent (FastAPI, port 8002): summarizes case text; extracts entities
- Citation Agent (FastAPI, port 8003): extracts legal citations from case text
- Precedent Agent (FastAPI, port 8004): finds related cases by citations/content
- Labels Server (Flask/simple, port 5000): serves case type/topic labels
- Frontend (React, port 3000): search UI

### Prerequisites
- Python 3.10+ (Windows users: prefer Python 3.10/3.11 over 3.12+ for widest library support)
- Node.js 18+
- CourtListener API key

### Quick Start (Windows PowerShell)
```powershell
# 1) Create and activate venv
py -3 -m venv venv
./venv/Scripts/Activate.ps1

# 2) Install Python deps
pip install -r requirements.txt

# 3) Environment variables (example values)
$env:JWT_SECRET="YOUR_JWT_SECRET"
$env:ENCRYPTION_KEY="YOUR_ENCRYPTION_KEY"  # 32-char urlsafe Fernet key
$env:COURTLISTENER_API_KEY="YOUR_COURTLISTENER_TOKEN"

# 4) Start services (each in a terminal) OR use the helper
py start_services.py
# Or individually:
uvicorn agents.case_finder.main:app --port 8001
uvicorn agents.summary.main:app --port 8002
uvicorn agents.citation.citation:app --port 8003
uvicorn agents.percedent.main:app --port 8004
uvicorn orchestrator.main:app --port 8000

# 5) Frontend
cd frontend
npm install
npm start
```

### Environment Variables
- JWT_SECRET: HMAC secret for signing/validating JWTs
- ENCRYPTION_KEY: urlsafe base64 Fernet key (32 bytes)
- COURTLISTENER_API_KEY: token for CourtListener API
- CASE_FINDER_URL (default http://localhost:8001)
- SUMMARY_URL (default http://localhost:8002)
- CITATION_URL (default http://localhost:8003)
- PRECEDENT_URL (default http://localhost:8004)
- CASE_TYPE_LABELS_URL (default http://localhost:5000/case_types)
- TOPIC_LABELS_URL (default http://localhost:5000/topics)

### JWT Token (dev)
Generate a dev token aligned with JWT_SECRET:
```powershell
py generate_token.py
```
Paste the token into the frontend `frontend/src/components/QueryParser.js` `TOKEN` constant when testing locally.

### How It Works (Workflow)
1. Frontend sends POST /query to Orchestrator with a JWT
2. Orchestrator → Case Finder `/parse_query` then `/search`
3. Orchestrator downloads full case text and skips shallow cases
4. Orchestrator → Summary `/summarize` with case_text
5. Orchestrator → Citation `/extract_citations` with case_text
6. Orchestrator → Precedent `/find_precedents`
7. Orchestrator returns enriched results to frontend

### Notes on Summaries and Text Handling
- The system summarizes from the actual opinion text, not preexisting snippets
- Orchestrator skips cases with insufficient text (default < 400 chars)
- Summary length adapts dynamically to input length

### Useful Search Texts
- Criminal fraud cases in the Second Circuit, 2018–2025
- Antitrust monopolization cases against tech platforms, 2017–2024
- Fourth Amendment cell‑site location information post‑Carpenter, 2018–2024
- Environmental Clean Water Act wetlands WOTUS jurisdiction, 2012–2024
- Securities fraud Rule 10b‑5 scienter pleading, 2016–2025

### Troubleshooting
- 401 Invalid token: ensure JWT_SECRET matches, token not expired
- 500 Case Finder error: verify `COURTLISTENER_API_KEY` is set
- Empty results: try broader terms; remove restrictive dates/courts
- Windows ConnectionResetError in Summary service: mitigated by selector event loop policy

### Ports
- Orchestrator: http://localhost:8000
- Case Finder: http://localhost:8001
- Summary: http://localhost:8002
- Citation: http://localhost:8003
- Precedent: http://localhost:8004
- Labels: http://localhost:5000
- Frontend: http://localhost:3000

### Tests (optional)
```powershell
pytest -q
```

### License
For academic use. Verify downstream data source terms (CourtListener). 


