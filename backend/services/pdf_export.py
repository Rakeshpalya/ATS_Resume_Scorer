import logging
from typing import Tuple
from backend.models.schemas import AnalysisResult
from backend.services.report_generator import report_generator

logger = logging.getLogger(__name__)

def generate_pdf_report(analysis: AnalysisResult) -> Tuple[bytes, str]:
    """
    Attempts to compile WeasyPrint PDF report.
    Returns (bytes, mime_type). If WeasyPrint or Cairo/Pango is unavailable,
    gracefully returns formatted plain text report.
    """
    html_content = report_generator.render_full_report_html(analysis)
    
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes, "application/pdf"
    except Exception as e:
        logger.warning(f"WeasyPrint PDF rendering unavailable or failed ({e}). Falling back to text report.")
        text_report = generate_text_summary(analysis)
        return text_report.encode("utf-8"), "text/plain"

def generate_text_summary(analysis: AnalysisResult) -> str:
    """Generates clean human-readable text analysis report."""
    lines = [
        "=" * 70,
        f"ATS RESUME SCORER - DIAGNOSTIC REPORT",
        "=" * 70,
        f"Candidate: {analysis.parsed_resume.name or 'Candidate'}",
        f"File:      {analysis.filename}",
        f"Generated: {analysis.created_at or 'N/A'}",
        "-" * 70,
        f"OVERALL ATS SCORE: {analysis.scores.overall_score} / 100",
        f"INTERPRETATION:    {analysis.scores.interpretation}",
        "-" * 70,
        "COMPONENT SCORE BREAKDOWN:",
        f" • Formatting & Hierarchy:  {analysis.scores.formatting_score} / {analysis.scores.formatting_max} pts",
        f" • Keywords & Terminology:  {analysis.scores.keywords_score} / {analysis.scores.keywords_max} pts",
        f" • Content & Metrics:       {analysis.scores.content_score} / {analysis.scores.content_max} pts",
        f" • Skill Validation:        {analysis.scores.skill_validation_score} / {analysis.scores.skill_validation_max} pts",
        f" • ATS Compatibility:       {analysis.scores.ats_compatibility_score} / {analysis.scores.ats_compatibility_max} pts",
        "-" * 70,
        "KEY STRENGTHS:"
    ]
    for s in analysis.strengths:
        lines.append(f" [+] {s}")

    if analysis.critical_issues:
        lines.append("-" * 70)
        lines.append("CRITICAL ISSUES:")
        for c in analysis.critical_issues:
            lines.append(f" [!] {c}")

    if analysis.jd_comparison:
        lines.append("-" * 70)
        lines.append("JOB DESCRIPTION MATCH:")
        lines.append(f" • Keyword Match:      {analysis.jd_comparison.match_percentage}%")
        lines.append(f" • Semantic Match:     {round(analysis.jd_comparison.semantic_similarity * 100)}%")
        lines.append(f" • Matched Keywords:   {', '.join(analysis.jd_comparison.matched_keywords[:10])}")
        lines.append(f" • Missing Keywords:   {', '.join(analysis.jd_comparison.missing_keywords[:10])}")

    lines.append("-" * 70)
    lines.append("PRIORITY ACTION ITEMS:")
    for idx, act in enumerate(analysis.action_items, 1):
        lines.append(f" {idx}. {act}")

    lines.append("-" * 70)
    lines.append("STRATEGIC RECOMMENDATIONS:")
    for idx, rec in enumerate(analysis.recommendations, 1):
        lines.append(f" {idx}. {rec}")

    lines.append("=" * 70)
    return "\n".join(lines)
