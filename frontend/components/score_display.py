import streamlit as st
from typing import Dict, Any
from frontend.components._helpers import get_score_color_class

def render_score_display(scores: Dict[str, Any]):
    overall = scores.get("overall_score", 0.0)
    interpretation = scores.get("interpretation", "Pending")
    color_class = get_score_color_class(overall)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div style="font-size: 0.9rem; font-weight: 600; color: #64748b; text-transform: uppercase;">
                    Overall ATS Score
                </div>
                <div class="score-display {color_class}">
                    {overall:.0f}<span style="font-size: 1.5rem; color: #94a3b8;">/100</span>
                </div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #1e293b;">
                    {interpretation}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown("##### 📊 Dimension Breakdown")

        # 1. Formatting
        f_val = scores.get("formatting_score", 0.0)
        f_max = scores.get("formatting_max", 20.0)
        st.write(f"**Formatting & Layout**: {f_val} / {f_max} pts")
        st.progress(min(1.0, f_val / f_max))

        # 2. Keywords
        k_val = scores.get("keywords_score", 0.0)
        k_max = scores.get("keywords_max", 25.0)
        st.write(f"**Keywords & Terminology**: {k_val} / {k_max} pts")
        st.progress(min(1.0, k_val / k_max))

        # 3. Content & Metrics
        c_val = scores.get("content_score", 0.0)
        c_max = scores.get("content_max", 25.0)
        st.write(f"**Content & Quantifiable Metrics**: {c_val} / {c_max} pts")
        st.progress(min(1.0, c_val / c_max))

        # 4. Skill Validation
        v_val = scores.get("skill_validation_score", 0.0)
        v_max = scores.get("skill_validation_max", 15.0)
        st.write(f"**Skill Cross-Validation**: {v_val} / {v_max} pts")
        st.progress(min(1.0, v_val / v_max))

        # 5. ATS Technical Compatibility
        a_val = scores.get("ats_compatibility_score", 0.0)
        a_max = scores.get("ats_compatibility_max", 15.0)
        st.write(f"**ATS Parser Compatibility**: {a_val} / {a_max} pts")
        st.progress(min(1.0, a_val / a_max))
