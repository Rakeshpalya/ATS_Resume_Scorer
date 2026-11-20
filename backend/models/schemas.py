from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ExperienceItem(BaseModel):
    job_title: str = ""
    company: str = ""
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""
    duration_months: Optional[int] = 0
    description: str = ""

class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    year: Optional[str] = ""

class ProjectItem(BaseModel):
    title: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)

class ParsedResume(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    professional_summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    action_verbs: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = ""

class ParsedJobDescription(BaseModel):
    title: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_years: Optional[float] = 0.0
    keywords: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = ""

class IssueDetail(BaseModel):
    issue_title: str
    severity_level: str  # Critical, Warning, Tip
    ats_impact: str      # High, Medium, Low
    explanation: str
    where_it_appears: str
    how_to_fix: str
    action_items: List[str] = Field(default_factory=list)
    example_improvement: Optional[Dict[str, str]] = None  # {"before": ..., "after": ...}

class SkillValidationItem(BaseModel):
    skill: str
    validated: bool
    confidence: float = 0.0
    matched_in: str = ""  # "experience", "projects", "none"
    evidence_snippet: str = ""

class JDComparisonResult(BaseModel):
    match_percentage: float = 0.0
    semantic_similarity: float = 0.0
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)

class ScoreBreakdown(BaseModel):
    formatting_score: float = 0.0
    formatting_max: float = 20.0
    keywords_score: float = 0.0
    keywords_max: float = 25.0
    content_score: float = 0.0
    content_max: float = 25.0
    skill_validation_score: float = 0.0
    skill_validation_max: float = 15.0
    ats_compatibility_score: float = 0.0
    ats_compatibility_max: float = 15.0
    overall_score: float = 0.0
    interpretation: str = ""
    penalties: Dict[str, float] = Field(default_factory=dict)
    bonuses: Dict[str, float] = Field(default_factory=dict)

class AnalysisResult(BaseModel):
    id: Optional[str] = None
    filename: str
    created_at: Optional[str] = None
    scores: ScoreBreakdown
    parsed_resume: ParsedResume
    jd_comparison: Optional[JDComparisonResult] = None
    skill_validation: List[SkillValidationItem] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    critical_issues: List[str] = Field(default_factory=list)
    detailed_issues: List[IssueDetail] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)

class AnalysisHistorySummary(BaseModel):
    id: str
    filename: str
    ats_score: float
    keyword_match: float
    missing_keywords: List[str]
    created_at: str

class UserProfile(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = "authenticated"
