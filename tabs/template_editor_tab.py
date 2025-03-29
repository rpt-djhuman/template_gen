# tabs/template_editor_tab.py
import streamlit as st
import pandas as pd
import json
from time import sleep
from utils.llm_utils import (
    generate_improved_prompt_template,
    generate_synthetic_outputs,
    suggest_variable_values_from_kb,
    analyze_knowledge_base,
)
from utils.document_utils import parse_documents


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
    if "added_suggestions" not in st.session_state:
        st.session_state.added_suggestions = set()
    if (
        "last_template" not in st.session_state
        or st.session_state.last_template != st.session_state.template_spec
    ):
        st.session_state.user_inputs = {}
        st.session_state.last_template = st.session_state.template_spec
    if "show_variable_editor" not in st.session_state:
        st.session_state.show_variable_editor = None
    if "show_output_editor" not in st.session_state:
        st.session_state.show_output_editor = None
    if "show_suggested_vars" not in st.session_state:
        st.session_state.show_suggested_vars = False


def render_template_settings(template_spec):
    with st.expander("Template Information (Metadata)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.template_spec["name"] = st.text_input(
                "Template Name", value=st.session_state.template_spec["name"]
            )
        with col2:
            st.session_state.template_spec["version"] = st.text_input(
                "Version", value=st.session_state.template_spec["version"]
            )

        st.session_state.template_spec["description"] = st.text_area(
            "Description",
            value=st.session_state.template_spec["description"],
            height=100,
        )

    # Prompt Template Section
    with st.expander("Prompt Template", expanded=True):
        st.info("Use {variable_name} to refer to input variables in your template")

        # Add buttons for prompt management
        col1, col2 = st.columns([1, 1])
        with col1:
            rewrite_prompt = st.button("AI Rewrite Prompt")
        with col2:
            reroll_prompt = st.button("Reroll Prompt Variation")

        # Handle prompt rewriting
        if rewrite_prompt or reroll_prompt:
            with st.spinner("Generating improved prompt template..."):
                improved_template = generate_improved_prompt_template(
                    st.session_state.template_spec,
                    st.session_state.knowledge_base,
                )
                # Only update if we got a valid result back
                if improved_template and len(improved_template) > 10:
                    st.session_state.template_spec["prompt"] = improved_template
                    st.success("Prompt template updated!")

        # Display the prompt template
        prompt_template = st.text_area(
            "Edit the prompt template",
            value=st.session_state.template_spec["prompt"],
            height=200,
        )
        st.session_state.template_spec["prompt"] = prompt_template

    # Knowledge Base Management Section
    with st.expander("Knowledge Base Management", expanded=False):
        st.info("Upload and manage documents to use as knowledge base")

        # Upload interface
        uploaded_files = st.file_uploader(
            "Upload documents",
            accept_multiple_files=True,
            type=["pdf", "txt", "docx", "html"],
        )

        # Handle document processing
        if uploaded_files:
            # Choose how to handle new uploads
            handle_method = st.radio(
                "How to handle new documents?",
                ["Replace existing", "Append to existing"],
                horizontal=True,
            )

            if st.button("Process Documents"):
                parse_documents.clear()
                analyze_knowledge_base.clear()
                st.session_state.kb_cleared = True
                with st.spinner("Processing documents..."):

                    if handle_method == "Replace existing":
                        new_content = parse_documents(uploaded_files)
                        st.session_state.knowledge_base = new_content
                        st.session_state.uploaded_filenames = [
                            file.name for file in uploaded_files
                        ]
                    else:  # Append
                        # Find new files by comparing filenames
                        new_files = []
                        duplicate_files = []

                        for file in uploaded_files:
                            if file.name in st.session_state.uploaded_filenames:
                                duplicate_files.append(file.name)
                            else:
                                new_files.append(file)
                                st.session_state.uploaded_filenames.append(file.name)

                        # Process only new files
                        if new_files:
                            new_content = parse_documents(new_files)
                            st.session_state.knowledge_base += "\n\n" + new_content

                        # Provide feedback about duplicates
                        if duplicate_files:
                            st.info(
                                f"Skipped {len(duplicate_files)} duplicate files: {', '.join(duplicate_files)}"
                            )

                    # Reset any analysis that depends on knowledge base
                    if "suggested_variables" in st.session_state:
                        st.session_state.suggested_variables = []
                    st.session_state.show_suggested_vars = False

                    st.success(f"Processed {len(uploaded_files)} documents")
                    st.rerun()

        # Display knowledge base information
        if st.session_state.knowledge_base:
            st.write(
                f"Knowledge base size: {len(st.session_state.knowledge_base)} characters"
            )

            # Clear knowledge base button
            # Display uploaded filenames
            if st.session_state.uploaded_filenames:
                st.write("Uploaded files:")
                for filename in st.session_state.uploaded_filenames:
                    st.write(f"- {filename}")

            if st.button("Clear Knowledge Base"):
                analyze_knowledge_base.clear()
                st.session_state.knowledge_base = ""
                st.session_state.kb_cleared = True
                st.session_state.uploaded_filenames = []
                if "suggested_variables" in st.session_state:
                    st.session_state.suggested_variables = []
                st.session_state.show_suggested_vars = False
                st.success("Knowledge base cleared")
                st.rerun()

            # Option to edit knowledge base directly
            edit_kb = st.checkbox("Edit knowledge base directly")
            if edit_kb:
                new_content = st.text_area(
                    "Edit knowledge base content",
                    value=st.session_state.knowledge_base,
                    height=300,
                )
                if st.button("Update Knowledge Base"):
                    analyze_knowledge_base.clear()
                    st.session_state.knowledge_base = new_content
                    if "suggested_variables" in st.session_state:
                        st.session_state.suggested_variables = []
                        st.session_state.show_suggested_vars = False
                    st.success("Knowledge base updated")
                    st.rerun()

    # Knowledge Base Analysis Section
    if st.session_state.knowledge_base:
        with st.expander("Knowledge Base Analysis", expanded=False):
            st.info("Analyze the knowledge base to suggest variables and values")

            if st.button(
                "Analyze Knowledge Base for Variables",
                key="analyze_kb_button_input",
            ):
                if not st.session_state.get("api_key") and not st.session_state.get(
                    "anthropic_api_key"
                ):
                    st.error(
                        "Please provide an OpenAI or Anthropic API key to analyze the knowledge base."
                    )
                else:
                    with st.spinner("Analyzing knowledge base..."):
                        suggested_vars = analyze_knowledge_base(
                            st.session_state.knowledge_base
                        )
                        if suggested_vars:
                            st.session_state.suggested_variables = suggested_vars
                            st.session_state.show_suggested_vars = True
                            st.success(
                                f"Found {len(suggested_vars)} potential variables in the knowledge base"
                            )
                        else:
                            st.warning(
                                "Could not extract variables from the knowledge base"
                            )

            # Display suggested variables if they exist
            if (
                st.session_state.suggested_variables
                and st.session_state.show_suggested_vars
            ):
                st.subheader("Suggested Variables")

                for i, var in enumerate(st.session_state.suggested_variables):
                    # Generate a unique ID for this variable
                    var_id = f"{var['name']}_{i}"

                    # Check if this variable has already been added
                    if var_id in st.session_state.added_suggestions:
                        continue

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(
                            f"**{var['name']}** ({var['type']}): {var['description']}"
                        )
                        if var.get("options"):
                            st.markdown(f"Options: {', '.join(var['options'])}")
                    with col2:
                        if st.button("Add", key=f"add_suggested_{var_id}"):
                            # Add this variable to the template
                            new_var = {
                                "name": var["name"],
                                "description": var["description"],
                                "type": var["type"],
                            }
                            if var.get("options"):
                                new_var["options"] = var["options"]
                            if var["type"] in ["string", "int", "float"]:
                                new_var["min"] = 1
                                new_var["max"] = 100

                            # Add to input variables
                            st.session_state.template_spec["input"].append(new_var)

                            # Mark this variable as added
                            st.session_state.added_suggestions.add(var_id)

                            # Show success message
                            st.success(f"Added {var['name']} to input variables!")

    # Input Variables Section
    with st.expander("Input Variables", expanded=True):
        # Add input variable button
        col1, col2 = st.columns([3, 1])
        with col1:
            new_input_name = st.text_input(
                "New input variable name", key="new_input_name"
            )
        with col2:
            if st.button("Add Input Variable"):
                new_var = {
                    "name": (
                        new_input_name
                        if new_input_name
                        else f"new_input_{len(st.session_state.template_spec['input']) + 1}"
                    ),
                    "description": "New input variable",
                    "type": "string",
                    "min": 1,
                    "max": 100,
                }
                st.session_state.template_spec["input"].append(new_var)

        # Display input variables with integrated input fields
        st.subheader("Input Variables")

        # Create a container for the variables
        for i, input_var in enumerate(st.session_state.template_spec["input"]):
            var_name = input_var["name"]
            var_type = input_var["type"]
            var_desc = input_var["description"]

            with st.container():
                # Variable header with description
                st.markdown(f"##### {var_name}\n###### {var_desc}")

                # Create columns for the variable controls
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    # Initialize user input if not exists
                    if var_name not in st.session_state.user_inputs:
                        if var_type == "bool":
                            st.session_state.user_inputs[var_name] = False
                        elif var_type == "categorical":
                            options = input_var.get("options", [])
                            min_selections = input_var.get("min", 1)
                            st.session_state.user_inputs[var_name] = (
                                options[:min_selections] if options else []
                            )
                        elif var_type in ["int", "float"]:
                            st.session_state.user_inputs[var_name] = input_var.get(
                                "min", 0
                            )
                        else:
                            st.session_state.user_inputs[var_name] = ""

                    # Create the appropriate input field based on variable type
                    if var_type == "string":
                        st.session_state.user_inputs[var_name] = st.text_input(
                            f"Enter value for {var_name}",
                            value=st.session_state.user_inputs[var_name],
                            key=f"use_{var_name}",
                        )
                    elif var_type == "int":
                        st.session_state.user_inputs[var_name] = st.number_input(
                            f"Enter value for {var_name}",
                            value=int(st.session_state.user_inputs[var_name]),
                            min_value=input_var.get("min", None),
                            max_value=input_var.get("max", None),
                            step=1,
                            key=f"use_{var_name}",
                        )
                    elif var_type == "float":
                        st.session_state.user_inputs[var_name] = st.number_input(
                            f"Enter value for {var_name}",
                            value=float(st.session_state.user_inputs[var_name]),
                            min_value=float(input_var.get("min", 0)),
                            max_value=float(input_var.get("max", 100)),
                            key=f"use_{var_name}",
                        )
                    elif var_type == "bool":
                        st.session_state.user_inputs[var_name] = st.checkbox(
                            f"Select value for {var_name}",
                            value=st.session_state.user_inputs[var_name],
                            key=f"use_{var_name}",
                        )
                    elif var_type == "categorical":
                        options = input_var.get("options", [])
                        min_selections = input_var.get("min", 1)
                        max_selections = input_var.get("max", 1)

                        if options:
                            current_value = st.session_state.user_inputs[var_name]

                            # Ensure current value is in options
                            if (
                                isinstance(current_value, str)
                                and current_value not in options
                            ):
                                options.append(current_value)
                            elif isinstance(current_value, (list, tuple)):
                                for val in current_value:
                                    if val not in options:
                                        options.append(val)

                            if min_selections == 1 and max_selections == 1:
                                # Single selection
                                st.session_state.user_inputs[var_name] = st.selectbox(
                                    f"Select value for {var_name}",
                                    options=options,
                                    index=(
                                        options.index(current_value)
                                        if isinstance(current_value, str)
                                        and current_value in options
                                        else 0
                                    ),
                                    key=f"use_{var_name}",
                                )
                            else:
                                # Multi-selection
                                st.session_state.user_inputs[var_name] = st.multiselect(
                                    f"Select {min_selections}-{max_selections} values for {var_name}",
                                    options=options,
                                    default=(
                                        current_value
                                        if isinstance(current_value, (list, tuple))
                                        else []
                                    ),
                                    key=f"use_{var_name}",
                                )
                        else:
                            st.warning(f"No options defined for {var_name}")

                with col2:
                    # Button to edit this variable
                    if st.button("Edit Settings", key=f"edit_input_{i}"):
                        st.session_state.show_variable_editor = i

                with col3:
                    # Button to remove this variable
                    if st.button("Remove", key=f"remove_input_{i}"):
                        st.session_state.template_spec["input"].pop(i)
                        st.rerun()

                # Show editor if this variable is selected
                if st.session_state.show_variable_editor == i:
                    with st.container():
                        st.markdown("---")
                        st.markdown(f"##### Variable Settings: {input_var['name']}")

                        # Name and description
                        input_var["name"] = st.text_input(
                            "Name",
                            value=input_var["name"],
                            key=f"input_name_{i}",
                        )
                        input_var["description"] = st.text_input(
                            "Description",
                            value=input_var["description"],
                            key=f"input_desc_{i}",
                        )

                        # Type selection
                        var_type = st.selectbox(
                            "Type",
                            options=[
                                "string",
                                "int",
                                "float",
                                "bool",
                                "categorical",
                            ],
                            index=[
                                "string",
                                "int",
                                "float",
                                "bool",
                                "categorical",
                            ].index(input_var["type"]),
                            key=f"input_type_{i}",
                        )
                        input_var["type"] = var_type

                        # Type-specific settings
                        if var_type in ["string", "int", "float"]:
                            col1, col2 = st.columns(2)
                            with col1:
                                input_var["min"] = st.number_input(
                                    "Min",
                                    value=int(input_var.get("min", 0)),
                                    key=f"input_min_{i}",
                                )
                            with col2:
                                input_var["max"] = st.number_input(
                                    "Max",
                                    value=int(input_var.get("max", 100)),
                                    key=f"input_max_{i}",
                                )

                        if var_type == "categorical":
                            # Suggest options from KB button
                            if st.button(
                                "Suggest Options from KB",
                                key=f"suggest_input_{i}",
                            ):
                                if not st.session_state.get(
                                    "api_key"
                                ) and not st.session_state.get("anthropic_api_key"):
                                    st.error(
                                        "Please provide an OpenAI API key to suggest options."
                                    )
                                elif not st.session_state.knowledge_base:
                                    st.warning(
                                        "No knowledge base available. Please upload documents first."
                                    )
                                else:
                                    with st.spinner(
                                        f"Suggesting options for {input_var['name']}..."
                                    ):
                                        suggestions = suggest_variable_values_from_kb(
                                            input_var["name"],
                                            "categorical",
                                            st.session_state.knowledge_base,
                                        )
                                        if suggestions and "options" in suggestions:
                                            input_var["options"] = suggestions[
                                                "options"
                                            ]
                                            st.success(
                                                f"Found {len(suggestions['options'])} options"
                                            )
                                        else:
                                            st.warning(
                                                "Could not find suitable options in the knowledge base"
                                            )

                            # Options editor
                            options = input_var.get("options", [])
                            options_str = st.text_area(
                                "Options (one per line)",
                                value="\n".join(options),
                                key=f"input_options_{i}",
                            )
                            input_var["options"] = [
                                opt.strip()
                                for opt in options_str.split("\n")
                                if opt.strip()
                            ]

                            # Min/max selections
                            col1, col2 = st.columns(2)
                            with col1:
                                input_var["min"] = st.number_input(
                                    "Min selections",
                                    value=int(input_var.get("min", 1)),
                                    min_value=0,
                                    key=f"input_cat_min_{i}",
                                )
                            with col2:
                                input_var["max"] = st.number_input(
                                    "Max selections",
                                    value=int(input_var.get("max", 1)),
                                    min_value=1,
                                    key=f"input_cat_max_{i}",
                                )

                        # Close editor button
                        if st.button("Done Editing", key=f"done_input_{i}"):
                            st.session_state.show_variable_editor = None
                            st.rerun()

                        st.markdown("---")

                st.divider()

    # Output Variables Section
    with st.expander("Output Variables", expanded=True):
        # Add output variable button
        col1, col2 = st.columns([3, 1])
        with col1:
            new_output_name = st.text_input(
                "New output variable name", key="new_output_name"
            )
        with col2:
            if st.button("Add Output Variable"):
                new_var = {
                    "name": (
                        new_output_name
                        if new_output_name
                        else f"new_output_{len(st.session_state.template_spec['output']) + 1}"
                    ),
                    "description": "New output variable",
                    "type": "string",
                    "min": 1,
                    "max": 100,
                }
                st.session_state.template_spec["output"].append(new_var)

        # Display output variables in a table-like format
        st.subheader("Output Variables")

        # Create a container for the variables
        for i, output_var in enumerate(st.session_state.template_spec["output"]):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{output_var['name']}** - {output_var['description']}")

            with col2:
                # Button to edit this variable
                if st.button("Edit", key=f"edit_output_{i}"):
                    st.session_state.show_output_editor = i

            with col3:
                # Button to remove this variable
                if st.button("Remove", key=f"remove_output_{i}"):
                    st.session_state.template_spec["output"].pop(i)
                    st.rerun()

            # Show editor if this variable is selected
            if st.session_state.show_output_editor == i:
                with st.container():
                    st.markdown("---")
                    st.markdown(f"##### Edit Output Variable: {output_var['name']}")

                    # Name and description
                    output_var["name"] = st.text_input(
                        "Name", value=output_var["name"], key=f"output_name_{i}"
                    )
                    output_var["description"] = st.text_input(
                        "Description",
                        value=output_var["description"],
                        key=f"output_desc_{i}",
                    )

                    # Type selection
                    var_type = st.selectbox(
                        "Type",
                        options=[
                            "string",
                            "int",
                            "float",
                            "bool",
                            "categorical",
                        ],
                        index=[
                            "string",
                            "int",
                            "float",
                            "bool",
                            "categorical",
                        ].index(output_var["type"]),
                        key=f"output_type_{i}",
                    )
                    output_var["type"] = var_type

                    # Type-specific settings
                    if var_type in ["string", "int", "float"]:
                        col1, col2 = st.columns(2)
                        with col1:
                            output_var["min"] = st.number_input(
                                "Min",
                                value=int(output_var.get("min", 0)),
                                key=f"output_min_{i}",
                            )
                        with col2:
                            output_var["max"] = st.number_input(
                                "Max",
                                value=int(output_var.get("max", 100)),
                                key=f"output_max_{i}",
                            )

                    if var_type == "categorical":
                        # Suggest options from KB button
                        if st.button(
                            "Suggest Options from KB", key=f"suggest_output_{i}"
                        ):
                            client = get_openai_client()
                            if not client:
                                st.error(
                                    "Please provide an OpenAI API key to suggest options."
                                )
                            elif not st.session_state.knowledge_base:
                                st.warning(
                                    "No knowledge base available. Please upload documents first."
                                )
                            else:
                                with st.spinner(
                                    f"Suggesting options for {output_var['name']}..."
                                ):
                                    suggestions = suggest_variable_values_from_kb(
                                        output_var["name"],
                                        "categorical",
                                        st.session_state.knowledge_base,
                                    )
                                    if suggestions and "options" in suggestions:
                                        output_var["options"] = suggestions["options"]
                                        st.success(
                                            f"Found {len(suggestions['options'])} options"
                                        )
                                    else:
                                        st.warning(
                                            "Could not find suitable options in the knowledge base"
                                        )

                        # Options editor
                        options = output_var.get("options", [])
                        options_str = st.text_area(
                            "Options (one per line)",
                            value="\n".join(options),
                            key=f"output_options_{i}",
                        )
                        output_var["options"] = [
                            opt.strip()
                            for opt in options_str.split("\n")
                            if opt.strip()
                        ]

                        # Min/max selections
                        col1, col2 = st.columns(2)
                        with col1:
                            output_var["min"] = st.number_input(
                                "Min selections",
                                value=int(output_var.get("min", 1)),
                                min_value=0,
                                key=f"output_cat_min_{i}",
                            )
                        with col2:
                            output_var["max"] = st.number_input(
                                "Max selections",
                                value=int(output_var.get("max", 1)),
                                min_value=1,
                                key=f"output_cat_max_{i}",
                            )

                    # Close editor button
                    if st.button("Done Editing", key=f"done_output_{i}"):
                        st.session_state.show_output_editor = None
                        st.rerun()

                    st.markdown("---")

    # tabs/template_editor_tab.py
    # In the render_template_settings function, within the "Data Table Integration" expander

    with st.expander("Data Table Integration", expanded=False):
        st.info(
            "Use values from your uploaded data table to populate template variables"
        )

        # Check if a data table exists
        if "data_table" in st.session_state and st.session_state.data_table is not None:
            df = st.session_state.data_table
            st.success(
                f"Using data table with {len(df)} rows and {len(df.columns)} columns"
            )

            # Get input and output variable names from template
            input_vars = [var["name"] for var in template_spec["input"]]
            output_vars = [var["name"] for var in template_spec["output"]]

            # Filter columns to show only those that are inputs or outputs
            # Also filter out any columns with empty/blank names
            relevant_columns = [
                col
                for col in df.columns
                if col in input_vars
                or col in output_vars
                and col.strip() != ""  # Filter out blank column names
            ]

            # If no relevant columns found, show all columns except blank ones
            if not relevant_columns:
                st.warning(
                    "None of the table columns match template variables. Showing all non-blank columns."
                )
                filtered_df = df[[col for col in df.columns if col.strip() != ""]]
            else:
                # Create filtered dataframe with only relevant columns
                filtered_df = df[relevant_columns].copy()
                st.info(
                    f"Showing {len(relevant_columns)} columns that match template variables."
                )

            # Show the dataframe with row numbers
            filtered_df_with_index = filtered_df.copy()
            # filtered_df_with_index.insert(0, "Row #", range(len(filtered_df)))
            st.dataframe(filtered_df_with_index)

            # Add option to show all columns
            show_all_columns = st.checkbox("Show all columns", value=False)
            if show_all_columns:
                # Filter out blank columns even when showing all
                valid_columns = [col for col in df.columns if col.strip() != ""]
                df_with_index = df[valid_columns].copy()
                # df_with_index.insert(0, "Row #", range(len(df)))
                st.dataframe(df_with_index)

            row_idx = st.number_input(
                "Select row number",
                min_value=0,
                max_value=len(df) - 1 if len(df) > 0 else 0,
                value=0,
            )

            if st.button("Use Selected Row"):
                # Map table columns to template variables
                updated_inputs = False
                for input_var in template_spec["input"]:
                    var_name = input_var["name"]
                    # Check if this variable exists as a column
                    if var_name in df.columns:
                        # Get the value from the selected row
                        value = df.iloc[row_idx][var_name]

                        # Skip NaN values
                        if pd.isna(value):
                            continue

                        # Update the user input based on variable type
                        var_type = input_var["type"]
                        if var_type == "string":
                            st.session_state.user_inputs[var_name] = str(value)
                            updated_inputs = True
                        elif var_type == "int":
                            try:
                                st.session_state.user_inputs[var_name] = int(value)
                                updated_inputs = True
                            except (ValueError, TypeError):
                                st.warning(
                                    f"Could not convert '{value}' to integer for {var_name}"
                                )
                        elif var_type == "float":
                            try:
                                st.session_state.user_inputs[var_name] = float(value)
                                updated_inputs = True
                            except (ValueError, TypeError):
                                st.warning(
                                    f"Could not convert '{value}' to float for {var_name}"
                                )
                        elif var_type == "bool":
                            # Handle various boolean representations
                            if isinstance(value, bool):
                                st.session_state.user_inputs[var_name] = value
                                updated_inputs = True
                            elif isinstance(value, (int, float)):
                                st.session_state.user_inputs[var_name] = bool(value)
                                updated_inputs = True
                            elif isinstance(value, str):
                                st.session_state.user_inputs[var_name] = (
                                    value.lower() in ("true", "yes", "1", "t", "y")
                                )
                                updated_inputs = True
                        elif var_type == "categorical":
                            # For categorical variables, ensure the value is in the options
                            if isinstance(value, str):
                                if (
                                    "options" in input_var
                                    and value not in input_var["options"]
                                ):
                                    input_var["options"].append(value)
                                st.session_state.user_inputs[var_name] = value
                                updated_inputs = True
                            elif isinstance(value, (list, tuple)):
                                # Handle multi-select categorical
                                for item in value:
                                    if (
                                        "options" in input_var
                                        and item not in input_var["options"]
                                    ):
                                        input_var["options"].append(item)
                                st.session_state.user_inputs[var_name] = list(value)
                                updated_inputs = True

                # Store the current row index for later comparison
                st.session_state.current_table_row = row_idx

                if updated_inputs:
                    st.success(
                        f"Values from row {row_idx} loaded into template variables"
                    )
                    # Create a unique key to force widget recreation
                    st.session_state.input_update_key = (
                        f"update_{pd.Timestamp.now().isoformat()}"
                    )
                    # Force a rerun to update the UI with the new values
                    st.rerun()
                else:
                    st.warning(
                        "No matching columns found between the table and template variables"
                    )
        else:
            st.warning("No data table available. Upload a table in the Setup tab.")

    # Template JSON
    with st.expander("Template JSON", expanded=False):
        st.json(st.session_state.template_spec)

        # Download button
        template_json = json.dumps(st.session_state.template_spec, indent=2)
        st.download_button(
            label="Download Template JSON",
            data=template_json,
            file_name="template_spec.json",
            mime="application/json",
        )


