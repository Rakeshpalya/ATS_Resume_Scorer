import streamlit as st
from typing import List, Dict, Any

def render_skill_validation(skill_validation_items: List[Dict[str, Any]]):
    st.markdown("##### 🔍 Skill Context & Cross-Validation Matrix")
    st.caption("Verifies whether each listed technical skill is backed up with contextual proof in your experience or projects.")

    if not skill_validation_items:
        st.info("No skills listed in the resume.")
        return

    validated = [item for item in skill_validation_items if item.get("validated")]
    unvalidated = [item for item in skill_validation_items if not item.get("validated")]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**✅ Validated Skills ({len(validated)})**")
        for item in validated:
            snippet = item.get("evidence_snippet", "")
            st.markdown(
                f"""
                <div style="margin-bottom: 6px; padding: 6px 10px; background: #f0fdf4; border-radius: 6px; border: 1px solid #bbf7d0;">
                    <strong style="color: #166534;">{item.get('skill')}</strong>
                    <div style="font-size: 0.8rem; color: #15803d;">{snippet}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col2:
        st.markdown(f"**⚠️ Unvalidated Skills ({len(unvalidated)})**")
        if unvalidated:
            for item in unvalidated:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 6px; padding: 6px 10px; background: #fefce8; border-radius: 6px; border: 1px solid #fef08a;">
                        <strong style="color: #854d0e;">{item.get('skill')}</strong>
                        <div style="font-size: 0.8rem; color: #a16207;">Not mentioned in any job role or project description.</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.success("All listed skills are supported with context!")
