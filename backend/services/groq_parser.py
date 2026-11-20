import json
import logging
import re
from typing import Dict, Any, Optional
from fastapi import HTTPException
from groq import Groq

from backend.core.config import settings
from backend.models.schemas import (
    ParsedResume,
    ParsedJobDescription,
    ExperienceItem,
    EducationItem,
    ProjectItem
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a resume parser. Extract information from the resume and return ONLY a valid JSON object. No explanation, no markdown."

RESUME_EXTRACTION_PROMPT = """Extract the structured resume data from the text below and return ONLY a JSON object matching this schema:
{{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+1 234 567 8900",
  "linkedin": "url or handle",
  "github": "url or handle",
  "professional_summary": "Summary text",
  "skills": ["Skill 1", "Skill 2"],
  "experience": [
    {{
      "job_title": "Title",
      "company": "Company Name",
      "start_date": "MM/YYYY",
      "end_date": "MM/YYYY or Present",
      "duration_months": 12,
      "description": "Responsibilities and achievements"
    }}
  ],
  "education": [
    {{
      "degree": "Degree and Major",
      "institution": "University / College",
      "year": "YYYY"
    }}
  ],
  "certifications": ["Cert 1"],
  "projects": [
    {{
      "title": "Project Name",
      "description": "Details",
      "technologies": ["Python", "FastAPI"]
    }}
  ],
  "action_verbs": ["spearheaded", "developed", "architected"],
  "keywords": ["AWS", "Docker", "REST API"]
}}

Resume text:
{text}
"""

JD_EXTRACTION_PROMPT = """Extract the structured job description data from the text below and return ONLY a JSON object matching this schema:
{{
  "title": "Job Title",
  "required_skills": ["Skill 1", "Skill 2"],
  "preferred_skills": ["Skill A", "Skill B"],
  "experience_years": 3.0,
  "keywords": ["Kubernetes", "Microservices", "CI/CD"]
}}

Job description text:
{text}
"""

def clean_json_markdown(raw_str: str) -> str:
    """Strips markdown code blocks, backticks, and extraneous text."""
    if not raw_str:
        return ""
    text = raw_str.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Alternatively find the first '{' and last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return text

class GroqParser:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.primary_model = settings.GROQ_MODEL_PRIMARY
        self.fallback_model = settings.GROQ_MODEL_FALLBACK

    def _call_llm(self, prompt: str, retry_count: int = 1) -> str:
        if not self.client:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY is not configured on the server."
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        # Try primary model then fallback model
        models_to_try = [self.primary_model, self.fallback_model]
        last_error = None

        for model in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=4096
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"Failed calling model {model}: {e}")
                last_error = e

        raise HTTPException(
            status_code=502,
            detail=f"Groq API error across configured models: {str(last_error)}"
        )

    def parse_resume(self, text: str) -> ParsedResume:
        """Parses resume text into ParsedResume schema using Groq."""
        if not self.client:
            return self._heuristic_resume_parser(text)

        prompt = RESUME_EXTRACTION_PROMPT.format(text=text[:14000])
        raw_output = self._call_llm(prompt)
        cleaned = clean_json_markdown(raw_output)

        data = None
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Retry once with corrective prompt
            logger.info("First JSON parse failed, retrying with corrective prompt...")
            corrective_prompt = (
                f"Your previous response was not valid JSON. Fix it and return ONLY a raw JSON object without markdown or comments:\n\n{raw_output}"
            )
            raw_output_retry = self._call_llm(corrective_prompt)
            cleaned_retry = clean_json_markdown(raw_output_retry)
            try:
                data = json.loads(cleaned_retry)
            except json.JSONDecodeError as err:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to parse structured JSON from Groq LLM: {str(err)}"
                )

        return self._build_parsed_resume(data, text)

    def parse_job_description(self, text: str) -> ParsedJobDescription:
        """Parses JD text into ParsedJobDescription schema using Groq."""
        if not text.strip():
            return ParsedJobDescription()

        if not self.client:
            return self._heuristic_jd_parser(text)

        prompt = JD_EXTRACTION_PROMPT.format(text=text[:12000])
        raw_output = self._call_llm(prompt)
        cleaned = clean_json_markdown(raw_output)

        data = None
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            corrective_prompt = (
                f"Your previous response was not valid JSON. Fix it and return ONLY a raw JSON object without markdown:\n\n{raw_output}"
            )
            raw_output_retry = self._call_llm(corrective_prompt)
            cleaned_retry = clean_json_markdown(raw_output_retry)
            try:
                data = json.loads(cleaned_retry)
            except json.JSONDecodeError as err:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to parse structured JD JSON from Groq: {str(err)}"
                )

        return ParsedJobDescription(
            title=data.get("title", ""),
            required_skills=data.get("required_skills", []),
            preferred_skills=data.get("preferred_skills", []),
            experience_years=float(data.get("experience_years") or 0.0),
            keywords=data.get("keywords", []),
            raw_text=text
        )

    def _build_parsed_resume(self, data: Dict[str, Any], raw_text: str) -> ParsedResume:
        experience = [
            ExperienceItem(
                job_title=exp.get("job_title", ""),
                company=exp.get("company", ""),
                start_date=exp.get("start_date", ""),
                end_date=exp.get("end_date", ""),
                duration_months=exp.get("duration_months", 0),
                description=exp.get("description", "")
            )
            for exp in data.get("experience", [])
            if isinstance(exp, dict)
        ]

        education = [
            EducationItem(
                degree=edu.get("degree", ""),
                institution=edu.get("institution", ""),
                year=str(edu.get("year", ""))
            )
            for edu in data.get("education", [])
            if isinstance(edu, dict)
        ]

        projects = [
            ProjectItem(
                title=proj.get("title", ""),
                description=proj.get("description", ""),
                technologies=proj.get("technologies", [])
            )
            for proj in data.get("projects", [])
            if isinstance(proj, dict)
        ]

        return ParsedResume(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            linkedin=data.get("linkedin", ""),
            github=data.get("github", ""),
            professional_summary=data.get("professional_summary", ""),
            skills=data.get("skills", []),
            experience=experience,
            education=education,
            certifications=data.get("certifications", []),
            projects=projects,
            action_verbs=data.get("action_verbs", []),
            keywords=data.get("keywords", []),
            raw_text=raw_text
        )

    def _heuristic_resume_parser(self, text: str) -> ParsedResume:
        """Heuristic fallback parser when Groq API key is not configured."""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        email = email_match.group(0) if email_match else ""

        phone_match = re.search(r"(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
        phone = phone_match.group(0) if phone_match else ""

        linkedin_match = re.search(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[\w\-]+", text, re.IGNORECASE)
        linkedin = linkedin_match.group(0) if linkedin_match else ""

        github_match = re.search(r"(?:https?:\/\/)?(?:www\.)?github\.com\/[\w\-]+", text, re.IGNORECASE)
        github = github_match.group(0) if github_match else ""

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        name = lines[0] if lines else "Candidate"

        # Extract common tech skills
        tech_words = [
            "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
            "react", "angular", "vue", "node.js", "fastapi", "django", "flask",
            "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
            "aws", "azure", "gcp", "git", "ci/cd", "rest api", "graphql", "html", "css",
            "machine learning", "deep learning", "nlp", "pytorch", "tensorflow", "agile"
        ]
        found_skills = []
        lower_text = text.lower()
        for w in tech_words:
            if re.search(r"\b" + re.escape(w) + r"\b", lower_text):
                found_skills.append(w.title())

        # Extract action verbs
        common_verbs = [
            "spearheaded", "developed", "architected", "implemented", "designed",
            "led", "engineered", "built", "optimized", "managed", "created",
            "automated", "streamlined", "delivered", "mentored", "orchestrated"
        ]
        found_verbs = [v for v in common_verbs if re.search(r"\b" + v + r"\b", lower_text)]

        return ParsedResume(
            name=name,
            email=email,
            phone=phone,
            linkedin=linkedin,
            github=github,
            professional_summary=lines[1] if len(lines) > 1 else "",
            skills=found_skills,
            experience=[
                ExperienceItem(
                    job_title="Software Professional",
                    company="Engineering Organization",
                    description=text[:500]
                )
            ],
            education=[
                EducationItem(degree="Bachelor of Science", institution="University")
            ],
            certifications=[],
            projects=[
                ProjectItem(title="Key Engineering Project", description=text[:300], technologies=found_skills[:3])
            ],
            action_verbs=found_verbs,
            keywords=found_skills[:10],
            raw_text=text
        )

    def _heuristic_jd_parser(self, text: str) -> ParsedJobDescription:
        tech_words = [
            "python", "javascript", "typescript", "react", "fastapi", "docker",
            "kubernetes", "aws", "postgresql", "git", "ci/cd", "rest api"
        ]
        found_skills = [w.title() for w in tech_words if w in text.lower()]
        return ParsedJobDescription(
            title="Target Position",
            required_skills=found_skills,
            preferred_skills=[],
            experience_years=3.0,
            keywords=found_skills,
            raw_text=text
        )

groq_parser = GroqParser()
