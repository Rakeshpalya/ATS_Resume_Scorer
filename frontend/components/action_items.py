import streamlit as st
from typing import List

def render_action_items(action_items: List[str]):
    st.markdown("##### ✅ Prioritized Optimization Checklist")
    st.caption("Immediate steps you should take to boost your ATS match and interview callback rate:")

    if not action_items:
        st.info("No urgent action items. Great job!")
        return

    for idx, item in enumerate(action_items, 1):
        st.checkbox(f"**{idx}.** {item}", key=f"action_item_{idx}")
