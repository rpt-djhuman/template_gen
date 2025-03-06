import streamlit as st
import json
import PyPDF2
import re
from io import BytesIO
import openai
import pandas as pd

# Setup page config
st.set_page_config(
    page_title="Template Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize OpenAI client (you'll need to provide your API key)
def get_openai_client():
    api_key = st.session_state.get("api_key", "")
    if api_key:
        return openai.OpenAI(api_key=api_key)
    return None


# Define helper functions for PDF parsing
def parse_pdf(file):
    """Extract text from a PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page_num].extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Error parsing PDF: {str(e)}")
        return ""


def parse_documents(uploaded_files):
    """Parse multiple document files and extract their text content."""
    content = ""
    for file in uploaded_files:
        try:
            file_type = file.name.split(".")[-1].lower()
            if file_type == "pdf":
                # Create a copy of the file to avoid buffer issues
                file_copy = BytesIO(file.getvalue())
                content += parse_pdf(file_copy) + "\n\n"
            elif file_type == "txt":
                content += file.getvalue().decode("utf-8") + "\n\n"
            else:
                st.warning(f"Unsupported file type: {file.name}")
        except Exception as e:
            st.error(f"Error processing file {file.name}: {str(e)}")
    return content


# Add this function after parse_documents function
def parse_template_file(uploaded_template):
    """Parse an uploaded template JSON file and validate its structure."""
    try:
        # Read the file content
        if uploaded_template.name.endswith(".json"):
            template_content = uploaded_template.getvalue().decode("utf-8")
            template_spec = json.loads(template_content)

            # Validate the template structure
            required_keys = [
                "name",
                "version",
                "description",
                "input",
                "output",
                "prompt",
            ]
            for key in required_keys:
                if key not in template_spec:
                    return None, f"Invalid template: Missing '{key}' field"

            # Validate input and output arrays
            if not isinstance(template_spec["input"], list):
                return None, "Invalid template: 'input' must be an array"
            if not isinstance(template_spec["output"], list):
                return None, "Invalid template: 'output' must be an array"

            # Check that each input and output has required fields
            for i, input_var in enumerate(template_spec["input"]):
                if not all(k in input_var for k in ["name", "description", "type"]):
                    return (
                        None,
                        f"Invalid template: Input variable at index {i} is missing required fields",
                    )

            for i, output_var in enumerate(template_spec["output"]):
                if not all(k in output_var for k in ["name", "description", "type"]):
                    return (
                        None,
                        f"Invalid template: Output variable at index {i} is missing required fields",
                    )

            return template_spec, None
        else:
            return None, "Uploaded file must be a JSON file"
    except json.JSONDecodeError:
        return None, "Invalid JSON format in the uploaded template file"
    except Exception as e:
        return None, f"Error parsing template file: {str(e)}"


# LLM call function
def call_llm(prompt, model="gpt-3.5-turbo"):
    """Call the LLM API to generate text based on the prompt."""
    try:
        client = get_openai_client()
        if not client:
            st.error("Please provide an OpenAI API key in the sidebar.")
            return "Error: No API key provided."

        # Get output specifications from the template if available
        output_specs = ""
        if st.session_state.show_template_editor and st.session_state.template_spec:
            output_vars = st.session_state.template_spec.get("output", [])
            if output_vars:
                output_specs = (
                    "Please generate output with the following specifications:\n"
                )
                for var in output_vars:
                    output_specs += (
                        f"- {var['name']}: {var['description']} (Type: {var['type']})"
                    )
                    if var.get("options"):
                        output_specs += f", Options: {var['options']}"
                    output_specs += "\n"

                # Add the output specs to the prompt
                prompt = f"{prompt}\n\n{output_specs}"

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling LLM API: {str(e)}")
        return f"Error: {str(e)}"


# Function to generate a template based on instructions and documents
def generate_template_from_instructions(instructions, document_content=""):
    """
    Use LLM to generate a template specification based on user instructions
    and document content.
    """
    client = get_openai_client()
    if not client:
        st.error("Please provide an OpenAI API key to generate a template.")
        return create_fallback_template(instructions)

    # Prepare the prompt for the LLM
    prompt = f"""
You are a template designer for an LLM-powered content generation system.
Create a template specification based on the following instructions:

INSTRUCTIONS:
{instructions}

{"DOCUMENT CONTENT (EXCERPT):" + document_content[:2000] + "..." if document_content else "NO DOCUMENTS PROVIDED"}

Generate a JSON template specification with the following structure:
{{
  "name": "A descriptive name for the template",
  "version": "1.0.0",
  "description": "A brief description of what this template does",
  "input": [
    {{
      "name": "variable_name",
      "description": "What this variable represents",
      "type": "string/int/float/bool/categorical",
      "min": minimum_value_or_length,
      "max": maximum_value_or_length,
      "options": ["option1", "option2"] (only for categorical type)
    }},
    ... more input variables
  ],
  "output": [
    {{
      "name": "output_variable_name",
      "description": "What this output represents",
      "type": "string/int/float/bool/categorical"
    }},
    ... more output variables
  ],
  "prompt": "A template string with {{variable_name}} placeholders that will be replaced with actual values"
}}

Make sure the prompt includes all input variables and is designed to produce the expected outputs.
If a 'lore' or 'knowledge_base' should be incorporated, include {{lore}} in the prompt template.
If document content was provided, design the template to effectively use that information.
"""

    try:
        # Call the LLM to generate the template
        response = client.chat.completions.create(
            model=st.session_state.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7,
        )

        template_text = response.choices[0].message.content

        # Extract the JSON part from the response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*{[\s\S]*}\s*$"
        json_match = re.search(json_pattern, template_text)

        if json_match:
            json_str = json_match.group(1) if json_match.group(1) else template_text
            # Clean up any remaining markdown or comments
            json_str = re.sub(r"```.*|```", "", json_str).strip()
            template_spec = json.loads(json_str)
            return template_spec
        else:
            # If no JSON format found, try to parse the entire response
            try:
                template_spec = json.loads(template_text)
                return template_spec
            except:
                st.warning("LLM didn't return valid JSON. Using fallback template.")
                return create_fallback_template(instructions)

    except Exception as e:
        st.error(f"Error generating template: {str(e)}")
        return create_fallback_template(instructions)


# Add these functions after the generate_template_from_instructions function


def generate_improved_prompt_template(template_spec, knowledge_base=""):
    """
    Use LLM to generate an improved prompt template based on current template variables.
    """
    client = get_openai_client()
    if not client:
        st.error("Please provide an OpenAI API key to rewrite the prompt.")
        return template_spec["prompt"]

    # Extract template information for context
    input_vars = template_spec["input"]
    output_vars = template_spec["output"]
    template_description = template_spec["description"]

    # Format variable information for the prompt
    input_vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']})"
            + (f", Options: {var['options']}" if var.get("options") else "")
            for var in input_vars
        ]
    )

    output_vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']})"
            for var in output_vars
        ]
    )

    # Prepare the prompt for the LLM
    prompt = f"""
You are an expert at designing effective prompts for LLMs. Rewrite the prompt template based on the following details:

TEMPLATE PURPOSE:
{template_description}

INPUT VARIABLES:
{input_vars_text}

OUTPUT VARIABLES:
{output_vars_text}

{"KNOWLEDGE BASE AVAILABLE:" if knowledge_base else "NO KNOWLEDGE BASE AVAILABLE."}
{knowledge_base[:500] + "..." if len(knowledge_base) > 500 else knowledge_base if knowledge_base else ""}

Current prompt template:
{template_spec["prompt"]}

Please create an improved prompt template that:
1. Uses all input variables (in curly braces like {{variable_name}})
2. Is designed to generate the specified outputs
3. Includes {{lore}} where background information or context should be inserted
4. Is clear, specific, and well-structured
5. Provides enough guidance to the LLM to generate high-quality results

Return ONLY the revised prompt template text, with no additional explanations.
"""

    try:
        # Call the LLM to generate the improved prompt template
        response = client.chat.completions.create(
            model=st.session_state.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )

        improved_template = response.choices[0].message.content.strip()

        # Remove any markdown code block formatting if present
        improved_template = re.sub(r"```.*\n|```", "", improved_template)

        return improved_template
    except Exception as e:
        st.error(f"Error generating improved prompt: {str(e)}")
        return template_spec["prompt"]


# Fallback template if generation fails
def create_fallback_template(instructions=""):
    """Create a basic template to use as fallback."""
    return {
        "name": "Generated Template",
        "version": "1.0.0",
        "description": instructions,
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
        "prompt": "Based on the following information:\n{input_1}\n\nAnd considering this additional context:\n{lore}\n\nGenerate the following output.",
    }


def generate_synthetic_inputs(template_spec, num_samples=1, max_retries=3):
    """Generate synthetic input data based on template specifications with retry logic."""
    client = get_openai_client()
    if not client:
        st.error("Please provide an OpenAI API key to generate synthetic data.")
        return []

    input_vars = template_spec["input"]

    # Format variable information for the prompt
    input_vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']})"
            + (
                f", Min: {var.get('min', 'N/A')}, Max: {var.get('max', 'N/A')}"
                if var["type"] in ["string", "int", "float"]
                else ""
            )
            + (f", Options: {var['options']}" if var.get("options") else "")
            for var in input_vars
        ]
    )

    prompt = f"""
You are a synthetic data generator. Generate {num_samples} realistic sample(s) for the following input variables:

{input_vars_text}

Return the data as a JSON array of objects, where each object contains values for all input variables.
Each object should follow this structure:
{{
  "variable_name_1": value1,
  "variable_name_2": value2,
  ...
}}

Make sure to:
1. Use appropriate data types (strings, numbers, booleans)
2. Stay within min/max constraints
3. Only use provided options for categorical variables
4. Generate realistic and diverse values
5. Return ONLY the JSON array with no additional text or explanation
6. The response must be valid JSON that can be parsed directly
"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=st.session_state.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.8,
            )

            result = response.choices[0].message.content.strip()

            # Extract JSON from the response
            json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\[[\s\S]*\]\s*$"
            json_match = re.search(json_pattern, result)

            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else result
                # Clean up any remaining markdown or comments
                json_str = re.sub(r"```.*|```", "", json_str).strip()
                try:
                    synthetic_inputs = json.loads(json_str)
                    # Validate that we got a list of dictionaries
                    if isinstance(synthetic_inputs, list) and all(
                        isinstance(item, dict) for item in synthetic_inputs
                    ):
                        return synthetic_inputs
                    else:
                        st.warning(
                            f"Attempt {attempt+1}: Generated data is not in the expected format. Retrying..."
                        )
                        continue
                except json.JSONDecodeError:
                    st.warning(
                        f"Attempt {attempt+1}: Failed to parse JSON. Retrying..."
                    )
                    continue
            else:
                # Try to parse the entire response as JSON
                try:
                    synthetic_inputs = json.loads(result)
                    # Validate that we got a list of dictionaries
                    if isinstance(synthetic_inputs, list) and all(
                        isinstance(item, dict) for item in synthetic_inputs
                    ):
                        return synthetic_inputs
                    else:
                        st.warning(
                            f"Attempt {attempt+1}: Generated data is not in the expected format. Retrying..."
                        )
                        continue
                except json.JSONDecodeError:
                    st.warning(
                        f"Attempt {attempt+1}: Failed to parse JSON. Retrying..."
                    )
                    continue

        except Exception as e:
            st.warning(
                f"Attempt {attempt+1}: Error generating synthetic inputs: {str(e)}. Retrying..."
            )
            if attempt == max_retries - 1:
                st.error(
                    f"Failed to generate synthetic inputs after {max_retries} attempts: {str(e)}"
                )
                return []

    st.error(f"Failed to generate valid synthetic inputs after {max_retries} attempts.")
    return []


