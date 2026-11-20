from typing import List, Tuple, Optional
from backend.models.schemas import (
    ParsedResume,
    ScoreBreakdown,
    SkillValidationItem,
    JDComparisonResult,
    IssueDetail
)

class RecommendationEngine:
    def generate_recommendations_and_strengths(
        self,
        resume: ParsedResume,
        scores: ScoreBreakdown,
        skill_val_items: List[SkillValidationItem],
        issues: List[IssueDetail],
        jd_comp: Optional[JDComparisonResult] = None
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        strengths: List[str] = []
        critical_issues: List[str] = []
        recommendations: List[str] = []
        action_items: List[str] = []

        # Strengths evaluation
        if scores.formatting_score >= 16:
            strengths.append("Standard, ATS-parseable section hierarchy and well-structured layout.")
        if len(resume.skills) >= 12:
            strengths.append(f"Strong technical vocabulary featuring {len(resume.skills)} distinct industry skills.")
        if len(resume.action_verbs) >= 10:
            strengths.append(f"High power-verb density ({len(resume.action_verbs)} action verbs) driving impactful statements.")
        
        validated_count = sum(1 for item in skill_val_items if item.validated)
        val_pct = (validated_count / len(skill_val_items) * 100) if skill_val_items else 0
        if val_pct >= 80:
            strengths.append(f"High skill validation rate ({round(val_pct)}%) with strong contextual evidence across projects and roles.")

        if jd_comp and jd_comp.match_percentage >= 70:
            strengths.append(f"High relevance to target Job Description ({round(jd_comp.match_percentage)}% keyword match).")
        if resume.linkedin and resume.github:
            strengths.append("Complete professional contact portfolio (LinkedIn and GitHub included).")

        # Fallback if no strengths detected
        if not strengths:
            strengths.append("Clear foundational resume structure ready for targeted optimization.")

        # Critical issues evaluation
        for issue in issues:
            if issue.severity_level == "Critical":
                critical_issues.append(f"{issue.issue_title}: {issue.explanation[:120]}...")

        # Action items & Recommendations
        for issue in issues:
            if issue.action_items:
                for item in issue.action_items[:2]:
                    if item not in action_items:
                        action_items.append(item)

        if scores.keywords_score < 18:
            recommendations.append("Incorporate more relevant technical skills and keywords directly matching current industry postings.")
        if scores.content_score < 18:
            recommendations.append("Rewrite bullet points to lead with strong action verbs followed by quantifiable metric outcomes.")
        if val_pct < 75:
            recommendations.append("Ensure every skill in your 'Skills' block is referenced at least once in your experience bullets or project descriptions.")
        if jd_comp and jd_comp.missing_keywords:
            top_miss = jd_comp.missing_keywords[:5]
            recommendations.append(f"Add the following missing job description keywords: {', '.join(top_miss)}.")

        if not recommendations:
            recommendations.append("Your resume meets high ATS standards! Keep technical keywords and metrics refreshed as your responsibilities evolve.")

        return strengths, critical_issues, recommendations, action_items

recommendation_engine = RecommendationEngine()
