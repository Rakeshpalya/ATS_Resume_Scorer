# ATS Resume Scorer

A web app that scores how well a resume matches a job description and returns actionable feedback. Built with FastAPI + Streamlit, using spaCy and Sentence Transformers for NLP and the Groq API for LLM-generated suggestions.

## What it does

1. Upload a resume (PDF / DOC / DOCX) and paste a job description.
2. The backend parses the resume, extracts skills and experience, and compares them to the JD using semantic similarity.
3. You get an ATS score, a breakdown by category (formatting, keywords, content, skill validation, ATS compatibility), and LLM-written suggestions for what to improve.
4. Past analyses are saved to your account so you can revisit them.

## Tech stack

- **Frontend:** Streamlit
- **Backend:** FastAPI (Python)
- **NLP:** spaCy (`en_core_web_md`), Sentence Transformers (`all-MiniLM-L6-v2`)
- **LLM:** Groq API (Llama 3)
- **Auth + Database:** Supabase (email/password and Google OAuth)
- **PDF report export:** WeasyPrint + Jinja2

## Project structure

```
ATS_SCORER/
├── backend/              FastAPI app, NLP services, API routes
├── frontend/             Streamlit app, views, components
├── jupyter notebooks/    Research and dataset prep (not used at runtime)
├── requirements.txt      Combined backend + frontend dependencies
└── .env.example          Template for environment variables
```

## Setup

### 1. Create a virtual environment (Windows PowerShell)

From the repository root, use Python 3.13 if it is installed. The project dependencies are declared with minimum versions, so pip selects releases compatible with the selected interpreter.

```powershell
if (-not (Test-Path .venv)) { py -3.13 -m venv .venv }
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
python -m spacy download en_core_web_md
python -m spacy download en_core_web_sm
```

The backend loads `en_core_web_md` first and falls back to `en_core_web_sm`. Both model packages must be installed for that fallback behavior.

On Windows, `python-magic` also needs the native libmagic library. Its package documentation points Windows users to `python-magic-bin`; install and test it inside the virtual environment if file-type detection reports a missing libmagic DLL:

```powershell
python -m pip install python-magic-bin==0.4.14
```

WeasyPrint's Python package may also need native Pango libraries on Windows. Follow the [current WeasyPrint installation instructions](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) and ensure its native libraries are available on `PATH`; installing Python requirements alone may not be sufficient. Linux system library instructions:

```bash
# Fedora
sudo dnf install -y cairo pango gdk-pixbuf2 libffi

# Debian / Ubuntu
sudo apt install -y libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libffi-dev
```

### 3. Configure environment variables

Copy the placeholder template only if `.env` does not already exist, then edit `.env` with your own credentials. Do not replace an existing `.env`:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

- `GROQ_API_KEY` is required by the current resume and job-description parsing pipeline.
- `SUPABASE_URL` and `SUPABASE_ANON_KEY` are used for frontend authentication. `SUPABASE_KEY` is used by backend history storage.
- `SUPABASE_JWT_SECRET` is needed only when verifying legacy HS256 tokens; asymmetric Supabase tokens use the project's JWKS endpoint.
- `AUTH_REDIRECT_URL` and `SENTENCE_TRANSFORMER_MODEL` are optional overrides.

The local Streamlit configuration is in `frontend/.streamlit/config.toml`. A `secrets.toml` file is not required for local defaults: Supabase values can come from the project-root `.env`, and the backend URL defaults to `http://localhost:8000`. If you create `frontend/.streamlit/secrets.toml` for overrides, keep it private and do not commit it.

### 4. Run the backend

From the project root, with the virtual environment active:

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now at `http://localhost:8000`.

### 5. Run the frontend

In a new terminal (activate the same virtual environment first):

```powershell
streamlit run frontend/streamlit_app.py
```

The app opens at `http://localhost:8501`.

## Notes for students

- **Never commit `.env` or `secrets.toml`** — they hold API keys. They are excluded by `.gitignore`; check before you push.
- The first backend startup downloads the Sentence Transformer model (`all-MiniLM-L6-v2`) if it is not cached.
- `jupyter notebooks/` is for experimentation and is not required to run the app.
