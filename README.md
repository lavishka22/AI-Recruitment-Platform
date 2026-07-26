# AI Recruitment Platform

AI-powered recruitment platform for resume parsing, GitHub analysis, candidate evaluation, and explainable ranking. Intended for technical hiring teams who want an automated, explainable shortlist of candidates from resumes and GitHub signals.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.x-green.svg)](https://www.python.org/)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-yellow.svg)](frontend)

## Table of contents
- [Features](#features)
- [Stack / Architecture](#stack--architecture)
- [Project structure](#project-structure)
- [Quick start (development)](#quick-start-development)
  - [Backend (FastAPI)](#backend-fastapi)
  - [Frontend (React + Vite)](#frontend-react--vite)
  - [Database](#database)
- [API / Docs](#api--docs)
- [Environment variables](#environment-variables)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [License](#license)

## Features
- Resume parsing and normalization
- GitHub analysis integration
- Evaluation and explainable candidate ranking
- REST API (FastAPI) and single-page frontend (React + Vite)

## Stack / Architecture
- Languages: Python (backend), JavaScript (frontend), SQL (schema)
- Backend: FastAPI application in `backend/app` (has routes for uploads, resume processing, evaluation, GitHub integration; CORSMiddleware configured for localhost:5173)
- Frontend: React + Vite app in `frontend/`
- Database: SQL schema present at `database/schema.sql` (project uses Supabase client inside the backend code)

How it fits together: the frontend sends candidate/resume data to the FastAPI backend, the backend stores/queries candidate data (Supabase/Postgres), performs parsing and evaluation, and returns ranked/explainable scores to the UI. FastAPI exposes interactive OpenAPI docs.

## Project structure
```
LICENSE
README.md
Screenshots/        - example UI images
backend/            - Python FastAPI backend
  .env.example
  requirements.txt
  app/
    main.py         - FastAPI app, mounts API routers, health endpoints
    api/            - upload, resume, evaluation, github routers
    core/           - clients/config (supabase client, etc.)
    services/       - business logic for parsing, evaluation
    repositories/   - DB access layer
    schemas/        - pydantic schemas
frontend/           - React + Vite SPA
  .env.example
  package.json
  src/
database/
  schema.sql        - database schema (Postgres)
```

## Quick start (development)
Important ports used:
- Backend (FastAPI): 8000
- Frontend (Vite): 5173

1) Backend
```bash
# from project root
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate     # Windows (Powershell)
pip install -r backend/requirements.txt

# set environment variables from backend/.env.example (see section below)
# run the backend
uvicorn backend.app.main:app --reload --port 8000
```

2) Frontend
```bash
cd frontend
npm install
npm run dev
# open http://localhost:5173 in your browser
```

3) Database
- If you're using Postgres (or supabase), apply the schema:
```bash
# Example for a local Postgres instance:
psql $DATABASE_URL -f database/schema.sql
```
- If using Supabase, make sure the Supabase project has the same schema or run the SQL there.

## API / Docs
- Root: GET http://localhost:8000/  — quick running check
- Health: GET http://localhost:8000/health
- Database health: GET http://localhost:8000/health/database
- FastAPI interactive docs: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

Example:
```bash
curl http://localhost:8000/health
# expected: JSON with "status": "healthy"
```

Note: The backend mounts routers for upload, resume, evaluation and GitHub-related endpoints (see `backend/app/api/` for exact paths and request formats). Add short examples for those endpoints in README once you decide canonical paths/parameters.

## Environment variables
Document the environment variables and point contributors to the example files:
- backend/.env.example — copy to backend/.env and populate:
  - SUPABASE_URL
  - SUPABASE_KEY
  - GITHUB_TOKEN
  - OPENAI_API_KEY (optional)
  - EMAIL_ADDRESS (optional)
  - EMAIL_PASSWORD (optional)
- frontend/.env.example — copy to frontend/.env for frontend-specific config (API base URL, etc.)

## Screenshots
Include UI screenshots from `Screenshots/` to show candidate list, resume view, and ranking explanations.

## Contributing
- Add a CONTRIBUTING.md with:
  - dev workflow for backend and frontend
  - style/formatting (Black/flake8 for Python, Prettier/eslint for JS)
  - how to run tests (if you add tests)
- Use descriptive PR titles and link related issues.
- Add a simple issue template for feature requests / bugs.

## Troubleshooting
- If you see CORS errors, confirm frontend is running on 5173 and backend CORS origins are correct (backend app allows localhost:5173).
- If database health fails, ensure SUPABASE credentials / DATABASE_URL are correct and schema is applied.

## License
This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file.
