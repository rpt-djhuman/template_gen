# tabs/template_editor_tab.py
import streamlit as st
import json
from utils.llm_utils import generate_improved_prompt_template, call_llm
from utils.template_utils import suggest_variable_values_from_kb, analyze_knowledge_base


def render_template_editor_tab():
    if st.session_state.show_template_editor and st.session_state.template_spec:
        st.header("Template Editor")
        st.subheader(st.session_state.template_spec["name"])

        # Initialize session state variables for this tab
        initialize_template_editor_state()

        # Create main layout with left (settings) and right (generation) columns
        left_col, right_col = st.columns([3, 2])

        # LEFT COLUMN - Settings
        with left_col:
            render_template_settings(st.session_state.template_spec)

        # RIGHT COLUMN - Generation
        with right_col:
            render_generation_section(st.session_state.template_spec)
    else:
        st.info(
            "No template has been generated yet. Go to the 'Setup' tab to create one."
        )


def initialize_template_editor_state():
    # Initialize session state variables
    if "suggested_variables" not in st.session_state:
        st.session_state.suggested_variables = []
    # ... rest of initializations


def render_template_settings(template_spec):
    # Basic template information
    with st.expander("Template Information (Metadata)", expanded=False):
        # ... rest of code remains same
        pass

    # Prompt Template Section
    with st.expander("Prompt Template", expanded=True):
        # ... rest of code remains same
        pass

    # Knowledge Base Management Section
    with st.expander("Knowledge Base Management", expanded=False):
        # ... rest of code remains same
        pass

    # Input Variables Section
    with st.expander("Input Variables", expanded=True):
        # ... rest of code remains same
        pass

    # Output Variables Section
    with st.expander("Output Variables", expanded=True):
        # ... rest of code remains same
        pass

    # Template JSON
    with st.expander("Template JSON", expanded=False):
        # ... rest of code remains same
        pass


def render_generation_section(template_spec):
    st.header("Generation")
    # ... rest of code remains same
