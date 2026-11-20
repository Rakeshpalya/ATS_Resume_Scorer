import os
import streamlit as st

# Page setup
st.set_page_config(
    page_title="AI ATS Resume Scorer & Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
css_file = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
if os.path.exists(css_file):
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from frontend.services.supabase_client import supabase_auth
from frontend.services.api_client import api_client
from frontend.views.landing import render_landing_view
from frontend.views.scorer import render_scorer_view
from frontend.views.history import render_history_view
from frontend.views.resources import render_resources_view

# Handle OAuth redirect code (?code=...)
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    try:
        session_info = supabase_auth.exchange_code_for_session(auth_code)
        if session_info and session_info.get("access_token"):
            st.session_state["auth_token"] = session_info["access_token"]
            st.session_state["auth_user"] = session_info["user"]
            st.query_params.clear()
            st.success("Successfully signed in with Google!")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"OAuth exchange failed: {e}")

# Sidebar
with st.sidebar:
    st.markdown("### 🎯 ATS Scorer AI")
    st.caption("AI-powered Resume Diagnostic System")

    # API Health Check
    is_api_healthy = api_client.check_health()
    if is_api_healthy:
        st.markdown('<span style="color:#16a34a; font-weight:600;">● API Connected (Port 8000)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#dc2626; font-weight:600;">○ API Offline (Start FastAPI)</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Auth State
    user = st.session_state.get("auth_user")
    token = st.session_state.get("auth_token")

    if user and token:
        user_email = getattr(user, "email", None) or "Authenticated User"
        st.markdown("##### 👤 Account")
        st.markdown(f"**Logged in as:**\n`{user_email}`")
        if st.button("Sign Out", key="sign_out_btn", use_container_width=True):
            supabase_auth.sign_out()
            st.session_state["auth_user"] = None
            st.session_state["auth_token"] = None
            st.success("Signed out successfully.")
            st.rerun()
    else:
        st.markdown("##### 🔐 Sign In to Save History")
        auth_tab1, auth_tab2 = st.tabs(["Sign In", "Create Account"])

        with auth_tab1:
            si_email = st.text_input("Email", key="si_email")
            si_password = st.text_input("Password", type="password", key="si_pass")
            if st.button("Sign In", key="si_btn", use_container_width=True):
                try:
                    res = supabase_auth.sign_in_with_password(si_email, si_password)
                    st.session_state["auth_token"] = res["access_token"]
                    st.session_state["auth_user"] = res["user"]
                    st.success("Signed in!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        with auth_tab2:
            su_email = st.text_input("Email", key="su_email")
            su_password = st.text_input("Password (min 6 chars)", type="password", key="su_pass")
            if st.button("Create Account", key="su_btn", use_container_width=True):
                try:
                    res = supabase_auth.sign_up_with_password(su_email, su_password)
                    if res.get("access_token"):
                        st.session_state["auth_token"] = res["access_token"]
                        st.session_state["auth_user"] = res["user"]
                        st.success("Account created and signed in!")
                    else:
                        st.info("Account created! Please check your email to confirm registration.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        if supabase_auth.is_configured():
            st.markdown("<div style='text-align: center; margin: 8px 0; color: #64748b;'>or</div>", unsafe_allow_html=True)
            try:
                google_url = supabase_auth.get_oauth_google_url()
                st.link_button("🌐 Sign in with Google", url=google_url, use_container_width=True)
            except Exception:
                pass

    st.markdown("---")
    st.markdown("##### 🧭 Navigation")
    nav_options = ["🏠 Home", "🎯 ATS Scorer", "📊 History", "📚 Resources"]
    
    current_nav = st.session_state.get("active_nav", "🏠 Home")
    selected_nav = st.radio(
        "Go to:",
        nav_options,
        index=nav_options.index(current_nav) if current_nav in nav_options else 0,
        label_visibility="collapsed"
    )
    st.session_state["active_nav"] = selected_nav

# Main view routing
if st.session_state.get("active_nav") == "🏠 Home":
    render_landing_view()
elif st.session_state.get("active_nav") == "🎯 ATS Scorer":
    render_scorer_view()
elif st.session_state.get("active_nav") == "📊 History":
    render_history_view()
elif st.session_state.get("active_nav") == "📚 Resources":
    render_resources_view()
