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
            st.markdown(f"#### {template['name']}")
            st.markdown(f"*{template['description']}*")

            # Show input variables
            with st.expander("Inputs and Outputs", expanded=False):
                st.markdown("**Inputs:**")
                for inp in template["input"]:
                    st.markdown(f"- {inp['name']}: {inp['type']}")

                # Show output variables
                st.markdown("**Outputs:**")
                for out in template["output"]:
                    st.markdown(f"- {out['name']}: {out['type']}")

            # Button to use this example
            if st.button(f"Use this example", key=f"use_example_{i}"):
                st.session_state.template_spec = template
                st.session_state.show_template_editor = True

                # Create some example outputs to show
                example_outputs = create_example_outputs(template)

                # Store example outputs in session state
                st.session_state.example_outputs = example_outputs

                # Success message
                st.success(
                    f"Example template loaded! Go to the 'Edit Template' tab to see it in action."
                )


def render_upload_template_section():
    st.subheader("Upload Template File")
    uploaded_template = st.file_uploader(
        "Upload a template JSON file",
        type=["json"],
        help="Upload a previously created template file (.json)",
    )

    if uploaded_template:
        template_spec, error = parse_template_file(uploaded_template)
        if error:
            st.error(error)
        else:
            st.success(f"Successfully loaded template: {template_spec['name']}")

            # Show template preview
            with st.expander("Template Preview", expanded=False):
                st.json(template_spec)

            # Button to use this template
            if st.button("Use This Template"):
                st.session_state.template_spec = template_spec
                st.session_state.show_template_editor = True
                st.success(
                    "Template loaded! Go to the 'Edit Template' tab to customize it."
                )


def render_document_based_template_section():
    # Step 1: Upload Knowledge Base
    st.subheader("Step 1: Upload Knowledge Base")
    uploaded_files = st.file_uploader(
        "Upload documents to use as knowledge base",
        accept_multiple_files=True,
        type=["pdf", "txt", "html"],
    )

    # Rest of your existing code for document processing...
    if uploaded_files and not st.session_state.kb_cleared:
        # Track filenames for UI feedback
        st.session_state.uploaded_filenames = [file.name for file in uploaded_files]

        with st.spinner("Processing documents..."):
            st.session_state.knowledge_base = parse_documents(uploaded_files)
        st.success(f"Processed {len(uploaded_files)} documents")

        with st.expander("Preview extracted content"):
            st.text_area(
                "Extracted Text",
                value=st.session_state.knowledge_base,
                height=200,
                disabled=True,
            )

    # Step 2: Provide Instructions
    st.subheader("Step 2: Provide Instructions")
    instructions = st.text_area(
        "Describe what you want to create",
        placeholder="Describe what you want to create (e.g., 'Create a character background generator with name, faction, and race as inputs...')",
        height=150,
    )

    # Generate Template button
    if st.button("Generate Template"):
        if not st.session_state.get("api_key") and not st.session_state.get(
            "anthropic_api_key"
        ):
            st.error(
                "Please provide an OpenAI API key in the sidebar before generating a template."
            )
        elif instructions:
            with st.spinner("Analyzing instructions and generating template..."):
                # Generate template based on instructions and document content
                st.session_state.template_spec = generate_template_from_instructions(
                    instructions, st.session_state.knowledge_base
                )
                st.session_state.show_template_editor = True
            st.success(
                "Template generated! Go to the 'Edit Template' tab to customize it."
            )
        else:
            st.warning("Please provide instructions first")


def render_empty_template_section():
    st.subheader("Create Empty Template")
    st.info(
        "This option creates a minimal template that you can customize in the 'Edit Template' tab."
    )

    # Optional: Allow setting a name and description for the template
    template_name = st.text_input("Template Name", value="Custom Template")
    template_description = st.text_area(
        "Template Description", value="A custom template created from scratch"
    )

    if st.button("Create Empty Template"):
        # Create a minimal template structure
        st.session_state.template_spec = {
            "name": template_name,
            "version": "1.0.0",
            "description": template_description,
            "input": [
                {
                    "name": "input_1",
                    "description": "First input variable",
                    "type": "string",
                    "min": 1,
                    "max": 100,
                }
            ],
            "output": [
                {
                    "name": "output_1",
                    "description": "Generated output",
                    "type": "string",
                    "min": 10,
                    "max": 1000,
                }
            ],
            "prompt": "Based on the following information:\n{input_1}\n\nGenerate the following output.",
        }

        st.session_state.show_template_editor = True
        st.success(
            "Empty template created! Go to the 'Edit Template' tab to customize it."
        )

        # Optional: Initialize an empty knowledge base
        if "knowledge_base" not in st.session_state:
            st.session_state.knowledge_base = ""
