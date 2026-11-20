# 🎯 AI ATS Resume Scorer & Analyzer System

A production-grade, AI-powered Applicant Tracking System (ATS) Resume Scorer and Analyzer application. It provides deep diagnostic resume scoring, semantic job description matching, skill cross-validation, and downloadable PDF reports.

---

## 🌟 Key Features

1. **Dual-Service Architecture**:
   - **Backend**: FastAPI (Python) on port 8000 handling file extraction, Groq LLM parsing, spaCy & Sentence Transformer semantic analysis, scoring algorithms, and PDF exports.
   - **Frontend**: Streamlit on port 8501 delivering an interactive web interface with Home, ATS Scorer, History, and Resources views.
2. **Groq LLM Extraction**:
   - High-speed resume & job description parsing into structured JSON with automatic retry and fence cleanup.
3. **Local NLP & Semantic Intelligence**:
   - spaCy (`en_core_web_md` / `en_core_web_sm`) and Sentence Transformers (`all-MiniLM-L6-v2`) for local semantic similarity and context cross-validation.
4. **5-Dimension Weighted ATS Scoring Engine**:
   - **Formatting (20 pts)**: Layout hierarchy, standard section headers, bullet density, and completeness.
   - **Keywords (25 pts)**: Keyword volume, technical skill density, and job description alignment.
   - **Content (25 pts)**: High-impact action power verbs, quantifiable metrics (`\d+%`, `\$\d+`), and grammar quality.
   - **Skill Cross-Validation (15 pts)**: Validates listed skills against project descriptions and work history.
   - **ATS Compatibility (15 pts)**: Detects privacy risks (full street addresses/zip codes) and unparseable symbols.
5. **Supabase Integration**:
   - User authentication (Email/Password + Google OAuth).
   - Analysis history storage protected by Row Level Security (RLS).
6. **Executive Diagnostic Reports**:
   - Downloadable WeasyPrint PDF and plaintext diagnostic summaries with prioritized action items and before/after improvements.

---

## 📁 Project Directory Structure

```
ATS_Resume_Scorer!/
├── .env.example
├── .env
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── supabase/
│   └── migrations/
│       └── 20261030215000_create_analyses.sql
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py
│   │   └── routes.py
│   ├── core/
│   │   └── config.py
│   ├── database/
│   │   └── supabase_db.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── ats_scorer.py
│   │   ├── feedback_engine.py
│   │   ├── groq_parser.py
│   │   ├── jd_matcher.py
│   │   ├── pdf_export.py
│   │   ├── recommendation_engine.py
│   │   ├── report_generator.py
│   │   ├── resume_analyzer.py
│   │   └── resume_parser.py
│   ├── templates/
│   │   ├── action_items.html
│   │   ├── jd_comparison.html
│   │   ├── quick_actions.html
│   │   └── summary.html
│   └── utils/
│       ├── file_utils.py
│       └── matching.py
├── frontend/
│   ├── streamlit_app.py
│   ├── assets/
│   │   └── styles.css
│   ├── components/
│   │   ├── _helpers.py
│   │   ├── action_items.py
│   │   ├── dashboard.py
│   │   ├── detailed_feedback.py
│   │   ├── jd_comparison.py
│   │   ├── recommendations.py
│   │   ├── score_display.py
│   │   ├── skill_validation.py
│   │   └── strengths_issues.py
│   ├── services/
│   │   ├── api_client.py
│   │   └── supabase_client.py
│   └── views/
│       ├── history.py
│       ├── landing.py
│       ├── resources.py
│       └── scorer.py
└── tests/
    ├── test_auth.py
    ├── test_frontend_auth_errors.py
    ├── test_frontend_secret_loading.py
    ├── test_groq_parser.py
    ├── test_supabase_db.py
    ├── test_supabase_schema.py
    └── test_upload_and_pdf.py
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13.
- (Optional) Free Groq API key from [console.groq.com](https://console.groq.com).
- (Optional) Free Supabase project from [supabase.com](https://supabase.com).

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_JWT_SECRET=your_supabase_jwt_secret_here
AUTH_REDIRECT_URL=http://localhost:8501
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
```

### 4. Supabase Database Migration
In your Supabase project dashboard, navigate to the **SQL Editor**, paste the SQL from `supabase/migrations/20261030215000_create_analyses.sql`, and execute it to create the `analyses` table with Row Level Security (RLS).

### 5. Running the Tests
Run pytest across the entire unit test suite:
```bash
python -m pytest -q
```

### 6. Start the Backend API (FastAPI)
```bash
uvicorn backend.main:app --reload --port 8000
```
Interactive Swagger API docs available at: `http://localhost:8000/docs`

### 7. Start the Frontend UI (Streamlit)
```bash
streamlit run frontend/streamlit_app.py
```
Open your browser at `http://localhost:8501`.
