# app.py
import streamlit as st
from tabs.setup_tab import render_setup_tab
from tabs.template_editor_tab import render_template_editor_tab
from tabs.data_generation_tab import render_data_generation_tab
from utils.session_state import initialize_session_state

# Setup page config
st.set_page_config(
    page_title="Template Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_sidebar():
    with st.sidebar:
        st.title("Template Generator")
        st.write("Create templates for generating content with LLMs.")

        # API Key inputs
        st.subheader("API Keys")
        api_key = st.text_input("OpenAI API Key", type="password")
        if api_key:
            st.session_state.api_key = api_key

        anthropic_api_key = st.text_input("Anthropic API Key", type="password")
        if anthropic_api_key:
            st.session_state.anthropic_api_key = anthropic_api_key

        # Model selection
        st.subheader("Model Selection")
        model_provider = st.radio(
            "Select Model Provider",
            options=["OpenAI", "Anthropic"],
            index=0,
        )

        if model_provider == "OpenAI":
            st.session_state.model = st.selectbox(
                "Select OpenAI Model",
                options=[
                    "gpt-4o-mini",
                    "gpt-3.5-turbo",
                    "gpt-4",
                    "gpt-4o",
                    "gpt-4-turbo",
                ],
                index=0,
            )
        else:  # Anthropic
            st.session_state.model = st.selectbox(
                "Select Claude Model",
                options=[
                    "claude-3-7-sonnet-latest",
                    "claude-3-5-haiku-latest",
                    "claude-3-5-sonnet-latest",
                    "claude-3-opus-latest",
                ],
                index=1,  # Default to Sonnet as a good balance of capability and cost
            )


def main():
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    render_sidebar()

    # Main application layout
    st.title("Template Generator")

    # Create tabs for workflow
    tab1, tab2, tab3 = st.tabs(["Setup", "Edit and Use Template", "Generate Data"])

    with tab1:
        render_setup_tab()

    with tab2:
        render_template_editor_tab()

    with tab3:
        render_data_generation_tab()


if __name__ == "__main__":
    main()
