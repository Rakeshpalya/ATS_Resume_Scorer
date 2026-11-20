import streamlit as st

def render_landing_view():
    # Hero Section
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-badge">✨ AI-Powered Career Intelligence</div>
            <div class="hero-heading">Beat the ATS. Land More Tech Interviews.</div>
            <div class="hero-subtitle">
                Evaluate your resume against enterprise Applicant Tracking Systems. Get instant diagnostic feedback on formatting, keyword density, quantified metrics, and semantic job description alignment.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Primary Action Row
    col_cta1, col_cta2, col_cta3 = st.columns([1, 2, 1])
    with col_cta2:
        if st.button("🚀 Start Free Resume Analysis Now", type="primary", use_container_width=True, key="hero_cta_btn"):
            st.session_state["active_nav"] = "🎯 ATS Scorer"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Feature Grid
    st.markdown("### ⚡ Why Modern ATS Systems Reject Resumes")
    st.caption("Over 75% of applications are filtered before a human recruiter sees them. Here is how our dual AI engine solves this:")

    fcol1, fcol2, fcol3 = st.columns(3)

    with fcol1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">Groq LLM Extraction</div>
                <div class="feature-desc">
                    Sub-second structured resume parsing powered by Llama-3 / GPT-OSS extracts clean JSON data, contact links, and experience bullets with zero hallucination.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with fcol2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">🧠</div>
                <div class="feature-title">Semantic Context Match</div>
                <div class="feature-desc">
                    Uses Sentence Transformers (<code>all-MiniLM-L6-v2</code>) and spaCy to verify that listed technical skills are backed up by concrete project evidence.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with fcol3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">🔒</div>
                <div class="feature-title">Supabase Cloud History</div>
                <div class="feature-desc">
                    Sign in with Google or Email to securely store analysis history in PostgreSQL protected by Row Level Security (RLS) policies.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # 5-Dimension Weighted Scoring Overview
    st.markdown("### 📊 The 5 Core ATS Scoring Dimensions")
    st.write("Our engine scores your resume across 5 weighted dimensions calibrated against enterprise ATS algorithms:")

    dcol1, dcol2 = st.columns(2)

    with dcol1:
        st.markdown(
            """
            - **1. Formatting & Hierarchy (20 pts)**: Detects standard section headers (`Experience`, `Education`, `Skills`, `Projects`), bullet density (15+ optimal), and multi-section completeness.
            - **2. Keywords & Terminology (25 pts)**: Measures keyword volume, hard skill density, and target Job Description match percentage via RapidFuzz and synonym normalization.
            - **3. Content & Impact (25 pts)**: Scans for power action verbs starting bullet points, measurable metrics (`\d+%`, `\$\d+`, scale), and grammar cleanliness.
            """
        )

    with dcol2:
        st.markdown(
            """
            - **4. Skill Cross-Validation (15 pts)**: Cross-references your skills list against project descriptions and work history to flag unevidenced skill-dumping.
            - **5. ATS Compatibility (15 pts)**: Identifies privacy risks (full street addresses / 5-digit zip codes) and decorative symbols (`│`, `║`, tables) that break parsers.
            """
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Bottom Banner CTA
    st.markdown(
        """
        <div style="background: #f1f5f9; border-radius: 12px; padding: 2rem; text-align: center; border: 1px solid #e2e8f0;">
            <h3 style="margin: 0 0 8px 0; color: #0f172a;">Ready to test and optimize your resume?</h3>
            <p style="color: #64748b; margin-bottom: 1.2rem;">Upload your PDF or DOCX file to receive your detailed diagnostic report in seconds.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("🔍 Scan Your Resume Now", use_container_width=True, key="bottom_cta_btn"):
        st.session_state["active_nav"] = "🎯 ATS Scorer"
        st.rerun()