def generate_synthetic_outputs(
    template_spec, input_data, knowledge_base="", max_retries=3
):
    """Generate synthetic output data based on template and input data with retry logic."""
    client = get_openai_client()
    if not client:
        st.error("Please provide an OpenAI API key to generate synthetic outputs.")
        return []

    output_vars = template_spec["output"]
    prompt_template = template_spec["prompt"]

    # Format output variable information for the prompt
    output_vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']}) {'Options: '+str(var['options']) if var.get('options') else ''}"
            for var in output_vars
        ]
    )

    results = []

    # Create a progress bar
    progress_bar = st.progress(0)

    try:
        for i, input_item in enumerate(input_data):
            # Fill the prompt template with input values
            filled_prompt = prompt_template
            for var_name, var_value in input_item.items():
                filled_prompt = filled_prompt.replace(f"{{{var_name}}}", str(var_value))

            # Replace {lore} with knowledge base if present
            if "{lore}" in filled_prompt:
                filled_prompt = filled_prompt.replace("{lore}", knowledge_base)

            # Create a prompt for generating synthetic output
            generation_prompt = f"""
You are generating synthetic output data based on the following input:

INPUT DATA:
{json.dumps(input_item, indent=2)}

PROMPT USED:
{filled_prompt}

REQUIRED OUTPUT VARIABLES:
{output_vars_text}

Generate realistic output data for these variables. Return ONLY a JSON object with the output variables:
{{
  "output_variable_1": value1,
  "output_variable_2": value2,
  ...
}}

Use appropriate data types for each variable. Return ONLY the JSON object with no additional text or explanation.
The response must be valid JSON that can be parsed directly.
"""

            output_data = None
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=st.session_state.model,
                        messages=[{"role": "user", "content": generation_prompt}],
                        max_tokens=2000,
                        temperature=0.7,
                    )

                    result = response.choices[0].message.content.strip()

                    # Extract JSON from the response
                    json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
                    json_match = re.search(json_pattern, result)

                    if json_match:
                        json_str = (
                            json_match.group(1) if json_match.group(1) else result
                        )
                        # Clean up any remaining markdown or comments
                        json_str = re.sub(r"```.*|```", "", json_str).strip()
                        try:
                            output_data = json.loads(json_str)
                            # Validate that we got a dictionary
                            if isinstance(output_data, dict):
                                # Check if all required output variables are present
                                required_vars = [var["name"] for var in output_vars]
                                if all(var in output_data for var in required_vars):
                                    break  # Valid output, exit retry loop
                                else:
                                    missing_vars = [
                                        var
                                        for var in required_vars
                                        if var not in output_data
                                    ]
                                    st.warning(
                                        f"Attempt {attempt+1} for input {i+1}: Missing output variables: {missing_vars}. Retrying..."
                                    )
                            else:
                                st.warning(
                                    f"Attempt {attempt+1} for input {i+1}: Generated output is not a dictionary. Retrying..."
                                )
                        except json.JSONDecodeError:
                            st.warning(
                                f"Attempt {attempt+1} for input {i+1}: Failed to parse JSON. Retrying..."
                            )
                    else:
                        # Try to parse the entire response as JSON
                        try:
                            output_data = json.loads(result)
                            # Validate that we got a dictionary
                            if isinstance(output_data, dict):
                                # Check if all required output variables are present
                                required_vars = [var["name"] for var in output_vars]
                                if all(var in output_data for var in required_vars):
                                    break  # Valid output, exit retry loop
                                else:
                                    missing_vars = [
                                        var
                                        for var in required_vars
                                        if var not in output_data
                                    ]
                                    st.warning(
                                        f"Attempt {attempt+1} for input {i+1}: Missing output variables: {missing_vars}. Retrying..."
                                    )
                            else:
                                st.warning(
                                    f"Attempt {attempt+1} for input {i+1}: Generated output is not a dictionary. Retrying..."
                                )
                        except json.JSONDecodeError:
                            st.warning(
                                f"Attempt {attempt+1} for input {i+1}: Failed to parse JSON. Retrying..."
                            )

                except Exception as e:
                    st.warning(
                        f"Attempt {attempt+1} for input {i+1}: Error generating output: {str(e)}. Retrying..."
                    )

                # If we've reached the max retries, log the error
                if attempt == max_retries - 1:
                    st.error(
                        f"Failed to generate valid output for input {i+1} after {max_retries} attempts."
                    )
                    output_data = {
                        "error": f"Failed to generate valid output after {max_retries} attempts"
                    }

            # Combine input and output data
            if output_data:
                combined_data = {**input_item, **output_data}
                results.append(combined_data)
            else:
                results.append({**input_item, "error": "Failed to generate output"})

            # Update progress bar
            progress_bar.progress((i + 1) / len(input_data))

    finally:
        # Ensure progress bar reaches 100% when done
        if len(input_data) > 0:
            progress_bar.progress(1.0)

    return results


