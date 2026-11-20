import streamlit as st

def render_landing_view():
    st.markdown('<div class="main-title">🎯 Beat the ATS. Land More Tech Interviews.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">AI-powered diagnostic ATS scoring, semantic job description matching, and actionable resume optimization.</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(
            """
            ### Why Most Resumes Get Rejected
            Over 75% of resumes are filtered out by Applicant Tracking Systems before a human recruiter ever sees them. Common pitfalls include:
            - **Unreadable formatting**: Complex columns, tables, or decorative borders that scramble ATS text parsers.
            - **Keyword mismatch**: Failing to match the terminology and hard skills specified in the job description.
            - **Unquantified experience**: Missing measurable achievements and impact numbers ($ revenue, % growth, scale).
            - **Unvalidated skill dumping**: Listing 30 skills in a block without any contextual evidence in project descriptions.

            ### What Our AI Analyzer Checks
            Our engine evaluates your resume across **5 core weighted dimensions**:
            1. **Formatting & Hierarchy (20 pts)**: Detects standard section headers, bullet structure, and parsing readiness.
            2. **Keywords & Terminology (25 pts)**: Measures keyword volume, hard skill density, and job description alignment.
            3. **Content & Impact (25 pts)**: Scans for action power verbs, quantifiable metrics, and grammar clarity.
            4. **Skill Cross-Validation (15 pts)**: Uses Sentence Transformers to verify listed skills appear in project evidence.
            5. **ATS Compatibility (15 pts)**: Screens for privacy risks (full street addresses/zip codes) and unparseable symbols.
            """
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Analyze Your Resume Now", type="primary", use_container_width=False):
            st.session_state["active_nav"] = "🎯 ATS Scorer"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div class="stat-card" style="margin-bottom: 1rem; text-align: left;">
                <h4 style="margin: 0; color: #2563eb;">⚡ Groq Llama-3 / GPT-OSS</h4>
                <p style="font-size: 0.9rem; color: #64748b; margin-top: 4px;">
                    Ultra-fast structured resume parsing extracts clean JSON representation in seconds.
                </p>
            </div>
            <div class="stat-card" style="margin-bottom: 1rem; text-align: left;">
                <h4 style="margin: 0; color: #16a34a;">🧠 Sentence Transformers</h4>
                <p style="font-size: 0.9rem; color: #64748b; margin-top: 4px;">
                    Local embeddings (`all-MiniLM-L6-v2`) provide deep semantic matching between your resume and job postings.
                </p>
            </div>
            <div class="stat-card" style="margin-bottom: 1rem; text-align: left;">
                <h4 style="margin: 0; color: #d97706;">🔒 Secure Supabase History</h4>
                <p style="font-size: 0.9rem; color: #64748b; margin-top: 4px;">
                    Save analysis history with Row Level Security (RLS) and re-download PDF diagnostic reports anytime.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