# tabs/template_editor_tab.py
def render_generation_section(template_spec):
    st.header("Generation")

    # Handle the lore/knowledge base as a special variable
    prompt_template = st.session_state.template_spec["prompt"]
    if "{lore}" in prompt_template:
        with st.expander("Document Knowledge Base", expanded=False):
            st.markdown("#### Document Knowledge Base")

            # Display info about the knowledge base
            if st.session_state.knowledge_base:
                st.success(
                    f"Using content from {len(st.session_state.uploaded_filenames) if 'uploaded_filenames' in st.session_state else 'uploaded'} documents as knowledge base"
                )

                # Use a button to toggle knowledge base content view instead of an expander
                if st.button("View/Hide Knowledge Base Content", key="toggle_kb_view"):
                    st.session_state.show_kb_content = not st.session_state.get(
                        "show_kb_content", False
                    )

                if st.session_state.get("show_kb_content", False):
                    st.text_area(
                        "Knowledge base content",
                        value=st.session_state.knowledge_base[:2000]
                        + (
                            "..." if len(st.session_state.knowledge_base) > 2000 else ""
                        ),
                        height=200,
                        disabled=True,
                    )

                # Add option to edit if needed
                use_edited_lore = st.checkbox("Edit knowledge base content")
                if use_edited_lore:
                    st.session_state.user_inputs["lore"] = st.text_area(
                        "Edit knowledge base for this generation",
                        value=st.session_state.knowledge_base,
                        height=300,
                    )
                else:
                    st.session_state.user_inputs["lore"] = (
                        st.session_state.knowledge_base
                    )
            else:
                st.warning("No documents uploaded. You can provide custom lore below.")
                st.session_state.user_inputs["lore"] = st.text_area(
                    "Enter background information or context",
                    placeholder="Enter custom lore or background information here...",
                    height=150,
                )

    # Check if we have original output data from the uploaded table
    has_original_outputs = False
    original_output_data = {}

    # Check if we have a data table and the current input values match a row in the table
    if "data_table" in st.session_state and st.session_state.data_table is not None:
        df = st.session_state.data_table
        output_vars = [var["name"] for var in template_spec["output"]]

        # Only proceed if we have output variables defined in the template
        if output_vars:
            # Get the current row if we're using data from the table
            if "current_table_row" in st.session_state:
                row_idx = st.session_state.current_table_row
                if 0 <= row_idx < len(df):
                    # Extract original output values from this row
                    for var_name in output_vars:
                        if var_name in df.columns:
                            value = df.iloc[row_idx][var_name]
                            if not pd.isna(value):  # Skip NaN values
                                original_output_data[var_name] = value
                                has_original_outputs = True

    # Generate Output button
    if st.button("Generate Output", key="generate_button"):
        # Check if API key is provided
        if not st.session_state.get("api_key") and not st.session_state.get(
            "anthropic_api_key"
        ):
            st.error(
                "Please provide an OpenAI or Anthropic API key in the sidebar before generating output."
            )
        else:
            # Fill the prompt template with user-provided values
            filled_prompt = prompt_template
            for var_name, var_value in st.session_state.user_inputs.items():
                filled_prompt = filled_prompt.replace(f"{{{var_name}}}", str(var_value))

            # Show the filled prompt
            with st.expander("View populated prompt"):
                st.text_area(
                    "Prompt sent to LLM",
                    value=filled_prompt,
                    height=200,
                    disabled=True,
                )

            # Call LLM with the filled prompt
            # Create a single input data item from user inputs
            input_data = [st.session_state.user_inputs.copy()]

            # Create a copy of the template spec
            template_spec_copy = st.session_state.template_spec.copy()

            # Call generate_synthetic_outputs with the input data
            with st.spinner("Generating output..."):
                model_selected = st.session_state.model
                generated_outputs = generate_synthetic_outputs(
                    template_spec_copy,
                    input_data,
                    st.session_state.knowledge_base,
                    max_retries=3,
                )

            # Extract the first output (since we only have one input)
            if generated_outputs and len(generated_outputs) > 0:
                # The output contains both input and output fields
                # We only want to display the output fields
                output_vars = [var["name"] for var in template_spec_copy["output"]]
                output_data = {
                    k: v for k, v in generated_outputs[0].items() if k in output_vars
                }
                st.session_state.generated_output = output_data
            else:
                st.session_state.generated_output = {
                    "error": "Failed to generate output"
                }

    # Display generated output
    if "generated_output" in st.session_state and st.session_state.generated_output:
        st.header("Generated Output")

        # Check if the output is a dictionary (JSON)
        if isinstance(st.session_state.generated_output, dict):
            # Display as JSON
            st.json(st.session_state.generated_output)

            # Option to save the output as JSON
            output_json = json.dumps(st.session_state.generated_output, indent=2)
            st.download_button(
                label="Download Output (JSON)",
                data=output_json,
                file_name="generated_output.json",
                mime="application/json",
            )

            # Show comparison with original output if available
            if has_original_outputs:
                with st.expander("Compare with Original Data", expanded=False):
                    st.subheader("Original vs. Generated Output")

                    # Create a comparison table
                    comparison_data = []
                    for var_name in original_output_data.keys():
                        original_value = original_output_data.get(var_name, "N/A")
                        generated_value = st.session_state.generated_output.get(
                            var_name, "N/A"
                        )
                        comparison_data.append(
                            {
                                "Variable": var_name,
                                "Original Value": original_value,
                                "Generated Value": generated_value,
                            }
                        )

                    if comparison_data:
                        comparison_df = pd.DataFrame(comparison_data)
                        st.dataframe(comparison_df)
                    else:
                        st.info("No matching output variables found for comparison.")
        else:
            # Display as text
            st.write(st.session_state.generated_output)

            # Option to save the output as text
            st.download_button(
                label="Download Output",
                data=str(st.session_state.generated_output),
                file_name="generated_output.txt",
                mime="text/plain",
            )