# Initialize session state
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

# Sidebar setup
with st.sidebar:
    st.title("Template Generator")
    st.write("Create templates for generating content with LLMs.")

    # API Key input
    api_key = st.text_input("OpenAI API Key", type="password")
    if api_key:
        st.session_state.api_key = api_key

    # Model selection
    st.session_state.model = st.selectbox(
        "Select LLM Model",
        options=["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        index=0,
    )

# Main application layout
st.title("Template Generator")

# Create tabs for workflow
tab1, tab2, tab3, tab4 = st.tabs(
    ["Setup", "Edit Template", "Use Template", "Generate Data"]
)

with tab1:
    st.header("Project Setup")

    # Add option to either upload a template or create a new one
    setup_option = st.radio(
        "Choose how to start your project",
        options=["Upload existing template", "Create new template from documents"],
        index=1,
    )

    if setup_option == "Upload existing template":
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
                with st.expander("Template Preview", expanded=True):
                    st.json(template_spec)

                # Button to use this template
                if st.button("Use This Template"):
                    st.session_state.template_spec = template_spec
                    st.session_state.show_template_editor = True
                    st.success(
                        "Template loaded! Go to the 'Edit Template' tab to customize it."
                    )

    if (
        setup_option == "Create new template from documents"
        or setup_option == "Upload existing template"
        and not uploaded_template
    ):
        # Step 1: Upload Knowledge Base (existing code)
        st.subheader("Step 1: Upload Knowledge Base")
        uploaded_files = st.file_uploader(
            "Upload documents to use as knowledge base",
            accept_multiple_files=True,
            type=["pdf", "txt"],
        )

        # Rest of your existing code for document processing...
        if uploaded_files:
            # Track filenames for UI feedback
            st.session_state.uploaded_filenames = [file.name for file in uploaded_files]

            with st.spinner("Processing documents..."):
                st.session_state.knowledge_base = parse_documents(uploaded_files)
            st.success(f"Processed {len(uploaded_files)} documents")

            with st.expander("Preview extracted content"):
                st.text_area(
                    "Extracted Text",
                    value=st.session_state.knowledge_base[:10000]
                    + ("..." if len(st.session_state.knowledge_base) > 1000 else ""),
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
            if not st.session_state.get("api_key"):
                st.error(
                    "Please provide an OpenAI API key in the sidebar before generating a template."
                )
            elif instructions:
                with st.spinner("Analyzing instructions and generating template..."):
                    # Generate template based on instructions and document content
                    st.session_state.template_spec = (
                        generate_template_from_instructions(
                            instructions, st.session_state.knowledge_base
                        )
                    )
                    st.session_state.show_template_editor = True
                st.success(
                    "Template generated! Go to the 'Edit Template' tab to customize it."
                )
            else:
                st.warning("Please provide instructions first")

with tab2:
    if st.session_state.show_template_editor and st.session_state.template_spec:
        st.header("Template Editor")

        # Basic template information
        with st.expander("Template Information", expanded=True):
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
                        st.session_state.template_spec, st.session_state.knowledge_base
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

        # Input Variables Editor
        with st.expander("Input Variables", expanded=True):
            st.subheader("Input Variables")

            # Add input variable button
            if st.button("Add Input Variable"):
                new_var = {
                    "name": f"new_input_{len(st.session_state.template_spec['input']) + 1}",
                    "description": "New input variable",
                    "type": "string",
                    "min": 0,
                    "max": 100,
                }
                st.session_state.template_spec["input"].append(new_var)
                st.rerun()

            # Display input variables
            for i, input_var in enumerate(st.session_state.template_spec["input"]):
                with st.container():
                    st.markdown(f"##### {input_var['name']}")

                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        input_var["name"] = st.text_input(
                            "Name", value=input_var["name"], key=f"input_name_{i}"
                        )

                        input_var["description"] = st.text_input(
                            "Description",
                            value=input_var["description"],
                            key=f"input_desc_{i}",
                        )

                    with col2:
                        var_type = st.selectbox(
                            "Type",
                            options=["string", "int", "float", "bool", "categorical"],
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

                        if var_type in ["string", "int", "float"]:
                            col_min, col_max = st.columns(2)
                            with col_min:
                                input_var["min"] = st.number_input(
                                    "Min",
                                    value=int(input_var.get("min", 0)),
                                    key=f"input_min_{i}",
                                )
                            with col_max:
                                input_var["max"] = st.number_input(
                                    "Max",
                                    value=int(input_var.get("max", 100)),
                                    key=f"input_max_{i}",
                                )

                        if var_type == "categorical":
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

                            # Add min and max for categorical variables
                            col_min, col_max = st.columns(2)
                            with col_min:
                                input_var["min"] = st.number_input(
                                    "Min selections",
                                    value=int(input_var.get("min", 1)),
                                    min_value=1,
                                    key=f"input_cat_min_{i}",
                                )
                            with col_max:
                                input_var["max"] = st.number_input(
                                    "Max selections",
                                    value=int(input_var.get("max", 1)),
                                    min_value=1,
                                    key=f"input_cat_max_{i}",
                                )

                    with col3:
                        if st.button("Remove", key=f"remove_input_{i}"):
                            st.session_state.template_spec["input"].pop(i)
                            st.rerun()

                    st.divider()

        # Output Variables Editor
        with st.expander("Output Variables", expanded=True):
            st.subheader("Output Variables")

            # Add output variable button
            if st.button("Add Output Variable"):
                new_var = {
                    "name": f"new_output_{len(st.session_state.template_spec['output']) + 1}",
                    "description": "New output variable",
                    "type": "string",
                    "min": 0,
                    "max": 100,
                }
                st.session_state.template_spec["output"].append(new_var)
                st.rerun()

            # Display output variables
            for i, output_var in enumerate(st.session_state.template_spec["output"]):
                with st.container():
                    st.markdown(f"##### {output_var['name']}")

                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        output_var["name"] = st.text_input(
                            "Name", value=output_var["name"], key=f"output_name_{i}"
                        )

                        output_var["description"] = st.text_input(
                            "Description",
                            value=output_var["description"],
                            key=f"output_desc_{i}",
                        )

                    with col2:
                        var_type = st.selectbox(
                            "Type",
                            options=["string", "int", "float", "bool", "categorical"],
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

                        if var_type in ["string", "int", "float"]:
                            col_min, col_max = st.columns(2)
                            with col_min:
                                output_var["min"] = st.number_input(
                                    "Min",
                                    value=int(output_var.get("min", 0)),
                                    key=f"output_min_{i}",
                                )
                            with col_max:
                                output_var["max"] = st.number_input(
                                    "Max",
                                    value=int(output_var.get("max", 100)),
                                    key=f"output_max_{i}",
                                )

                        if var_type == "categorical":
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

                    with col3:
                        if st.button("Remove", key=f"remove_output_{i}"):
                            st.session_state.template_spec["output"].pop(i)
                            st.rerun()

                    st.divider()

        # Template Specification and Download Section
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
    else:
        st.info(
            "No template has been generated yet. Go to the 'Setup' tab to create one."
        )

with tab3:
    if st.session_state.show_template_editor and st.session_state.template_spec:
        st.header("Use Template")

        # Reset user inputs when template changes
        if (
            "last_template" not in st.session_state
            or st.session_state.last_template != st.session_state.template_spec
        ):
            st.session_state.user_inputs = {}
            st.session_state.last_template = st.session_state.template_spec

        # Create input fields based on the template specification
        for input_var in st.session_state.template_spec["input"]:
            var_name = input_var["name"]
            var_type = input_var["type"]
            var_desc = input_var["description"]

            st.markdown(f"##### {var_desc}")

            if var_type == "string":
                st.session_state.user_inputs[var_name] = st.text_input(
                    f"Enter value for {var_name}", key=f"use_{var_name}"
                )

            elif var_type == "int":
                st.session_state.user_inputs[var_name] = st.number_input(
                    f"Enter value for {var_name}",
                    min_value=input_var.get("min", None),
                    max_value=input_var.get("max", None),
                    step=1,
                    key=f"use_{var_name}",
                )

            elif var_type == "float":
                st.session_state.user_inputs[var_name] = st.number_input(
                    f"Enter value for {var_name}",
                    min_value=float(input_var.get("min", 0)),
                    max_value=float(input_var.get("max", 100)),
                    key=f"use_{var_name}",
                )

            elif var_type == "bool":
                st.session_state.user_inputs[var_name] = st.checkbox(
                    f"Select value for {var_name}", key=f"use_{var_name}"
                )

            elif var_type == "categorical":
                options = input_var.get("options", [])
                if options:
                    st.session_state.user_inputs[var_name] = st.selectbox(
                        f"Select value for {var_name}",
                        options=options,
                        key=f"use_{var_name}",
                    )
                else:
                    st.warning(f"No options defined for {var_name}")

        # Handle the lore/knowledge base as a special variable
        prompt_template = st.session_state.template_spec["prompt"]
        if "{lore}" in prompt_template:
            st.markdown("##### Document Knowledge Base")

            # Display info about the knowledge base
            if st.session_state.knowledge_base:
                st.success(
                    f"Using content from {len(st.session_state.uploaded_filenames) if 'uploaded_filenames' in st.session_state else 'uploaded'} documents as knowledge base"
                )

                with st.expander("View knowledge base content"):
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

        # Generate Output button
        if st.button("Generate Output", key="generate_button"):
            # Check if API key is provided
            if not st.session_state.get("api_key"):
                st.error(
                    "Please provide an OpenAI API key in the sidebar before generating output."
                )
            else:
                # Fill the prompt template with user-provided values
                filled_prompt = prompt_template
                for var_name, var_value in st.session_state.user_inputs.items():
                    filled_prompt = filled_prompt.replace(
                        f"{{{var_name}}}", str(var_value)
                    )

                # Show the filled prompt
                with st.expander("View populated prompt"):
                    st.text_area(
                        "Prompt sent to LLM",
                        value=filled_prompt,
                        height=200,
                        disabled=True,
                    )

                # Call LLM with the filled prompt
                with st.spinner("Generating output..."):
                    model_selected = st.session_state.model
                    generated_output = call_llm(filled_prompt, model=model_selected)
                    st.session_state.generated_output = generated_output

        # Display generated output
        if st.session_state.generated_output:
            st.header("Generated Output")
            st.markdown("### Result")
            st.write(st.session_state.generated_output)

            # Option to save the output
            st.download_button(
                label="Download Output",
                data=st.session_state.generated_output,
                file_name="generated_output.txt",
                mime="text/plain",
            )
    else:
        st.info(
            "No template has been generated yet. Go to the 'Setup' tab to create one."
        )

with tab4:
    if st.session_state.show_template_editor and st.session_state.template_spec:
        st.header("Generate Synthetic Data")

        with st.expander("Template Information", expanded=False):
            st.json(st.session_state.template_spec)

        # Data generation controls
        st.subheader("Generation Settings")

        col1, col2 = st.columns(2)
        with col1:
            num_samples = st.number_input(
                "Number of samples to generate", min_value=1, max_value=100, value=5
            )
        with col2:
            temperature = st.slider(
                "Temperature (creativity)",
                min_value=0.1,
                max_value=1.0,
                value=0.7,
                step=0.1,
            )
            st.session_state.temperature = temperature

        # Initialize containers for generated data
        if "synthetic_inputs" not in st.session_state:
            st.session_state.synthetic_inputs = []
        if "synthetic_outputs" not in st.session_state:
            st.session_state.synthetic_outputs = []
        if "combined_data" not in st.session_state:
            st.session_state.combined_data = []

        # Generate inputs button
        if st.button("Generate Synthetic Inputs"):
            if not st.session_state.get("api_key"):
                st.error("Please provide an OpenAI API key in the sidebar.")
            else:
                with st.spinner(f"Generating {num_samples} synthetic input samples..."):
                    st.session_state.synthetic_inputs = generate_synthetic_inputs(
                        st.session_state.template_spec, num_samples=num_samples
                    )

                if st.session_state.synthetic_inputs:
                    st.success(
                        f"Generated {len(st.session_state.synthetic_inputs)} input samples"
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

            # Generate outputs button
            if st.button("Generate Outputs for These Inputs"):
                if not st.session_state.get("api_key"):
                    st.error("Please provide an OpenAI API key in the sidebar.")
                else:
                    with st.spinner("Generating outputs for each input..."):
                        st.session_state.combined_data = generate_synthetic_outputs(
                            st.session_state.template_spec,
                            st.session_state.synthetic_inputs,
                            st.session_state.knowledge_base,
                        )

                    if st.session_state.combined_data:
                        st.success(
                            f"Generated outputs for {len(st.session_state.combined_data)} inputs"
                        )

        # Display combined data if available
        if st.session_state.combined_data:
            st.subheader("Complete Dataset (Inputs + Outputs)")

            # Show data in a table
            combined_df = pd.DataFrame(st.session_state.combined_data)
            st.dataframe(combined_df)

            # Download buttons for different formats
            col1, col2 = st.columns(2)

            with col1:
                # CSV download
                combined_csv = combined_df.to_csv(index=False)
                st.download_button(
                    label="Download Complete Dataset (CSV)",
                    data=combined_csv,
                    file_name="synthetic_dataset.csv",
                    mime="text/csv",
                )

            with col2:
                # JSON download
                combined_json = json.dumps(st.session_state.combined_data, indent=2)
                st.download_button(
                    label="Download Complete Dataset (JSON)",
                    data=combined_json,
                    file_name="synthetic_dataset.json",
                    mime="application/json",
                )
    else:
        st.info(
            "No template has been generated yet. Go to the 'Setup' tab to create one."
        )
