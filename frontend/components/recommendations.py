import streamlit as st
from typing import List

def render_recommendations(recommendations: List[str]):
    st.markdown("##### 💡 Strategic Recommendations")
    st.caption("Long-term resume optimization advice based on top ATS hiring trends:")

    if not recommendations:
        st.info("No specific recommendations at this time.")
        return

    for idx, rec in enumerate(recommendations, 1):
        st.info(f"**Recommendation #{idx}**: {rec}")
