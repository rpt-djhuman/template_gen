# tabs/data_generation_tab.py
import streamlit as st
import json
import pandas as pd
import math
import random
from io import BytesIO
from utils.llm_utils import (
    generate_synthetic_inputs_hybrid,
    generate_synthetic_outputs,
    generate_missing_column_values,
    generate_categorical_permutations,
)
from utils.data_utils import (
    calculate_cartesian_product_size,
    prepare_dataframe_with_json_columns,
    prepare_dataframe_for_parquet,
)


def render_data_generation_tab():
    if st.session_state.show_template_editor and st.session_state.template_spec:
        st.header("Generate Synthetic Data")

        with st.expander("Template Information", expanded=False):
            st.json(st.session_state.template_spec)

        # Data generation controls
        st.subheader("Generation Settings")
        num_samples = render_generation_settings()

        # Categorical variable options
        template_spec_copy, categorical_vars, product_size = render_categorical_options(
            num_samples
        )

        # Generate inputs button and display
        render_input_generation_section(
            num_samples, categorical_vars, template_spec_copy
        )

        # Output generation section
        render_output_generation_section()

        # Display combined data
        render_combined_data_section()
    else:
        st.info(
            "No template has been generated yet. Go to the 'Setup' tab to create one."
        )


def render_generation_settings():
    col1, col2 = st.columns(2)
    with col1:
        num_samples = st.number_input(
            "Number of samples to generate", min_value=1, max_value=100, value=5
        )
    with col2:
        # Store the temperature value in session state
        st.session_state.temperature = st.slider(
            "Temperature (creativity)",
            min_value=0.1,
            max_value=1.0,
            value=0.7,
            step=0.1,
        )
    # Initialize containers for generated data
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

    return num_samples


def render_categorical_options(num_samples):
    categorical_vars = [
        var
        for var in st.session_state.template_spec["input"]
        if var["type"] == "categorical" and var.get("options")
    ]

    # Create a copy of the template spec for modification
    template_spec_copy = st.session_state.template_spec.copy()
    template_spec_copy["input"] = st.session_state.template_spec["input"].copy()

    # Initialize UI state for categorical variables if not present
    if "categorical_ui_state" not in st.session_state:
        st.session_state.categorical_ui_state = {}

    # In tab3, modify the categorical variable options section
    if categorical_vars:
        st.subheader("Categorical Variable Options")
        st.info(
            "Select which options to include in the permutations for each categorical variable."
        )

        # For each categorical variable, allow selecting options
        for i, var in enumerate(
            [
                v
                for v in template_spec_copy["input"]
                if v["type"] == "categorical" and v.get("options")
            ]
        ):
            var_name = var["name"]

            # Initialize UI state for this variable if not present
            if var_name not in st.session_state.categorical_ui_state:
                st.session_state.categorical_ui_state[var_name] = {
                    "selected_options": var.get("options", []).copy(),
                    "previous_options": var.get("options", []).copy(),
                }

            with st.expander(f"{var_name} - {var['description']}", expanded=False):
                options = var.get("options", [])

                # Update previous_options if options have changed
                if set(options) != set(
                    st.session_state.categorical_ui_state[var_name]["previous_options"]
                ):
                    # Find new options that weren't in the previous options list
                    new_options = [
                        opt
                        for opt in options
                        if opt
                        not in st.session_state.categorical_ui_state[var_name][
                            "previous_options"
                        ]
                    ]

                    # Add new options to selected_options
                    if new_options:
                        st.session_state.categorical_ui_state[var_name][
                            "selected_options"
                        ].extend(new_options)

                    # Update previous_options
                    st.session_state.categorical_ui_state[var_name][
                        "previous_options"
                    ] = options.copy()

                # Add "Select All" and "Clear All" buttons
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(
                        f"Select All Options for {var_name}",
                        key=f"select_all_{i}",
                    ):
                        st.session_state.categorical_ui_state[var_name][
                            "selected_options"
                        ] = options.copy()
                with col2:
                    if st.button(
                        f"Clear All Options for {var_name}", key=f"clear_all_{i}"
                    ):
                        st.session_state.categorical_ui_state[var_name][
                            "selected_options"
                        ] = []

                # Create multiselect for options
                st.session_state.categorical_ui_state[var_name]["selected_options"] = (
                    st.multiselect(
                        f"Select options to include for {var_name}",
                        options=options,
                        default=st.session_state.categorical_ui_state[var_name][
                            "selected_options"
                        ],
                        key=f"options_select_{i}",
                    )
                )

                # Show selected count
                st.write(
                    f"Selected {len(st.session_state.categorical_ui_state[var_name]['selected_options'])} out of {len(options)} options"
                )

        # Calculate and display Cartesian product size
        # Create a temporary list of variables with selected_options for calculation
        temp_vars_for_calculation = []
        for var in [
            v for v in template_spec_copy["input"] if v["type"] == "categorical"
        ]:
            var_copy = var.copy()
            var_copy["options"] = st.session_state.categorical_ui_state[var["name"]][
                "selected_options"
            ]
            temp_vars_for_calculation.append(var_copy)

        product_size, var_counts = calculate_cartesian_product_size(
            temp_vars_for_calculation
        )

        st.subheader("Combination Analysis")
        st.info(f"Total number of possible combinations: {product_size:,}")

        # Display breakdown of combinations
        st.write("Breakdown by variable:")
        for var in var_counts:
            st.write(f"- {var['name']}: {var['count']:,} possible values")

        if product_size > num_samples:
            st.warning(
                f"Note: Only {num_samples} samples will be generated from the {product_size:,} possible combinations"
            )
        elif product_size < num_samples:
            st.warning(
                f"Note: Some combinations will be repeated to reach {num_samples} samples (only {product_size:,} unique combinations possible)"
            )
    else:
        product_size = 0

    return template_spec_copy, categorical_vars, product_size


