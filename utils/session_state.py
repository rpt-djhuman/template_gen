# utils/session_state.py
import streamlit as st


def initialize_session_state():
    """Initialize all session state variables"""
    if "template_spec" not in st.session_state:
        st.session_state.template_spec = None
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = ""
    if "show_template_editor" not in st.session_state:
        st.session_state.show_template_editor = False
    if "user_inputs" not in st.session_state:
        st.session_state.user_inputs = {}
    if "generated_output" not in st.session_state:
        st.session_state.generated_output = ""
    if "uploaded_filenames" not in st.session_state:
        st.session_state.uploaded_filenames = []
    if "kb_cleared" not in st.session_state:
        st.session_state.kb_cleared = False
    if "synthetic_inputs" not in st.session_state:
        st.session_state.synthetic_inputs = []
    if "synthetic_outputs" not in st.session_state:
        st.session_state.synthetic_outputs = []
    if "combined_data" not in st.session_state:
        st.session_state.combined_data = []
    if "show_json_columns" not in st.session_state:
        st.session_state.show_json_columns = False
    if "modified_prompt_template" not in st.session_state:
        st.session_state.modified_prompt_template = ""
    if "selected_samples" not in st.session_state:
        st.session_state.selected_samples = []
    if "suggested_variables" not in st.session_state:
        st.session_state.suggested_variables = []
    if "added_suggestions" not in st.session_state:
        st.session_state.added_suggestions = set()
    if "show_variable_editor" not in st.session_state:
        st.session_state.show_variable_editor = None
    if "show_output_editor" not in st.session_state:
        st.session_state.show_output_editor = None
    if "show_suggested_vars" not in st.session_state:
        st.session_state.show_suggested_vars = False
