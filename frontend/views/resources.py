import streamlit as st

def render_resources_view():
    st.markdown('<div class="main-title">📚 ATS Resources & Cheat Sheets</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Best practices, power verb directories, and bullet point formulas to maximize interview callbacks.</div>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3 = st.tabs(["🚀 Google XYZ Formula", "⚡ Action Power Verbs", "📋 ATS Dos and Don'ts"])

    with tab1:
        st.markdown(
            """
            ### The Google 'XYZ' Formula
            Former Google SVP of People Operations Laszlo Bock recommends phrasing every bullet point as:
            > **"Accomplished [X] as measured by [Y], by doing [Z]"**

            #### High-Impact Examples:
            - **Weak**: "Worked on improving our backend microservices."
            - **Strong (XYZ)**: "Reduced API response latency by **42% (Y)** across **15 core microservices (X)** by implementing asynchronous FastAPI endpoints with Redis caching **(Z)**."
            
            - **Weak**: "Led a team of engineers to build a new feature."
            - **Strong (XYZ)**: "Spearheaded a **5-engineer team (Z)** to launch the real-time billing portal **(X)**, increasing monthly recurring revenue by **\$240,000 (Y)** within 90 days."
            """
        )

    with tab2:
        st.markdown("### High-Impact Power Action Verbs by Category")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
                **Technical & Architecture**
                - Architected
                - Engineered
                - Containerized
                - Deployed
                - Refactored
                - Automated
                - Scaled
                - Integrated
                """
            )
        with col2:
            st.markdown(
                """
                **Optimization & Growth**
                - Accelerated
                - Streamlined
                - Optimized
                - Maximize
                - Reduced
                - Boosted
                - Doubled
                - Consolidated
                """
            )
        with col3:
            st.markdown(
                """
                **Leadership & Delivery**
                - Spearheaded
                - Orchestrated
                - Championed
                - Mentored
                - Executed
                - Delivered
                - Formulated
                - Navigated
                """
            )

    with tab3:
        st.markdown(
            """
            ### ATS Formatting Checklist

            | What to DO (ATS-Friendly) | What to AVOID (Breaks Parsers) |
            | :--- | :--- |
            | Use standard headings (`Experience`, `Education`, `Skills`, `Projects`) | Inventing creative headings (`Where I've Been`, `Knowledge Tree`) |
            | Single-column, clean linear layout | Two-column tables, sidebars, multi-box grids |
            | Standard bullet points (`•`, `-`) | Decorative icons, stars, arrows, rating bars (`Skill: ★★★★☆`) |
            | Include city and state (`Austin, TX`) | Full street address and postal zip code (triggers geo filtering) |
            | Standard system fonts (Calibri, Arial, Helvetica, Times) | Custom downloaded fonts or graphics saved as images |
            | Upload `.pdf` or `.docx` format | Uploading `.png`, `.jpg`, `.pages`, or flattened scanned PDFs |
            """
        )