# tabs/data_generation_tab.py
def render_input_generation_section(num_samples, categorical_vars, template_spec_copy):
    if "data_table" in st.session_state and st.session_state.data_table is not None:
        df = st.session_state.data_table
        st.info(f"You have an uploaded data table with {len(df)} rows")

        # Check for missing columns in the table
        template_inputs = [var["name"] for var in template_spec_copy["input"]]
        missing_columns = [var for var in template_inputs if var not in df.columns]

        use_table = st.checkbox("Use data from uploaded table", value=False)

        if use_table:
            # Options for using the table
            if missing_columns:
                st.warning(
                    f"Your table is missing the following input columns: {', '.join(missing_columns)}"
                )
                st.info(
                    "You need to augment the table with missing columns before using it directly."
                )

                # Only show the augment option when there are missing columns
                table_option = "Augment table with missing columns"
            else:
                # If no missing columns, show all options
                table_option = st.radio(
                    "How to use the table data:",
                    options=[
                        "Use table as-is",
                        "Generate new rows similar to table",
                        "Augment table with missing columns",
                    ],
                )

            if table_option == "Use table as-is":
                if st.button("Load Table Data"):
                    # Map table columns to template variables
                    template_inputs = [
                        var["name"] for var in template_spec_copy["input"]
                    ]

                    # Create synthetic inputs from table
                    synthetic_inputs = []
                    for i in range(len(df)):
                        row_data = {}
                        for var_name in template_inputs:
                            if var_name in df.columns:
                                row_data[var_name] = df.iloc[i][var_name]
                            else:
                                # For missing columns, use empty values
                                row_data[var_name] = ""
                        synthetic_inputs.append(row_data)

                    st.session_state.synthetic_inputs = synthetic_inputs
                    st.success(f"Loaded {len(synthetic_inputs)} rows from table")

            elif table_option == "Generate new rows similar to table":
                num_new_rows = st.number_input(
                    "Number of new rows to generate",
                    min_value=1,
                    max_value=100,
                    value=5,
                )

                if st.button("Generate Similar Rows"):
                    if not st.session_state.get("api_key") and not st.session_state.get(
                        "anthropic_api_key"
                    ):
                        st.error(
                            "Please provide an OpenAI or Anthropic API key in the sidebar."
                        )
                    else:
                        with st.spinner(
                            f"Generating {num_new_rows} new rows similar to table data..."
                        ):
                            # This would call a new function to generate rows similar to existing data
                            # For now, we'll use the existing function but add table examples
                            template_spec_copy["examples"] = df.head(
                                min(5, len(df))
                            ).to_dict("records")

                            st.session_state.synthetic_inputs = (
                                generate_synthetic_inputs_hybrid(
                                    template_spec_copy, num_samples=num_new_rows
                                )
                            )

                            st.success(
                                f"Generated {len(st.session_state.synthetic_inputs)} new rows"
                            )

            elif table_option == "Augment table with missing columns":
                # Identify missing columns
                template_inputs = [var["name"] for var in template_spec_copy["input"]]
                missing_columns = [
                    var for var in template_inputs if var not in df.columns
                ]

                if missing_columns:
                    st.write(f"Missing input columns: {', '.join(missing_columns)}")

                    if st.button("Generate Missing Columns"):
                        if not st.session_state.get(
                            "api_key"
                        ) and not st.session_state.get("anthropic_api_key"):
                            st.error(
                                "Please provide an OpenAI or Anthropic API key in the sidebar."
                            )
                        else:
                            with st.spinner(
                                f"Generating values for {len(missing_columns)} missing columns..."
                            ):
                                # Create a copy of the table data
                                augmented_data = df.to_dict("records")

                                # Get the missing column variable definitions
                                missing_var_defs = [
                                    var
                                    for var in template_spec_copy["input"]
                                    if var["name"] in missing_columns
                                ]

                                # Separate categorical and non-categorical variables
                                missing_cat_vars = [
                                    var
                                    for var in missing_var_defs
                                    if var["type"] == "categorical"
                                    and var.get("options")
                                ]

                                # Pre-generate categorical permutations if needed
                                cat_permutations = {}
                                if missing_cat_vars:
                                    # Generate permutations for categorical variables
                                    # This ensures we get a good distribution of values
                                    cat_permutations = generate_categorical_permutations(
                                        missing_cat_vars,
                                        min(
                                            20, len(augmented_data)
                                        ),  # Generate a reasonable number of permutations
                                    )

                                # For each row, generate the missing values
                                progress_bar = st.progress(0)
                                for i, row in enumerate(augmented_data):
                                    try:
                                        # Update progress
                                        progress_bar.progress(
                                            min((i + 1) / len(augmented_data), 1.0)
                                        )

                                        # If we have categorical permutations, use them
                                        if cat_permutations:
                                            # Select a random permutation for categorical values
                                            cat_values = random.choice(cat_permutations)

                                            # For non-categorical variables, use the LLM
                                            missing_non_cat_vars = [
                                                var
                                                for var in missing_var_defs
                                                if var not in missing_cat_vars
                                            ]

                                            if missing_non_cat_vars:
                                                # Add categorical values to the row context
                                                row_with_cats = row.copy()
                                                row_with_cats.update(cat_values)

                                                # Generate non-categorical values
                                                non_cat_values = generate_missing_column_values(
                                                    row_data=row_with_cats,
                                                    missing_var_defs=missing_non_cat_vars,
                                                )

                                                # Combine all values
                                                missing_values = {
                                                    **cat_values,
                                                    **non_cat_values,
                                                }
                                            else:
                                                # Only categorical variables to fill
                                                missing_values = cat_values
                                        else:
                                            # No categorical variables, use the LLM for all missing columns
                                            missing_values = (
                                                generate_missing_column_values(
                                                    row_data=row,
                                                    missing_var_defs=missing_var_defs,
                                                )
                                            )

                                        # Update the row with the generated values
                                        row.update(missing_values)

                                    except Exception as e:
                                        st.warning(
                                            f"Error generating values for row {i+1}: {str(e)}"
                                        )
                                        # Use default values for any errors
                                        for var in missing_var_defs:
                                            row[var["name"]] = get_default_value(var)

                                # Ensure progress bar completes
                                progress_bar.progress(1.0)

                                # Store the augmented data in session state
                                st.session_state.synthetic_inputs = augmented_data

                                # Create a DataFrame from the augmented data to display
                                augmented_df = pd.DataFrame(augmented_data)

                                # Display the augmented table
                                st.subheader("Augmented Table with Missing Columns")
                                st.dataframe(augmented_df)

                                # Provide a download button for the augmented table
                                csv = augmented_df.to_csv(index=False)
                                st.download_button(
                                    label="Download Augmented Table (CSV)",
                                    data=csv,
                                    file_name="augmented_table.csv",
                                    mime="text/csv",
                                )

                                st.success(
                                    f"Augmented {len(augmented_data)} rows with missing columns"
                                )
                else:
                    st.success("All template input variables exist in the table!")

            return  # Skip the regular generation button
    if st.button("Generate Synthetic Inputs"):
        if not st.session_state.get("api_key") and not st.session_state.get(
            "anthropic_api_key"
        ):
            st.error("Please provide an OpenAI or Anthropic API key in the sidebar.")
        else:
            with st.spinner(f"Generating {num_samples} synthetic input samples..."):
                # Create a temporary template spec with selected options for generation
                generation_template = template_spec_copy.copy()
                generation_template["input"] = template_spec_copy["input"].copy()

                # Update categorical variables with selected options
                if categorical_vars:
                    for i, var in enumerate(generation_template["input"]):
                        if (
                            var["type"] == "categorical"
                            and var.get("options")
                            and var["name"] in st.session_state.categorical_ui_state
                        ):
                            # Create a copy of the variable
                            var_copy = var.copy()
                            # Set options to only the selected ones
                            var_copy["options"] = st.session_state.categorical_ui_state[
                                var["name"]
                            ]["selected_options"]
                            # Replace the variable in the template
                            generation_template["input"][i] = var_copy

                    st.session_state.synthetic_inputs = (
                        generate_synthetic_inputs_hybrid(
                            generation_template, num_samples=num_samples
                        )
                    )
                else:
                    st.session_state.synthetic_inputs = (
                        generate_synthetic_inputs_hybrid(
                            st.session_state.template_spec, num_samples=num_samples
                        )
                    )
            if st.session_state.synthetic_inputs:
                st.success(
                    f"Generated {len(st.session_state.synthetic_inputs)} input samples"
                )
                # Reset selected samples when new inputs are generated
                st.session_state.selected_samples = []
                # Reset modified prompt when new inputs are generated
                st.session_state.modified_prompt_template = (
                    st.session_state.template_spec["prompt"]
                )

    # Display generated inputs if available
    if st.session_state.synthetic_inputs:
        st.subheader("Generated Input Data")

        # Show data in a table
        input_df = pd.DataFrame(st.session_state.synthetic_inputs)
        st.dataframe(input_df)

        # Download button for inputs
        input_csv = input_df.to_csv(index=False)
        st.download_button(
            label="Download Input Data (CSV)",
            data=input_csv,
            file_name="synthetic_inputs.csv",
            mime="text/csv",
        )


