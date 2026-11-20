import re
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from backend.models.schemas import (
    ParsedResume,
    ScoreBreakdown,
    SkillValidationItem,
    JDComparisonResult
)
from backend.utils.matching import (
    extract_measurable_metrics,
    detect_decorative_characters,
    detect_privacy_risks,
    normalize_skill,
    fuzzy_match_skill
)
from backend.services.jd_matcher import jd_matcher

class ATSScorer:
    def __init__(self):
        pass

    def evaluate_formatting(self, resume: ParsedResume) -> Tuple[float, Dict[str, Any]]:
        score = 0.0
        details = {}

        # 1. Base points for key sections detected (up to 10 pts)
        has_exp = len(resume.experience) > 0
        has_edu = len(resume.education) > 0
        has_skills = len(resume.skills) > 0
        has_summary = bool(resume.professional_summary.strip())
        has_projects = len(resume.projects) > 0

        section_pts = 0.0
        if has_exp:
            section_pts += 3.0
        if has_edu:
            section_pts += 2.0
        if has_skills:
            section_pts += 2.0
        if has_summary:
            section_pts += 1.5
        if has_projects:
            section_pts += 1.5
        score += section_pts
        details["section_points"] = section_pts

        # 2. Tiered bullet count score (up to 5 pts)
        raw = resume.raw_text or ""
        bullets = re.findall(r"^[ \t]*[\u2022\u2023\u25E6\u2043\u2219\*\-][ \t]+(.+)$", raw, re.MULTILINE)
        if not bullets and resume.experience:
            for exp in resume.experience:
                lines = [l for l in exp.description.split("\n") if len(l.strip()) > 10]
                bullets.extend(lines)

        bullet_count = len(bullets)
        details["bullet_count"] = bullet_count
        if bullet_count >= 15:
            bullet_pts = 5.0
        elif bullet_count >= 10:
            bullet_pts = 4.0
        elif bullet_count >= 5:
            bullet_pts = 3.0
        elif bullet_count >= 3:
            bullet_pts = 2.0
        elif bullet_count >= 1:
            bullet_pts = 1.0
        else:
            bullet_pts = 0.0
        score += bullet_pts
        details["bullet_points"] = bullet_pts

        # 3. Section completeness tier: 4 sections filled (5 pts), 3 (4 pts), 2 (3 pts), 1 (2 pts)
        filled_count = sum([has_exp, has_edu, has_skills, has_projects or has_summary])
        details["filled_sections"] = filled_count
        if filled_count >= 4:
            completeness_pts = 5.0
        elif filled_count == 3:
            completeness_pts = 4.0
        elif filled_count == 2:
            completeness_pts = 3.0
        elif filled_count == 1:
            completeness_pts = 2.0
        else:
            completeness_pts = 0.0
        score += completeness_pts
        details["completeness_points"] = completeness_pts

        final_formatting = min(20.0, score)
        return final_formatting, details

    def evaluate_keywords(self, resume: ParsedResume, jd_comp: Optional[JDComparisonResult]) -> Tuple[float, Dict[str, Any]]:
        score = 0.0
        details = {}

        # 1. Resume keyword volume tiers (max 10 pts)
        kw_count = len(resume.keywords)
        details["keywords_count"] = kw_count
        if kw_count >= 20:
            kw_pts = 10.0
        elif kw_count >= 15:
            kw_pts = 8.0
        elif kw_count >= 10:
            kw_pts = 6.0
        elif kw_count >= 5:
            kw_pts = 4.0
        elif kw_count >= 1:
            kw_pts = 2.0
        else:
            kw_pts = 0.0
        score += kw_pts
        details["keyword_volume_pts"] = kw_pts

        # 2. Skills volume tiers (max 10 pts)
        skills_count = len(resume.skills)
        details["skills_count"] = skills_count
        if skills_count >= 15:
            sk_pts = 10.0
        elif skills_count >= 10:
            sk_pts = 8.0
        elif skills_count >= 5:
            sk_pts = 6.0
        elif skills_count >= 3:
            sk_pts = 4.0
        elif skills_count >= 1:
            sk_pts = 2.0
        else:
            sk_pts = 0.0
        score += sk_pts
        details["skills_volume_pts"] = sk_pts

        # 3. JD comparison match tier (when JD is provided) via RapidFuzz matching (max 5 pts)
        if jd_comp and (jd_comp.matched_keywords or jd_comp.missing_keywords):
            match_pct = jd_comp.match_percentage
            if match_pct >= 70.0:
                jd_pts = 5.0
            elif match_pct >= 50.0:
                jd_pts = 4.0
            elif match_pct >= 30.0:
                jd_pts = 3.0
            elif match_pct >= 10.0:
                jd_pts = 2.0
            elif match_pct > 0.0:
                jd_pts = 1.0
            else:
                jd_pts = 0.0
        else:
            # Baseline when JD is not provided
            jd_pts = 5.0 if (skills_count >= 8 and kw_count >= 8) else 3.5
        score += jd_pts
        details["jd_match_pts"] = jd_pts

        final_keywords = min(25.0, score)
        return final_keywords, details

    def evaluate_content(self, resume: ParsedResume) -> Tuple[float, Dict[str, Any]]:
        score = 0.0
        details = {}

        # 1. Action verbs tier (max 10 pts)
        verbs_count = len(resume.action_verbs)
        details["action_verbs_count"] = verbs_count
        if verbs_count >= 15:
            v_pts = 10.0
        elif verbs_count >= 10:
            v_pts = 8.0
        elif verbs_count >= 7:
            v_pts = 6.0
        elif verbs_count >= 5:
            v_pts = 4.0
        elif verbs_count >= 3:
            v_pts = 2.0
        elif verbs_count >= 1:
            v_pts = 1.0
        else:
            v_pts = 0.0
        score += v_pts
        details["action_verbs_pts"] = v_pts

        # 2. Measurable achievements regex patterns (max 5 pts)
        raw_text = resume.raw_text or ""
        metrics = extract_measurable_metrics(raw_text)
        details["metrics_count"] = len(metrics)
        details["metrics_samples"] = metrics[:5]
        m_count = len(metrics)
        if m_count >= 10:
            m_pts = 5.0
        elif m_count >= 7:
            m_pts = 4.0
        elif m_count >= 5:
            m_pts = 3.0
        elif m_count >= 3:
            m_pts = 2.0
        elif m_count >= 1:
            m_pts = 1.0
        else:
            m_pts = 0.0
        score += m_pts
        details["metrics_pts"] = m_pts

        # 3. Grammar quality baseline (10 pts minus half of grammar penalty)
        grammar_penalty = 0.0
        # Check repeated words or blatant typo patterns
        repeated_words = len(re.findall(r"\b(\w+)\s+\1\b", raw_text, re.IGNORECASE))
        grammar_penalty += repeated_words * 0.5
        grammar_pts = max(0.0, 10.0 - (0.5 * grammar_penalty))
        score += grammar_pts
        details["grammar_pts"] = grammar_pts
        details["grammar_penalty"] = grammar_penalty

        final_content = min(25.0, score)
        return final_content, details

    def evaluate_skill_validation(self, resume: ParsedResume) -> Tuple[float, List[SkillValidationItem]]:
        """Cross-reference listed skills against project descriptions and work experience."""
        total_skills = len(resume.skills)
        if total_skills == 0:
            return 0.0, []

        st_model = jd_matcher.get_st_model()

        # Build context pool: Experience and Projects descriptions
        exp_texts = [f"{e.job_title} at {e.company}: {e.description}" for e in resume.experience]
        proj_texts = [f"{p.title}: {p.description} {' '.join(p.technologies)}" for p in resume.projects]

        all_evidence = exp_texts + proj_texts
        combined_evidence_str = "\n".join(all_evidence).lower()

        # Pre-compute evidence embeddings if sentence transformers available
        evidence_embeddings = None
        if st_model and all_evidence:
            try:
                evidence_embeddings = st_model.encode(all_evidence, convert_to_numpy=True)
            except Exception:
                evidence_embeddings = None

        validated_count = 0
        items: List[SkillValidationItem] = []

        for skill in resume.skills:
            norm_skill = normalize_skill(skill)
            matched = False
            matched_in = "none"
            evidence_snippet = ""
            confidence = 0.0

            # 1. Exact or substring match in experience/projects
            for idx, exp in enumerate(resume.experience):
                exp_text = f"{exp.job_title} {exp.description}".lower()
                if norm_skill in exp_text or fuzzy_match_skill(norm_skill, exp_text):
                    matched = True
                    matched_in = "experience"
                    confidence = 1.0
                    evidence_snippet = f"Used in role '{exp.job_title}' at {exp.company}"
                    break

            if not matched:
                for idx, proj in enumerate(resume.projects):
                    proj_text = f"{proj.title} {proj.description} {' '.join(proj.technologies)}".lower()
                    if norm_skill in proj_text or any(fuzzy_match_skill(norm_skill, t) for t in proj.technologies):
                        matched = True
                        matched_in = "projects"
                        confidence = 1.0
                        evidence_snippet = f"Demonstrated in project '{proj.title}'"
                        break

            # 2. Embedding semantic match (cosine similarity >= 0.60)
            if not matched and st_model is not None and evidence_embeddings is not None and len(evidence_embeddings) > 0:
                try:
                    s_emb = st_model.encode(skill, convert_to_numpy=True)
                    s_norm = np.linalg.norm(s_emb)
                    if s_norm > 0:
                        sims = np.dot(evidence_embeddings, s_emb) / (np.linalg.norm(evidence_embeddings, axis=1) * s_norm)
                        max_idx = int(np.argmax(sims))
                        max_sim = float(sims[max_idx])
                        if max_sim >= 0.60:
                            matched = True
                            confidence = round(max_sim, 2)
                            matched_in = "experience" if max_idx < len(exp_texts) else "projects"
                            evidence_snippet = f"Contextually applied ({round(max_sim * 100)}% semantic relevance)"
                except Exception:
                    pass

            if matched:
                validated_count += 1

            items.append(
                SkillValidationItem(
                    skill=skill,
                    validated=matched,
                    confidence=confidence,
                    matched_in=matched_in,
                    evidence_snippet=evidence_snippet
                )
            )

        score = (validated_count / total_skills) * 15.0
        return round(score, 2), items

    def evaluate_ats_compatibility(self, resume: ParsedResume) -> Tuple[float, Dict[str, Any]]:
        score = 15.0
        details = {}
        deductions = {}

        raw_text = resume.raw_text or ""

        # 1. Location / Privacy check: Regex for street address and 5-digit zip
        has_risk, risk_items = detect_privacy_risks(raw_text)
        if has_risk:
            score -= 5.0
            deductions["privacy_address_risk"] = -5.0
            details["privacy_risks"] = risk_items

        # 2. Special decorative characters (│, ║, tables)
        decorative = detect_decorative_characters(raw_text)
        if decorative:
            deduct_pts = min(4.0, len(decorative) * 2.0)
            score -= deduct_pts
            deductions["decorative_characters"] = -deduct_pts
            details["decorative_chars"] = decorative

        # 3. Missing/Short key sections
        if not resume.experience:
            score -= 4.0
            deductions["missing_experience"] = -4.0
        if not resume.education:
            score -= 2.0
            deductions["missing_education"] = -2.0

        details["deductions"] = deductions
        final_score = max(0.0, min(15.0, score))
        return round(final_score, 2), details

    def score(
        self,
        resume: ParsedResume,
        jd_comp: Optional[JDComparisonResult] = None
    ) -> Tuple[ScoreBreakdown, List[SkillValidationItem]]:
        # 1. Formatting (20 pts)
        formatting_score, _ = self.evaluate_formatting(resume)
        # 2. Keywords (25 pts)
        keywords_score, _ = self.evaluate_keywords(resume, jd_comp)
        # 3. Content (25 pts)
        content_score, content_details = self.evaluate_content(resume)
        # 4. Skill Validation (15 pts)
        skill_val_score, skill_val_items = self.evaluate_skill_validation(resume)
        # 5. ATS Compatibility (15 pts)
        ats_compat_score, _ = self.evaluate_ats_compatibility(resume)

        # Normalized percentages
        formatting_pct = (formatting_score / 20.0) * 100.0
        keywords_pct = (keywords_score / 25.0) * 100.0
        content_pct = (content_score / 25.0) * 100.0
        skill_validation_pct = (skill_val_score / 15.0) * 100.0 if resume.skills else 100.0
        ats_compatibility_pct = (ats_compat_score / 15.0) * 100.0

        skills_keywords_pct = (keywords_pct * 0.6) + (skill_validation_pct * 0.4)
        base_score = (
            skills_keywords_pct   * 0.40 +
            content_pct           * 0.30 +
            formatting_pct        * 0.15 +
            ats_compatibility_pct * 0.15
        )

        penalties: Dict[str, float] = {}
        bonuses: Dict[str, float] = {}

        # Penalties: missing JD keywords (>70% missing: -15, >50%: -10, >30%: -5)
        if jd_comp and (jd_comp.matched_keywords or jd_comp.missing_keywords):
            total_jd_kw = len(jd_comp.matched_keywords) + len(jd_comp.missing_keywords)
            if total_jd_kw > 0:
                missing_ratio = len(jd_comp.missing_keywords) / total_jd_kw
                if missing_ratio > 0.70:
                    penalties["severe_missing_jd_keywords"] = -15.0
                elif missing_ratio > 0.50:
                    penalties["moderate_missing_jd_keywords"] = -10.0
                elif missing_ratio > 0.30:
                    penalties["mild_missing_jd_keywords"] = -5.0

        # Bonuses: validation >= 90% (+2), perfect grammar (+1)
        if skill_validation_pct >= 90.0 and len(resume.skills) >= 5:
            bonuses["high_skill_validation"] = 2.0
        if content_details.get("grammar_penalty", 0.0) == 0.0:
            bonuses["clean_grammar"] = 1.0

        final_score = base_score + sum(penalties.values()) + sum(bonuses.values())
        overall_score = min(100.0, max(0.0, final_score))

        # Interpretation
        if overall_score >= 85.0:
            interpretation = "Excellent - Highly ATS Optimized"
        elif overall_score >= 70.0:
            interpretation = "Strong Match - Minor Optimization Needed"
        elif overall_score >= 50.0:
            interpretation = "Moderate - Significant Gaps Identified"
        else:
            interpretation = "Needs Immediate Attention"

        breakdown = ScoreBreakdown(
            formatting_score=round(formatting_score, 1),
            formatting_max=20.0,
            keywords_score=round(keywords_score, 1),
            keywords_max=25.0,
            content_score=round(content_score, 1),
            content_max=25.0,
            skill_validation_score=round(skill_val_score, 1),
            skill_validation_max=15.0,
            ats_compatibility_score=round(ats_compat_score, 1),
            ats_compatibility_max=15.0,
            overall_score=round(overall_score, 1),
            interpretation=interpretation,
            penalties=penalties,
            bonuses=bonuses
        )

        return breakdown, skill_val_items

ats_scorer = ATSScorer()
