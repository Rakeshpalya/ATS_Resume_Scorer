import streamlit as st
from frontend.services.api_client import api_client
from frontend.components.dashboard import render_dashboard

def render_history_view():
    st.markdown('<div class="main-title">📊 Analysis History</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Review past resume scans, score trends, and download reports.</div>', unsafe_allow_html=True)

    token = st.session_state.get("auth_token")
    user = st.session_state.get("auth_user")

    if not user or not token:
        st.info("🔒 Please sign in using the sidebar to view your saved resume analyses.")
        return

    try:
        with st.spinner("Loading your analysis history..."):
            history = api_client.get_history(token)
    except Exception as e:
        st.error(f"Could not load history: {e}")
        return

    if not history:
        st.info("You haven't run any saved resume analyses yet. Head over to the ATS Scorer to get started!")
        return

    st.markdown(f"**Found {len(history)} saved resume scans:**")

    for item in history:
        analysis_id = item.get("id")
        filename = item.get("filename", "Resume")
        score = item.get("ats_score", 0.0)
        date = item.get("created_at", "")[:10]
        match_rate = item.get("keyword_match", 0.0)
        missing_kw = item.get("missing_keywords", [])

        with st.expander(f"📄 {filename} — Score: {score:.0f}/100 ({date})"):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**Overall ATS Score**: {score:.0f}/100")
                if match_rate > 0:
                    st.write(f"**JD Match Rate**: {match_rate:.0f}%")
                if missing_kw:
                    st.caption(f"Missing Keywords: {', '.join(missing_kw[:6])}")

            with col2:
                if st.button("🔍 View Analysis", key=f"view_{analysis_id}", use_container_width=True):
                    with st.spinner("Fetching report details..."):
                        try:
                            full_res = api_client.get_analysis(analysis_id, token)
                            st.session_state["viewing_analysis"] = full_res
                        except Exception as e:
                            st.error(f"Error: {e}")

            with col3:
                if st.button("🗑️ Delete", key=f"del_{analysis_id}", use_container_width=True):
                    try:
                        api_client.delete_analysis(analysis_id, token)
                        st.success("Deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")

    # Display active analysis if selected
    if "viewing_analysis" in st.session_state and st.session_state["viewing_analysis"]:
        st.markdown("---")
        render_dashboard(st.session_state["viewing_analysis"])