# tabs/data_generation_tab.py
def render_output_generation_section():
    st.subheader("Generate Outputs")

    # Initialize the modified prompt template with the current template from session state
    if (
        not st.session_state.modified_prompt_template
        or st.session_state.modified_prompt_template
        != st.session_state.template_spec["prompt"]
    ):
        st.session_state.modified_prompt_template = st.session_state.template_spec[
            "prompt"
        ]

    # Allow editing the prompt template
    with st.expander("View/Edit Prompt Template", expanded=False):
        st.info(
            "You can modify the prompt template used for generating outputs. Use {variable_name} to refer to input variables."
        )

        st.session_state.modified_prompt_template = st.text_area(
            "Prompt Template",
            value=st.session_state.modified_prompt_template,
            height=200,
        )

        # Button to reset to original template
        if st.button("Reset to Original Template"):
            st.session_state.modified_prompt_template = st.session_state.template_spec[
                "prompt"
            ]
            st.success("Prompt template reset to original")

    # Sample selection options
    selection_method = st.radio(
        "Select samples for output generation",
        options=["Generate for all samples", "Select specific samples"],
        index=0,
        key="selection_method_radio",
    )

    if selection_method == "Select specific samples":
        # Create a list of sample indices for selection
        sample_options = [
            f"Sample {i+1}" for i in range(len(st.session_state.synthetic_inputs))
        ]

        # Allow multi-selection of samples
        selected_indices = st.multiselect(
            "Select samples to generate outputs for",
            options=range(len(sample_options)),
            format_func=lambda i: sample_options[i],
        )

        # Store selected samples
        st.session_state.selected_samples = selected_indices

        # Preview selected samples
        if selected_indices:
            st.write(f"Selected {len(selected_indices)} samples:")
            selected_df = pd.DataFrame(
                [st.session_state.synthetic_inputs[i] for i in selected_indices]
            )
            st.dataframe(selected_df)
    else:
        # Use all samples
        st.session_state.selected_samples = list(
            range(len(st.session_state.synthetic_inputs))
        )

    # Preview the prompt for a selected sample
    if st.session_state.selected_samples:
        with st.expander("Preview Prompt for Sample", expanded=False):
            # Let user select which sample to preview
            preview_index = st.selectbox(
                "Select a sample to preview prompt",
                options=st.session_state.selected_samples,
                format_func=lambda i: f"Sample {i+1}",
            )

            # Get the selected sample
            sample = st.session_state.synthetic_inputs[preview_index]

            # Fill the prompt template with sample values
            filled_prompt = st.session_state.modified_prompt_template
            for var_name, var_value in sample.items():
                filled_prompt = filled_prompt.replace(f"{{{var_name}}}", str(var_value))

            # Replace {lore} with knowledge base if present
            if "{lore}" in filled_prompt:
                filled_prompt = filled_prompt.replace(
                    "{lore}", st.session_state.knowledge_base
                )

            # Show the filled prompt
            st.text_area(
                "Filled Prompt", value=filled_prompt, height=300, disabled=True
            )

    # Advanced output generation options
    with st.expander("Advanced Output Generation Options", expanded=False):
        st.info("Configure options for generating multiple outputs per input")

        # Option to generate multiple outputs for some inputs
        enable_multiple_outputs = st.checkbox(
            "Generate multiple outputs for some inputs",
            help="Enable generating multiple variations of outputs for selected inputs",
            key="enable_multiple_outputs_checkbox",
        )

        if enable_multiple_outputs:
            # Proportion of inputs to duplicate
            duplicate_proportion = st.slider(
                "Proportion of inputs to generate multiple outputs for",
                min_value=0.0,
                max_value=1.0,
                value=0.2,
                step=0.1,
                help="What fraction of the input samples should have multiple outputs",
            )

            # Number of outputs per duplicated input
            outputs_per_input = st.number_input(
                "Number of outputs per selected input",
                min_value=2,
                max_value=5,
                value=2,
                help="How many different outputs to generate for each selected input",
            )

            # Preview the effect
            if st.session_state.selected_samples:
                num_selected = len(st.session_state.selected_samples)
                num_to_duplicate = math.ceil(num_selected * duplicate_proportion)
                total_outputs = (num_selected - num_to_duplicate) + (
                    num_to_duplicate * outputs_per_input
                )

                st.write(
                    f"This will result in approximately {total_outputs} total outputs:"
                )
                st.write(f"- {num_selected - num_to_duplicate} inputs with 1 output")
                st.write(
                    f"- {num_to_duplicate} inputs with {outputs_per_input} outputs each"
                )

    # Generate outputs button - using a unique key to avoid conflicts
    if st.button(
        "Generate Outputs for Selected Samples", key="generate_outputs_button"
    ):
        if not st.session_state.get("api_key") and not st.session_state.get(
            "anthropic_api_key"
        ):
            st.error("Please provide an OpenAI or Anthropic API key in the sidebar.")
        elif not st.session_state.selected_samples:
            st.error("No samples selected for output generation.")
        else:
            # Create a copy of the template spec with the modified prompt
            modified_template = st.session_state.template_spec.copy()
            modified_template["prompt"] = st.session_state.modified_prompt_template

            # Get only the selected samples
            selected_inputs = [
                st.session_state.synthetic_inputs[i]
                for i in st.session_state.selected_samples
            ]

            # Handle multiple outputs if enabled
            if (
                "enable_multiple_outputs_checkbox" in st.session_state
                and st.session_state.enable_multiple_outputs_checkbox
            ):
                # Calculate how many inputs should have multiple outputs
                num_to_duplicate = math.ceil(
                    len(selected_inputs) * duplicate_proportion
                )

                # Randomly select inputs for multiple outputs
                duplicate_indices = random.sample(
                    range(len(selected_inputs)), num_to_duplicate
                )

                # Create the expanded input list
                expanded_inputs = []
                for i, input_data in enumerate(selected_inputs):
                    if i in duplicate_indices:
                        # Add multiple copies for selected inputs
                        expanded_inputs.extend([input_data] * outputs_per_input)
                    else:
                        # Add single copy for other inputs
                        expanded_inputs.append(input_data)

                # Update selected_inputs with the expanded list
                selected_inputs = expanded_inputs

            with st.spinner(
                f"Generating outputs for {len(selected_inputs)} samples..."
            ):
                generated_outputs = generate_synthetic_outputs(
                    modified_template,
                    selected_inputs,
                    st.session_state.knowledge_base,
                )

            if generated_outputs:
                # If we're generating for all samples, replace the combined data
                if selection_method == "Generate for all samples":
                    st.session_state.combined_data = generated_outputs
                else:
                    # For specific samples, we need to handle the case of multiple outputs
                    if (
                        "enable_multiple_outputs_checkbox" in st.session_state
                        and st.session_state.enable_multiple_outputs_checkbox
                    ):
                        # Simply use all generated outputs as the combined data
                        st.session_state.combined_data = generated_outputs
                    else:
                        # Handle single outputs as before
                        if not st.session_state.combined_data or len(
                            st.session_state.combined_data
                        ) != len(st.session_state.synthetic_inputs):
                            st.session_state.combined_data = [None] * len(
                                st.session_state.synthetic_inputs
                            )

                        # Update only the selected samples
                        for i, output_idx in enumerate(
                            st.session_state.selected_samples
                        ):
                            if i < len(generated_outputs):
                                st.session_state.combined_data[output_idx] = (
                                    generated_outputs[i]
                                )

                        # Remove any None values (samples that haven't been generated yet)
                        st.session_state.combined_data = [
                            item
                            for item in st.session_state.combined_data
                            if item is not None
                        ]

                st.success(f"Generated {len(generated_outputs)} outputs")


