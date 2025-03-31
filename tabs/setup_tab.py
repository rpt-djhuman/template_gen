# tabs/setup_tab.py
import streamlit as st
import numpy as np
import pandas as pd
import json
from utils.llm_utils import generate_template_from_instructions
from utils.document_utils import parse_documents
from utils.template_utils import (
    create_example_templates,
    create_example_outputs,
    parse_template_file,
    sanitize_template_spec,
)
from utils.data_utils import process_uploaded_table


def render_setup_tab():
    st.header("Project Setup")

    # Add option to either upload a template or create a new one
    setup_option = st.radio(
        "Choose how to start your project",
        options=[
            "Create new template from documents",
            "Create template from tabular data",
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
    elif setup_option == "Create template from tabular data":
        render_tabular_data_template_section()


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
            # Sanitize the template to remove UI-specific keys
            template_spec = sanitize_template_spec(template_spec)
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
        key="document_kb_uploader",
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
                key="document_kb_preview",
            )

    # Step 2: Provide Instructions
    st.subheader("Step 2: Provide Instructions")
    instructions = st.text_area(
        "Describe what you want to create",
        placeholder="Describe what you want to create (e.g., 'Create a character background generator with name, faction, and race as inputs...')",
        height=150,
        key="document_instructions",
    )

    # Generate Template button
    if st.button("Generate Template", key="generate_document_template_btn"):
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
    template_name = st.text_input(
        "Template Name", value="Custom Template", key="empty_template_name"
    )
    template_description = st.text_area(
        "Template Description",
        value="A custom template created from scratch",
        key="empty_template_description",
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


def render_tabular_data_template_section():
    st.subheader("Create Template from Tabular Data")

    # Step 1: Upload tabular data file
    st.markdown("### Step 1: Upload Data")
    uploaded_file = st.file_uploader(
        "Upload a tabular data file",
        type=["csv", "xlsx", "xls", "json"],
        help="Upload a CSV, Excel, or JSON file containing your data",
        key="tabular_data_uploader",
    )

    if uploaded_file:
        # Process the uploaded file
        df, column_info, error = process_uploaded_table(uploaded_file)

        if error:
            st.error(error)
        else:
            # Store in session state
            st.session_state.uploaded_table = df
            st.session_state.table_column_info = column_info
            st.session_state.data_table = df

            # Display preview of the data
            st.success(
                f"Successfully loaded data with {len(df.columns)} columns and {len(df)} rows"
            )
            with st.expander("Data Preview", expanded=True):
                st.dataframe(df.head(5))

            # Step 2: Select input and output columns
            st.markdown("### Step 2: Select Columns for Template")

            # Template name and description
            template_name = st.text_input(
                "Template Name",
                value=f"{uploaded_file.name.split('.')[0]} Template",
                key="tabular_template_name",
            )
            template_description = st.text_area(
                "Template Description",
                value=f"Template generated from {uploaded_file.name}",
                key="tabular_template_description",
            )

            # Column selection
            st.markdown("#### Select Input Columns")
            st.info("Select columns that will be used as inputs in your template")

            input_columns = st.multiselect(
                "Input Columns",
                options=list(column_info.keys()),
                default=list(column_info.keys())[: min(3, len(column_info))],
                help="These columns will be used as inputs in your template",
                key="tabular_input_columns",
            )

            st.markdown("#### Select Output Columns")
            st.info("Select columns that will be used as outputs in your template")

            # Filter out input columns from output options
            output_options = [
                col for col in column_info.keys() if col not in input_columns
            ]
            output_columns = st.multiselect(
                "Output Columns",
                options=output_options,
                default=output_options[: min(1, len(output_options))],
                help="These columns will be used as outputs in your template",
                key="tabular_output_columns",
            )

            # Store selections in session state
            st.session_state.input_columns = input_columns
            st.session_state.output_columns = output_columns

            # Step 3: Create template
            st.markdown("### Step 3: Create Template")

            if st.button(
                "Create Template from Data", key="create_tabular_template_btn"
            ):
                if not input_columns:
                    st.error("Please select at least one input column")
                else:
                    input_specs = []
                    for col in input_columns:
                        col_spec = {
                            "name": col,
                            "description": column_info[col]["description"],
                        }
                        # Add other properties
                        for k, v in column_info[col].items():
                            if k not in ["name", "description"]:
                                col_spec[k] = ensure_json_serializable(v)
                        input_specs.append(col_spec)

                    output_specs = []
                    for col in output_columns:
                        col_spec = {
                            "name": col,
                            "description": column_info[col]["description"],
                        }
                        # Add other properties
                        for k, v in column_info[col].items():
                            if k not in ["name", "description"]:
                                col_spec[k] = ensure_json_serializable(v)
                        output_specs.append(col_spec)

                    template_spec = {
                        "name": template_name,
                        "version": "1.0.0",
                        "description": template_description,
                        "input": input_specs,
                        "output": output_specs,
                        "prompt": generate_prompt_from_columns(
                            input_columns, output_columns
                        ),
                    }

                    # If no output columns were selected, add a default output
                    if not output_columns:
                        template_spec["output"] = [
                            {
                                "name": "generated_output",
                                "description": "Generated output based on input data",
                                "type": "string",
                                "min": 10,
                                "max": 1000,
                            }
                        ]

                    # Store in session state
                    st.session_state.template_spec = template_spec
                    st.session_state.show_template_editor = True

                    # Success message
                    st.success(
                        "Template created from tabular data! Go to the 'Edit Template' tab to customize it."
                    )


def generate_prompt_from_columns(input_columns, output_columns):
    """Generate a basic prompt template from column names"""
    prompt = "Based on the following information:\n\n"

    # Add input placeholders
    for col in input_columns:
        prompt += f"{col}: {{{col}}}\n"

    # Add output instructions
    if output_columns:
        prompt += "\nGenerate the following outputs:\n"
        for col in output_columns:
            prompt += f"- {col}\n"
    else:
        prompt += "\nGenerate an appropriate response based on this information."

    return prompt


def ensure_json_serializable(obj):
    """
    Recursively convert any non-JSON serializable objects to serializable types.

    Args:
        obj: Any Python object

    Returns:
        JSON serializable version of the object
    """
    if isinstance(
        obj,
        (
            np.int_,
            np.intc,
            np.intp,
            np.int8,
            np.int16,
            np.int32,
            np.int64,
            np.uint8,
            np.uint16,
            np.uint32,
            np.uint64,
        ),
    ):
        return int(obj)
    elif isinstance(obj, (np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: ensure_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(ensure_json_serializable(item) for item in obj)
    elif pd and isinstance(obj, pd.Series):
        return obj.tolist()
    elif pd and isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    else:
        return obj
