import os
import streamlit as st

# Configure page
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

# Handle OAuth redirect callback (?code=...)
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    try:
        session_info = supabase_auth.exchange_code_for_session(auth_code)
        if session_info and session_info.get("access_token"):
            st.session_state["auth_token"] = session_info["access_token"]
            st.session_state["auth_user"] = session_info["user"]
            st.query_params.clear()
            st.toast("🎉 Successfully signed in with Google!", icon="✅")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"OAuth callback exchange error: {e}")

# Sidebar configuration
with st.sidebar:
    st.markdown('<div class="brand-title">🎯 ATS Scorer AI</div>', unsafe_allow_html=True)
    st.caption("AI-Powered Resume Diagnostic & Optimization")

    # API connection health
    is_api_healthy = api_client.check_health()
    if is_api_healthy:
        st.markdown('<span style="color:#16a34a; font-weight:600; font-size:0.85rem;">● API Connected (Port 8000)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#dc2626; font-weight:600; font-size:0.85rem;">○ API Offline (Start FastAPI)</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Navigation menu
    st.markdown("##### 🧭 Navigation")
    nav_options = ["🏠 Home", "🎯 ATS Scorer", "📊 History", "📚 Resources"]
    current_nav = st.session_state.get("active_nav", "🏠 Home")
    selected_nav = st.radio(
        "Navigation",
        nav_options,
        index=nav_options.index(current_nav) if current_nav in nav_options else 0,
        label_visibility="collapsed"
    )
    st.session_state["active_nav"] = selected_nav

    st.markdown("---")

    # Authentication section
    user = st.session_state.get("auth_user")
    token = st.session_state.get("auth_token")

    if user and token:
        user_email = getattr(user, "email", None) or "Authenticated User"
        st.markdown("##### 👤 Account Profile")
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; margin-bottom:10px;">
                <div style="font-size:0.8rem; color:#64748b;">Signed in as:</div>
                <div style="font-weight:600; font-size:0.9rem; color:#0f172a; word-break:break-all;">{user_email}</div>
                <div style="font-size:0.75rem; color:#16a34a; margin-top:4px;">● Connected to Supabase</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Sign Out", key="sign_out_btn", use_container_width=True):
            supabase_auth.sign_out()
            st.session_state["auth_user"] = None
            st.session_state["auth_token"] = None
            st.toast("Signed out successfully.")
            st.rerun()
    else:
        st.markdown("##### 🔐 Sign In to Save History")

        # Google Sign-in button with SVG icon
        try:
            google_url = supabase_auth.get_oauth_google_url()
            google_button_html = f"""
            <a href="{google_url}" target="_self" class="google-signin-btn">
                <svg width="18" height="18" viewBox="0 0 18 18">
                    <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.616z"/>
                    <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"/>
                    <path fill="#FBBC05" d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707s.102-1.167.282-1.707V4.961H.957C.347 6.175 0 7.55 0 9s.347 2.825.957 4.039l3.007-2.332z"/>
                    <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.961L3.964 7.293C4.672 5.166 6.656 3.58 9 3.58z"/>
                </svg>
                Continue with Google
            </a>
            """
            st.markdown(google_button_html, unsafe_allow_html=True)
        except Exception as e:
            st.caption("Google sign in is available when configured in Supabase.")

        st.markdown('<div class="auth-divider">or with email</div>', unsafe_allow_html=True)

        auth_tab1, auth_tab2 = st.tabs(["Sign In", "Create Account"])

        with auth_tab1:
            si_email = st.text_input("Email", key="si_email", placeholder="you@example.com")
            si_password = st.text_input("Password", type="password", key="si_pass", placeholder="••••••••")
            if st.button("Sign In with Email", key="si_btn", use_container_width=True, type="primary"):
                if not si_email or not si_password:
                    st.warning("Please enter your email and password.")
                else:
                    try:
                        res = supabase_auth.sign_in_with_password(si_email, si_password)
                        st.session_state["auth_token"] = res["access_token"]
                        st.session_state["auth_user"] = res["user"]
                        st.success("Signed in successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        with auth_tab2:
            su_email = st.text_input("Email", key="su_email", placeholder="you@example.com")
            su_password = st.text_input("Password (min 6 characters)", type="password", key="su_pass", placeholder="••••••••")
            if st.button("Create Account", key="su_btn", use_container_width=True, type="primary"):
                if not su_email or not su_password:
                    st.warning("Please fill in both email and password.")
                elif len(su_password) < 6:
                    st.warning("Password must be at least 6 characters long.")
                else:
                    try:
                        res = supabase_auth.sign_up_with_password(su_email, su_password)
                        if res.get("access_token"):
                            st.session_state["auth_token"] = res["access_token"]
                            st.session_state["auth_user"] = res["user"]
                            st.success("🎉 Account created and signed in!")
                            st.rerun()
                        else:
                            st.success("✅ Account created! Please check your email to confirm registration before signing in.")
                    except Exception as e:
                        st.error(str(e))

# Main view routing
if st.session_state.get("active_nav") == "🏠 Home":
    render_landing_view()
elif st.session_state.get("active_nav") == "🎯 ATS Scorer":
    render_scorer_view()
elif st.session_state.get("active_nav") == "📊 History":
    render_history_view()
elif st.session_state.get("active_nav") == "📚 Resources":
    render_resources_view()
