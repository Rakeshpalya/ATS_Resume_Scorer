import streamlit as st
from frontend.services.api_client import api_client
from frontend.components.dashboard import render_dashboard

def render_scorer_view():
    st.markdown('<div class="main-title">🎯 AI ATS Resume Scorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Upload your resume and optional job description for full diagnostic ATS feedback.</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 1. Upload Resume (PDF or DOCX)")
        resume_file = st.file_uploader(
            "Select your resume file (Max 5 MB)",
            type=["pdf", "docx"],
            help="PDF with text layer or DOCX format is recommended."
        )

    with col2:
        st.markdown("#### 2. Target Job Description (Optional)")
        jd_input_mode = st.radio("Input method:", ["Paste Text", "Upload .txt File"], horizontal=True)
        jd_text = ""
        jd_file_bytes = None
        jd_filename = None

        if jd_input_mode == "Paste Text":
            jd_text = st.text_area(
                "Paste Job Description text here:",
                height=180,
                placeholder="Paste the target job description to get keyword matching and skill gap analysis..."
            )
        else:
            jd_uploaded = st.file_uploader("Upload JD text file (.txt)", type=["txt"])
            if jd_uploaded:
                jd_file_bytes = jd_uploaded.read()
                jd_filename = jd_uploaded.name

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🔍 Analyze Resume with AI", type="primary", use_container_width=True)

    if analyze_btn:
        if not resume_file:
            st.warning("Please upload a resume file (.pdf or .docx) to proceed.")
            return

        with st.spinner("Analyzing resume formatting, keywords, metrics, and semantic alignment..."):
            try:
                resume_bytes = resume_file.read()
                token = st.session_state.get("auth_token")

                result = api_client.analyze_resume(
                    file_bytes=resume_bytes,
                    filename=resume_file.name,
                    jd_text=jd_text,
                    jd_bytes=jd_file_bytes,
                    jd_filename=jd_filename,
                    token=token
                )
                st.session_state["latest_analysis"] = result
                st.success("Analysis complete!")
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")

    # If results exist in session state, render dashboard
    if "latest_analysis" in st.session_state and st.session_state["latest_analysis"]:
        render_dashboard(st.session_state["latest_analysis"])