def render_combined_data_section():
    if st.session_state.combined_data:
        st.subheader("Complete Dataset (Inputs + Outputs)")

        # Toggle for showing JSON columns
        st.session_state.show_json_columns = st.checkbox(
            "Show input/output JSON columns",
            value=st.session_state.show_json_columns,
        )

        # Prepare dataframe with JSON columns
        full_df, display_df = prepare_dataframe_with_json_columns(
            st.session_state.combined_data,
            st.session_state.template_spec,
            st.session_state.show_json_columns,
        )

        # Show data in a table
        st.dataframe(display_df)

        # Compare with original table if available
        if "data_table" in st.session_state and st.session_state.data_table is not None:
            with st.expander("Compare with Original Table Data", expanded=False):
                df = st.session_state.data_table

                # Get output variables
                output_vars = [
                    var["name"] for var in st.session_state.template_spec["output"]
                ]

                # Find output variables that exist in both datasets
                common_outputs = [var for var in output_vars if var in df.columns]

                if common_outputs:
                    st.success(
                        f"Found {len(common_outputs)} output variables to compare"
                    )

                    # Select which output to compare
                    output_to_compare = st.selectbox(
                        "Select output to compare:", options=common_outputs
                    )

                    if output_to_compare:
                        # Create a comparison dataframe
                        # This is simplified and would need to be enhanced to match rows properly
                        comparison_df = pd.DataFrame()
                        comparison_df["Generated"] = [
                            row.get(output_to_compare, "")
                            for row in st.session_state.combined_data
                        ]

                        # For simplicity, we'll just use the first N rows from the original table
                        n = min(len(comparison_df), len(df))
                        comparison_df["Original"] = (
                            df[output_to_compare].head(n).tolist()
                        )

                        st.write("Comparison of generated vs. original outputs:")
                        st.dataframe(comparison_df)
                else:
                    st.warning("No common output variables found for comparison")

        # Download buttons for different formats
        col1, col2, col3 = st.columns(3)

        with col1:
            # CSV download
            combined_csv = full_df.to_csv(index=False)
            st.download_button(
                label="Download Dataset (CSV)",
                data=combined_csv,
                file_name="synthetic_dataset.csv",
                mime="text/csv",
            )

        with col2:
            # JSON download
            combined_json = json.dumps(st.session_state.combined_data, indent=2)
            st.download_button(
                label="Download Dataset (JSON)",
                data=combined_json,
                file_name="synthetic_dataset.json",
                mime="application/json",
            )

        with col3:
            # Parquet download
            try:
                # Create a BytesIO object to hold the Parquet file
                parquet_buffer = BytesIO()
                # Convert DataFrame to Parquet-compatible types
                parquet_df = prepare_dataframe_for_parquet(full_df)
                # Write the DataFrame to the BytesIO object in Parquet format
                parquet_df.to_parquet(parquet_buffer, index=False)
                # Reset the buffer's position to the beginning
                parquet_buffer.seek(0)

                st.download_button(
                    label="Download Dataset (Parquet)",
                    data=parquet_buffer,
                    file_name="synthetic_dataset.parquet",
                    mime="application/octet-stream",
                )
            except Exception as e:
                st.error(f"Error creating Parquet file: {str(e)}")
                st.info(
                    "To use Parquet format, install pyarrow with: pip install pyarrow"
                )
