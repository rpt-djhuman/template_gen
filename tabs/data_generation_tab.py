# tabs/data_generation_tab.py
import streamlit as st
import json
import pandas as pd
import math
import random
from io import BytesIO
from utils.llm_utils import generate_synthetic_inputs_hybrid, generate_synthetic_outputs
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
        render_generation_settings()

        # Categorical variable options
        render_categorical_options()

        # Generate inputs button and display
        render_input_generation_section()

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


def render_categorical_options():
    # ... rest of code remains same
    pass


def render_input_generation_section():
    # ... rest of code remains same
    pass


def render_output_generation_section():
    # ... rest of code remains same
    pass


def render_combined_data_section():
    # ... rest of code remains same
    pass
