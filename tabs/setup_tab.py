# tabs/setup_tab.py
import streamlit as st
import json
from utils.llm_utils import generate_template_from_instructions
from utils.document_utils import parse_documents
from utils.template_utils import (
    create_example_templates,
    create_example_outputs,
    parse_template_file,
)


def render_setup_tab():
    st.header("Project Setup")

    # Add option to either upload a template or create a new one
    setup_option = st.radio(
        "Choose how to start your project",
        options=[
            "Create new template from documents",
            "Upload existing template",
            "Create an empty template",
        ],
        index=0,
    )

    if (
        setup_option == "Create new template from documents"
        or setup_option == "Create an empty template"
    ):
        render_examples_section()

    if setup_option == "Upload existing template":
        render_upload_template_section()
    elif setup_option == "Create new template from documents":
        render_document_based_template_section()
    elif setup_option == "Create an empty template":
        render_empty_template_section()


# Helper functions for each section
def render_examples_section():
    # Add Examples section
    st.markdown("---")
    st.subheader("Or try one of our examples")

    # Get example templates
    example_templates = create_example_templates()

    # Create columns for example cards
    cols = st.columns(len(example_templates))

    # Display each example in a card
    for i, (col, template) in enumerate(zip(cols, example_templates)):
        with col:
            # ... rest of code remains same
            pass


def render_upload_template_section():
    st.subheader("Upload Template File")
    # ... rest of code remains same


def render_document_based_template_section():
    # Step 1: Upload Knowledge Base
    st.subheader("Step 1: Upload Knowledge Base")
    # ... rest of code remains same


def render_empty_template_section():
    st.subheader("Create Empty Template")
    # ... rest of code remains same
