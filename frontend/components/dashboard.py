import streamlit as st
from typing import Dict, Any

from frontend.components.score_display import render_score_display
from frontend.components.strengths_issues import render_strengths_and_issues
from frontend.components.jd_comparison import render_jd_comparison
from frontend.components.skill_validation import render_skill_validation
from frontend.components.detailed_feedback import render_detailed_feedback
from frontend.components.action_items import render_action_items
from frontend.components.recommendations import render_recommendations
from frontend.services.api_client import api_client

def render_dashboard(analysis: Dict[str, Any]):
    st.markdown("---")
    filename = analysis.get("filename", "Resume")
    created = analysis.get("created_at", "")[:10]
    st.subheader(f"📄 Analysis Results for: `{filename}`")
    if created:
        st.caption(f"Analysis generated on: {created}")

    # Top overall score display
    scores = analysis.get("scores", {})
    render_score_display(scores)

    st.markdown("---")

    # Strengths and Critical Issues
    strengths = analysis.get("strengths", [])
    critical = analysis.get("critical_issues", [])
    render_strengths_and_issues(strengths, critical)

    st.markdown("---")

    # JD Comparison (if present)
    jd_comp = analysis.get("jd_comparison")
    render_jd_comparison(jd_comp)

    st.markdown("---")

    # Skill cross-validation
    skill_val = analysis.get("skill_validation", [])
    render_skill_validation(skill_val)

    st.markdown("---")

    # Detailed feedback
    issues = analysis.get("detailed_issues", [])
    render_detailed_feedback(issues)

    st.markdown("---")

    # Action items & recommendations
    col1, col2 = st.columns(2)
    with col1:
        actions = analysis.get("action_items", [])
        render_action_items(actions)
    with col2:
        recs = analysis.get("recommendations", [])
        render_recommendations(recs)

    st.markdown("---")
    st.markdown("##### 📥 Export Diagnostic Report")

    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        if st.button("Generate & Download PDF Report", key="download_pdf_btn", use_container_width=True):
            with st.spinner("Compiling PDF report..."):
                try:
                    file_bytes, mime = api_client.export_pdf(analysis)
                    ext = "pdf" if mime == "application/pdf" else "txt"
                    st.download_button(
                        label=f"⬇️ Click to Download ({ext.upper()})",
                        data=file_bytes,
                        file_name=f"ATS_Report_{analysis.get('id', 'resume')}.{ext}",
                        mime=mime,
                        key="actual_dl_btn"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF report: {e}")

    with exp_col2:
        # Build quick text summary
        text_lines = [
            f"ATS RESUME REPORT: {filename}",
            f"Overall ATS Score: {scores.get('overall_score')}/100",
            f"Interpretation: {scores.get('interpretation')}",
            "\nKey Strengths:",
            *[f"- {s}" for s in strengths],
            "\nAction Items:",
            *[f"- {a}" for a in analysis.get('action_items', [])],
            "\nRecommendations:",
            *[f"- {r}" for r in analysis.get('recommendations', [])]
        ]
        text_summary = "\n".join(text_lines)
        st.download_button(
            label="⬇️ Download Text Summary (.txt)",
            data=text_summary,
            file_name=f"ATS_Summary_{analysis.get('id', 'resume')}.txt",
            mime="text/plain",
            use_container_width=True,
            key="download_txt_btn"
        )
