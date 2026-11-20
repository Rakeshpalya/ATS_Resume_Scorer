import streamlit as st
from typing import List

def render_strengths_and_issues(strengths: List[str], critical_issues: List[str]):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 🌟 Key Strengths")
        if strengths:
            for s in strengths:
                st.success(f"**✔** {s}")
        else:
            st.info("No standout strengths detected yet.")

    with col2:
        st.markdown("##### ⚠️ Critical Issues")
        if critical_issues:
            for issue in critical_issues:
                st.error(f"**✖** {issue}")
        else:
            st.success("🎉 No critical blocking issues detected! Your resume follows ATS guidelines.")
