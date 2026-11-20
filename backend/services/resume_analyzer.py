import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.models.schemas import (
    ParsedResume,
    ParsedJobDescription,
    AnalysisResult
)
from backend.services.resume_parser import parse_resume_file
from backend.services.groq_parser import groq_parser
from backend.services.jd_matcher import jd_matcher
from backend.services.ats_scorer import ats_scorer
from backend.services.feedback_engine import feedback_engine
from backend.services.recommendation_engine import recommendation_engine

class ResumeAnalyzer:
    def analyze_resume(
        self,
        filename: str,
        content: bytes,
        jd_text: Optional[str] = None
    ) -> AnalysisResult:
        """End-to-end resume analysis pipeline."""
        # 1. Parse file bytes (PDF/DOCX)
        raw_text, _ = parse_resume_file(filename, content)

        # 2. Extract structured resume with Groq LLM (or fallback)
        parsed_resume = groq_parser.parse_resume(raw_text)

        # 3. Parse and match Job Description (if provided)
        jd_comparison = None
        if jd_text and jd_text.strip():
            parsed_jd = groq_parser.parse_job_description(jd_text.strip())
            jd_comparison = jd_matcher.match(parsed_resume, parsed_jd)

        # 4. Score Resume (5 weighted dimensions)
        scores, skill_val_items = ats_scorer.score(parsed_resume, jd_comparison)

        # 5. Generate detailed feedback
        detailed_issues = feedback_engine.generate_feedback(
            resume=parsed_resume,
            scores=scores,
            skill_val_items=skill_val_items,
            jd_comp=jd_comparison
        )

        # 6. Generate recommendations, strengths, and action items
        strengths, critical_issues, recommendations, action_items = (
            recommendation_engine.generate_recommendations_and_strengths(
                resume=parsed_resume,
                scores=scores,
                skill_val_items=skill_val_items,
                issues=detailed_issues,
                jd_comp=jd_comparison
            )
        )

        analysis_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        return AnalysisResult(
            id=analysis_id,
            filename=filename,
            created_at=created_at,
            scores=scores,
            parsed_resume=parsed_resume,
            jd_comparison=jd_comparison,
            skill_validation=skill_val_items,
            strengths=strengths,
            critical_issues=critical_issues,
            detailed_issues=detailed_issues,
            recommendations=recommendations,
            action_items=action_items
        )

resume_analyzer = ResumeAnalyzer()
