import streamlit as st
from typing import List, Dict, Any

def render_detailed_feedback(issues: List[Dict[str, Any]]):
    st.markdown("##### 🛠️ Detailed Diagnostic Feedback")
    st.caption("Specific issues identified by ATS parsing rules with actionable instructions and before/after improvements.")

    if not issues:
        st.success("No issues detected! Your resume is in top shape.")
        return

    for idx, issue in enumerate(issues, 1):
        title = issue.get("issue_title", "Issue")
        severity = issue.get("severity_level", "Tip")
        impact = issue.get("ats_impact", "Low")
        explanation = issue.get("explanation", "")
        where = issue.get("where_it_appears", "Resume")
        how = issue.get("how_to_fix", "")
        action_items = issue.get("action_items", [])
        example = issue.get("example_improvement")

        badge_icon = "🔴" if severity == "Critical" else ("🟡" if severity == "Warning" else "🔵")

        with st.expander(f"{badge_icon} #{idx}. {title} ({severity} | {impact} Impact)", expanded=(severity == "Critical")):
            st.markdown(f"**Where it appears**: `{where}`")
            st.markdown(f"**Explanation**: {explanation}")
            st.markdown(f"**How to fix**: {how}")

            if action_items:
                st.markdown("**Action Checklist:**")
                for act in action_items:
                    st.markdown(f"- [ ] {act}")

            if example and isinstance(example, dict):
                st.markdown(
                    f"""
                    <div class="example-box">
                        <div class="diff-before">❌ <strong>Before:</strong> {example.get('before', '')}</div>
                        <div class="diff-after">✅ <strong>After:</strong> {example.get('after', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
