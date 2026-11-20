from typing import List, Optional
from backend.models.schemas import (
    ParsedResume,
    ScoreBreakdown,
    SkillValidationItem,
    JDComparisonResult,
    IssueDetail
)
from backend.utils.matching import detect_privacy_risks, extract_measurable_metrics

class FeedbackEngine:
    def generate_feedback(
        self,
        resume: ParsedResume,
        scores: ScoreBreakdown,
        skill_val_items: List[SkillValidationItem],
        jd_comp: Optional[JDComparisonResult] = None
    ) -> List[IssueDetail]:
        issues: List[IssueDetail] = []
        raw_text = resume.raw_text or ""

        # 1. Missing Projects section
        if not resume.projects:
            issues.append(
                IssueDetail(
                    issue_title="Missing Projects Section",
                    severity_level="Critical",
                    ats_impact="High",
                    explanation="ATS parsers and technical recruiters heavily favor candidates with dedicated Projects demonstrating applied skills and real-world tools.",
                    where_it_appears="Entire Resume",
                    how_to_fix="Add a dedicated 'Projects' section featuring 2-3 significant projects with tools used and quantifiable outcomes.",
                    action_items=[
                        "Create a 'Projects' section heading.",
                        "Add at least 2 technical projects listing technologies used in parenthesis.",
                        "Describe your role and impact using strong action verbs."
                    ],
                    example_improvement={
                        "before": "No projects listed.",
                        "after": "Distributed Task Queue (Python, Redis, Docker)\n• Built an asynchronous task distribution pipeline handling 50k requests/min with <100ms latency."
                    }
                )
            )

        # 2. Missing Experience section
        if not resume.experience:
            issues.append(
                IssueDetail(
                    issue_title="Missing Professional Experience",
                    severity_level="Critical",
                    ats_impact="High",
                    explanation="Professional experience is the primary section ATS systems use to calculate candidate seniority and relevance.",
                    where_it_appears="Work Experience Section",
                    how_to_fix="Include chronological employment history or relevant internships with job titles, company names, and dates.",
                    action_items=[
                        "Add work history in reverse chronological order.",
                        "Provide month and year for start/end dates.",
                        "Detail core responsibilities and achievements."
                    ],
                    example_improvement={
                        "before": "Employment history omitted.",
                        "after": "Software Engineer | Tech Corp | 06/2022 - Present\n• Engineered microservices using FastAPI and PostgreSQL, serving 120k active users."
                    }
                )
            )

        # 3. Missing Education section
        if not resume.education:
            issues.append(
                IssueDetail(
                    issue_title="Missing Education Section",
                    severity_level="Warning",
                    ats_impact="Medium",
                    explanation="Many enterprise ATS filters verify minimum degree qualifications automatically.",
                    where_it_appears="Education Section",
                    how_to_fix="Add your degree, institution, and graduation year.",
                    action_items=[
                        "Create an Education section.",
                        "Specify degree, major, university, and year."
                    ],
                    example_improvement={
                        "before": "No education listed.",
                        "after": "B.S. in Computer Science | State University | 2023"
                    }
                )
            )

        # 4. Missing Skills section
        if len(resume.skills) < 5:
            issues.append(
                IssueDetail(
                    issue_title="Insufficient or Missing Skills Section",
                    severity_level="Critical",
                    ats_impact="High",
                    explanation="ATS keyword matching algorithms scan the skills block to match candidate profiles to job requisitions.",
                    where_it_appears="Skills Section",
                    how_to_fix="Categorize and list at least 10-15 relevant hard and soft skills.",
                    action_items=[
                        "Create categorized skill groups: Languages, Frameworks, Cloud, Databases.",
                        "Incorporate industry-standard keywords from target job descriptions."
                    ],
                    example_improvement={
                        "before": "Skills: Coding, Problem Solving",
                        "after": "Languages: Python, Go, TypeScript | Frameworks: FastAPI, React | Cloud: AWS, Docker, Kubernetes"
                    }
                )
            )

        # 5. Weak Action Verbs
        if len(resume.action_verbs) < 7:
            issues.append(
                IssueDetail(
                    issue_title="Low Action Verb Density",
                    severity_level="Warning",
                    ats_impact="Medium",
                    explanation="Resumes that start bullet points with passive words (e.g., 'Responsible for', 'Helped with') receive lower content scores.",
                    where_it_appears="Bullet points in Experience and Projects",
                    how_to_fix="Begin each bullet point with high-impact power verbs like 'Architected', 'Spearheaded', 'Optimized', or 'Automated'.",
                    action_items=[
                        "Replace 'Responsible for' with active verbs.",
                        "Vary your action verbs to showcase leadership, technical execution, and problem solving."
                    ],
                    example_improvement={
                        "before": "Responsible for managing the database and assisting backend developers.",
                        "after": "Architected and optimized PostgreSQL database queries, reducing query response times by 35%."
                    }
                )
            )

        # 6. Lack of Quantifiable Metrics
        metrics = extract_measurable_metrics(raw_text)
        if len(metrics) < 3:
            issues.append(
                IssueDetail(
                    issue_title="Lack of Measurable Achievements",
                    severity_level="Critical",
                    ats_impact="High",
                    explanation="ATS and hiring managers look for quantifiable proof of business impact (percentages, revenue, performance gains, user scale).",
                    where_it_appears="Experience Bullet Points",
                    how_to_fix="Use the XYZ formula: 'Accomplished [X] as measured by [Y] by doing [Z]'.",
                    action_items=[
                        "Add numbers, percentages, or dollar values to at least 4 bullets.",
                        "Quantify user scale, latency improvements, or cost reductions."
                    ],
                    example_improvement={
                        "before": "Improved website speed and helped attract more visitors.",
                        "after": "Reduced Largest Contentful Paint (LCP) by 45%, resulting in a 22% increase in user conversion."
                    }
                )
            )

        # 7. Low Skill Validation (< 70% validated)
        unvalidated = [item.skill for item in skill_val_items if not item.validated]
        if resume.skills and (len(unvalidated) / len(resume.skills)) > 0.30:
            sample_unvalidated = ", ".join(unvalidated[:4])
            issues.append(
                IssueDetail(
                    issue_title=f"Unvalidated Listed Skills ({len(unvalidated)} skills lack context)",
                    severity_level="Warning",
                    ats_impact="Medium",
                    explanation=f"Skills like {sample_unvalidated} appear in your skills list but are never mentioned or evidenced in your work history or projects.",
                    where_it_appears="Skills vs Experience & Projects",
                    how_to_fix="Mention how and where you applied each listed skill inside your bullet points.",
                    action_items=[
                        f"Integrate unvalidated skills ({sample_unvalidated}) into your experience bullets.",
                        "Alternatively, remove skills you cannot actively discuss in an interview."
                    ],
                    example_improvement={
                        "before": "Skills list contains 'Kubernetes', but experience description never mentions Kubernetes.",
                        "after": "Experience bullet: 'Deployed and maintained multi-region Kubernetes clusters on AWS EKS.'"
                    }
                )
            )

        # 8. Location Privacy Risk
        has_risk, risk_items = detect_privacy_risks(raw_text)
        if has_risk:
            issues.append(
                IssueDetail(
                    issue_title="Location Privacy Risk (Street Address / Zip Code)",
                    severity_level="Warning",
                    ats_impact="Medium",
                    explanation="Including full street addresses or postal zip codes creates privacy risks and can trigger outdated geographic filtering in automated ATS systems.",
                    where_it_appears="Header / Contact Information",
                    how_to_fix="Replace exact street addresses and zip codes with 'City, State' or 'Remote'.",
                    action_items=[
                        "Remove house/apartment numbers and street names.",
                        "List only 'City, State' (e.g. 'San Francisco, CA') or 'Remote - US'."
                    ],
                    example_improvement={
                        "before": "123 Elm Street, Apt 4B, Austin, TX 78701",
                        "after": "Austin, TX (Open to Remote)"
                    }
                )
            )

        # 9. Contact Info Omissions
        missing_contact = []
        if not resume.linkedin:
            missing_contact.append("LinkedIn Profile")
        if not resume.github:
            missing_contact.append("GitHub / Portfolio")
        if not resume.email:
            missing_contact.append("Email Address")
        if not resume.phone:
            missing_contact.append("Phone Number")

        if missing_contact:
            issues.append(
                IssueDetail(
                    issue_title=f"Missing Contact Links: {', '.join(missing_contact)}",
                    severity_level="Tip",
                    ats_impact="Low",
                    explanation="Providing direct links to LinkedIn and GitHub allows recruiters to verify your code and professional network in one click.",
                    where_it_appears="Header Section",
                    how_to_fix="Add clickable, cleanly formatted URLs or handles in your resume header.",
                    action_items=[
                        f"Add your {item} to the header." for item in missing_contact
                    ],
                    example_improvement={
                        "before": "John Doe | john@email.com",
                        "after": "John Doe | john@email.com | linkedin.com/in/johndoe | github.com/johndoe"
                    }
                )
            )

        # 10. Missing JD Keywords (when JD is provided)
        if jd_comp and jd_comp.missing_keywords:
            top_missing = jd_comp.missing_keywords[:6]
            issues.append(
                IssueDetail(
                    issue_title=f"Missing Target Job Description Keywords ({len(jd_comp.missing_keywords)} missing)",
                    severity_level="Critical" if len(top_missing) >= 4 else "Warning",
                    ats_impact="High",
                    explanation=f"The job description specifically looks for: {', '.join(top_missing)}. Your resume does not currently mention these keywords.",
                    where_it_appears="Skills & Experience Sections",
                    how_to_fix="Strategically weave these target keywords into your summary, skills list, and project descriptions where truthful.",
                    action_items=[
                        f"Add relevant missing skills: {', '.join(top_missing)}.",
                        "Align project descriptions with the terminology used in the job description."
                    ],
                    example_improvement={
                        "before": f"Resume lacks: {top_missing[0] if top_missing else 'Docker'}",
                        "after": f"Added: 'Containerized microservices using {top_missing[0] if top_missing else 'Docker'} and configured CI/CD pipelines.'"
                    }
                )
            )

        return issues

feedback_engine = FeedbackEngine()
