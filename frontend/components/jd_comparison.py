import streamlit as st
from typing import Dict, Any, Optional

def render_jd_comparison(jd_data: Optional[Dict[str, Any]]):
    st.markdown("##### 🎯 Target Job Description Alignment")

    if not jd_data or not (jd_data.get("matched_keywords") or jd_data.get("missing_keywords")):
        st.info("No Job Description was provided for this analysis. Add a target JD to see keyword match rate and skills gap analysis.")
        return

    match_pct = jd_data.get("match_percentage", 0.0)
    sem_sim = jd_data.get("semantic_similarity", 0.0)
    matched = jd_data.get("matched_keywords", [])
    missing = jd_data.get("missing_keywords", [])
    gaps = jd_data.get("skill_gaps", [])

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="JD Keyword Match Rate", value=f"{match_pct:.0f}%")
    with col2:
        st.metric(label="Semantic Relevance", value=f"{sem_sim * 100:.0f}%")

    # Matched keywords
    st.markdown(f"**Matched Role Keywords ({len(matched)})**")
    if matched:
        pills_html = "".join([f'<span class="badge-pill badge-matched">{kw}</span>' for kw in matched])
        st.markdown(f"<div>{pills_html}</div>", unsafe_allow_html=True)
    else:
        st.write("None matched yet.")

    # Missing keywords
    st.markdown(f"**Missing Target Keywords ({len(missing)})**")
    if missing:
        pills_html = "".join([f'<span class="badge-pill badge-missing">{kw}</span>' for kw in missing])
        st.markdown(f"<div>{pills_html}</div>", unsafe_allow_html=True)
    else:
        st.success("All target JD keywords are present in your resume!")

    # Role specific gaps
    if gaps:
        st.markdown(f"**⚠️ Required Skills Gap ({len(gaps)})**")
        st.caption("These skills were explicitly required by the job posting:")
        for g in gaps:
            st.warning(f"• **{g}**")
