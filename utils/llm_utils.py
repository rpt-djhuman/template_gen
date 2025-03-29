# utils/llm_utils.py
import openai
import anthropic
import json
import re
import random
import itertools
import streamlit as st
from tqdm import tqdm


def get_openai_client():
    api_key = st.session_state.get("api_key", "")
    if api_key:
        return openai.OpenAI(api_key=api_key)
    return None


def get_anthropic_client():
    api_key = st.session_state.get("anthropic_api_key", "")
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    return None


def call_model_api(prompt, model, temperature=0.7, max_tokens=1000):
    """
    Abstraction function to call the appropriate LLM API based on the model name.

    Args:
        prompt (str): The prompt to send to the model
        model (str): The model name (e.g., "gpt-4", "claude-3-opus-latest")
        temperature (float): Creativity parameter (0.0 to 1.0)
        max_tokens (int): Maximum number of tokens to generate

    Returns:
        str: The generated text response
    """
    # Check if it's a Claude model
    if model.startswith("claude"):
        client = get_anthropic_client()
        if not client:
            return "Error: No Anthropic API key provided."

        try:
            response = client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.content[0].text
        except Exception as e:
            return f"Error calling Anthropic API: {str(e)}"

    # Otherwise, use OpenAI
    else:
        client = get_openai_client()
        if not client:
            return "Error: No OpenAI API key provided."

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI API: {str(e)}"


def call_llm(prompt, model="gpt-3.5-turbo"):
    """Call the LLM API to generate text based on the prompt."""
    try:
        # Get output specifications from the template if available
        output_specs = ""
        if st.session_state.show_template_editor and st.session_state.template_spec:
            output_vars = st.session_state.template_spec.get("output", [])
            if output_vars:
                output_specs = "Please generate output with the following specifications in JSON format:\n"
                for var in output_vars:
                    output_specs += (
                        f"- {var['name']}: {var['description']} (Type: {var['type']})"
                    )
                    if var.get("options"):
                        output_specs += f", Options: {var['options']}"
                    output_specs += "\n"

                # Add the output specs to the prompt
                prompt = f"{prompt}\n\n{output_specs}\n\nReturn ONLY a JSON object with the output variables, with no additional text or explanation."

        result = call_model_api(
            model=model,
            prompt=prompt,
            max_tokens=1000,
            temperature=st.session_state.get("temperature", 0.7),
        )

        # Try to parse as JSON if the template has output variables
        if (
            st.session_state.show_template_editor
            and st.session_state.template_spec
            and st.session_state.template_spec.get("output")
        ):
            # Extract JSON from the response
            json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
            json_match = re.search(json_pattern, result)

            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else result
                # Clean up any remaining markdown or comments
                json_str = re.sub(r"```.*|```", "", json_str).strip()
                try:
                    output_data = json.loads(json_str)
                    # Store the parsed JSON in session state for proper rendering
                    st.session_state.json_output = output_data
                    return output_data
                except:
                    pass
            else:
                try:
                    output_data = json.loads(result)
                    # Store the parsed JSON in session state for proper rendering
                    st.session_state.json_output = output_data
                    return output_data
                except:
                    pass

        # If we couldn't parse as JSON or it's not meant to be JSON, return as is
        return result
    except Exception as e:
        st.error(f"Error calling LLM API: {str(e)}")
        return f"Error: {str(e)}"


def generate_template_from_instructions(instructions, document_content=""):
    """
    Use LLM to generate a template specification based on user instructions
    and document content.
    """

    # Prepare the prompt for the LLM
    prompt = f"""
You are a template designer for an LLM-powered content generation system.
Create a template specification based on the following instructions:

INSTRUCTIONS:
{instructions}

{"DOCUMENT CONTENT (EXCERPT):" + document_content + "..." if document_content else "NO DOCUMENTS PROVIDED"}

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
The prompt should address an LLM as if it was a combination of a system prompt and user input, and must contain information around formatting,
structure and context for the LLM to generate the desired content as derived from these instructions and/or documents.
If a 'lore' or 'knowledge_base' should be incorporated, include {{lore}} in the prompt template.
If document content was provided, design the template to effectively use that information.
"""

    try:
        # Call the LLM to generate the template
        template_text = call_model_api(
            model=st.session_state.model,
            prompt=prompt,
            max_tokens=4096,
            temperature=0.7,
        )

        # Extract the JSON part from the response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*{[\s\S]*}\s*$"
        json_match = re.search(json_pattern, template_text)

        if json_match:
            json_str = json_match.group(1) if json_match.group(1) else template_text
            # Clean up any remaining markdown or comments
            json_str = re.sub(r"```.*|```", "", json_str).strip()
            template_spec = json.loads(json_str, strict=False)
            return template_spec
        else:
            # If no JSON format found, try to parse the entire response
            try:
                template_spec = json.loads(template_text, strict=False)
                return template_spec
            except:
                st.warning("LLM didn't return valid JSON. Using fallback template.")
                return create_fallback_template(instructions)

    except Exception as e:
        st.error(f"Error generating template: {str(e)}")
        return create_fallback_template(instructions)


def generate_improved_prompt_template(template_spec, knowledge_base=""):
    """
    Use LLM to generate an improved prompt template based on current template variables.
    """
    if not st.session_state.get("api_key") and not st.session_state.get(
        "anthropic_api_key"
    ):
        st.error("Please provide an OpenAI or Anthropic API key to rewrite the prompt.")
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
{knowledge_base if knowledge_base else ""}

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
        improved_template = call_model_api(
            model=st.session_state.model,
            prompt=prompt,
            max_tokens=4096,
            temperature=0.7,
        )

        # Remove any markdown code block formatting if present
        improved_template = re.sub(r"```.*\n|```", "", improved_template)

        return improved_template
    except Exception as e:
        st.error(f"Error generating improved prompt: {str(e)}")
        return template_spec["prompt"]


def generate_synthetic_inputs_hybrid(template_spec, num_samples=10, max_retries=3):
    """
    Generate synthetic input data using a hybrid approach:
    - Programmatically generate combinations of categorical variables
    - Use LLM to fill in non-categorical variables
    - Process row by row for resilience
    """
    if not st.session_state.get("api_key") and not st.session_state.get(
        "anthropic_api_key"
    ):
        st.error("Please provide an OpenAI API key to generate synthetic data.")
        return []

    # Extract all variables from the template
    input_vars = template_spec["input"]

    # Separate categorical and non-categorical variables
    categorical_vars = [
        var for var in input_vars if var["type"] == "categorical" and var.get("options")
    ]
    non_categorical_vars = [var for var in input_vars if var not in categorical_vars]

    # Process in batches and show progress
    with st.spinner(f"Generating {num_samples} synthetic inputs..."):
        progress_bar = st.progress(0)
        results = []

        # If we have categorical variables, use them to create base permutations
        if categorical_vars:
            st.info(
                f"Generating permutations for {len(categorical_vars)} categorical variables"
            )
            # Create permutations of categorical values
            permutations = generate_categorical_permutations(
                categorical_vars, num_samples
            )

            # For each permutation, fill in non-categorical variables
            for i, perm in enumerate(permutations):
                # Update progress
                progress_bar.progress(min((i + 1) / len(permutations), 1.0))

                # Create a complete row by adding non-categorical values
                row = perm.copy()
                if non_categorical_vars:
                    non_cat_values = generate_non_categorical_values(
                        non_categorical_vars, perm, max_retries
                    )
                    row.update(non_cat_values)

                results.append(row)

                # Stop if we have enough samples
                if len(results) >= num_samples:
                    break
        else:
            # No categorical variables, generate each row individually
            for i in range(num_samples):
                # Update progress
                progress_bar.progress(min((i + 1) / num_samples, 1.0))

                # Generate a complete row of values
                row = generate_single_row(input_vars, max_retries)
                if row:
                    results.append(row)

        # Ensure we have the requested number of samples
        while len(results) < num_samples:
            # Generate additional rows if needed
            row = generate_single_row(input_vars, max_retries)
            if row:
                results.append(row)

        # Ensure progress bar completes
        progress_bar.progress(1.0)

    return results[:num_samples]


def generate_synthetic_outputs(
    template_spec, input_data, knowledge_base="", max_retries=3
):
    """Generate synthetic output data based on template and input data with retry logic."""

    output_vars = template_spec["output"]
    prompt_template = template_spec["prompt"]

    # Format output variable information for the prompt
    output_vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']}) {'Options: '+str(var['options']) if var.get('options') else ''}"
            for var in output_vars
        ]
    )

    input_vars = template_spec["input"]
    input_vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']}) {'Options: '+str(var['options']) if var.get('options') else ''}"
            for var in input_vars
        ]
    )

    output_format = "{"
    for var in output_vars:
        output_format += f'"{var["name"]}": output, '
    output_format = output_format.rstrip(", ") + "}"

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

DEFINITION OF INPUT VARIABLES:
{input_vars_text}

INPUT DATA:
{json.dumps(input_item, indent=2)}

PROMPT USED:
{filled_prompt}

REQUIRED OUTPUT VARIABLES:
{output_vars_text}

Generate realistic output data for these variables. Return ONLY a JSON object with the below format, using the names of the required output variables as keys:
{output_format}

Use appropriate data types for each variable. Return ONLY the JSON object with no additional text or explanation.
The response must be valid JSON that can be parsed directly.
"""

            output_data = None
            for attempt in range(max_retries):
                try:
                    response = call_model_api(
                        model=st.session_state.model,
                        prompt=generation_prompt,
                        max_tokens=2000,
                        temperature=st.session_state.temperature,
                    )

                    result = response.strip()

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
                            output_data = json.loads(json_str, strict=False)
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
                            output_data = json.loads(result, strict=False)
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


def generate_categorical_permutations(categorical_vars, target_count):
    """Generate efficient permutations of categorical variables."""
    # Build option sets for each categorical variable
    option_sets = []

    for var in categorical_vars:
        var_name = var["name"]
        options = var.get("options", [])
        min_sel = var.get("min", 1)
        max_sel = var.get("max", 1)

        # Get selected options if they exist
        selected_options = var.get("selected_options", options)

        # Use only selected options for permutation
        options_to_use = [opt for opt in options if opt in selected_options]

        # If no options selected, use all options
        if not options_to_use:
            options_to_use = options

        # Single selection case
        if min_sel == 1 and max_sel == 1:
            option_sets.append([(var_name, opt) for opt in options_to_use])
        else:
            # Multi-selection case - generate varied selection sizes
            var_options = []

            # Include min selections
            for combo in itertools.combinations(options_to_use, min_sel):
                var_options.append((var_name, list(combo)))

            # Include max selections if different from min
            if max_sel != min_sel:
                for combo in itertools.combinations(options_to_use, max_sel):
                    var_options.append((var_name, list(combo)))

            # Include some intermediate selections if applicable
            for size in range(min_sel + 1, max_sel):
                combos = list(itertools.combinations(options_to_use, size))
                if combos:
                    sample_size = min(3, len(combos))  # Take up to 3 samples
                    for combo in random.sample(combos, sample_size):
                        var_options.append((var_name, list(combo)))

            option_sets.append(var_options)

    # Generate permutations
    all_permutations = []
    for combo in itertools.product(*option_sets):
        perm = {name: value for name, value in combo}
        all_permutations.append(perm)

    # If we have too many permutations, sample a diverse subset
    if len(all_permutations) > target_count:
        return random.sample(all_permutations, target_count)

    # If we don't have enough, duplicate with variations
    while len(all_permutations) < target_count:
        # Clone an existing permutation
        new_perm = random.choice(all_permutations).copy()

        # Modify a random categorical value if possible
        if categorical_vars:
            var = random.choice(categorical_vars)
            var_name = var["name"]
            options = var.get("options", [])
            selected_options = var.get("selected_options", options)

            # Use only selected options for variation
            options_to_use = [opt for opt in options if opt in selected_options]
            if not options_to_use:
                options_to_use = options

            if options_to_use and len(options_to_use) > 1:
                if var.get("min", 1) == 1 and var.get("max", 1) == 1:
                    # For single selection, choose a different option
                    current = new_perm[var_name]
                    other_options = [opt for opt in options_to_use if opt != current]
                    if other_options:
                        new_perm[var_name] = random.choice(other_options)
                else:
                    # For multi-selection, modify the selection
                    current_selection = new_perm[var_name]
                    min_sel = var.get("min", 1)
                    max_sel = var.get("max", 1)

                    # Decide whether to add or remove an item
                    if len(current_selection) < max_sel and random.random() > 0.5:
                        # Add an item not already in the selection
                        available = [
                            opt
                            for opt in options_to_use
                            if opt not in current_selection
                        ]
                        if available:
                            current_selection.append(random.choice(available))
                    elif len(current_selection) > min_sel:
                        # Remove a random item
                        idx_to_remove = random.randrange(len(current_selection))
                        current_selection.pop(idx_to_remove)

        all_permutations.append(new_perm)

    return all_permutations


def generate_non_categorical_values(non_cat_vars, existing_values, max_retries):
    """Generate values for non-categorical variables given existing categorical values."""
    if not non_cat_vars:
        return {}

    # Format the variables for the prompt
    vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']})"
            + (
                f", Min: {var.get('min', 'N/A')}, Max: {var.get('max', 'N/A')}"
                if var["type"] in ["string", "int", "float"]
                else ""
            )
            for var in non_cat_vars
        ]
    )

    # Create prompt with existing categorical values as context
    prompt = f"""
    As a synthetic data generator, create values for these variables:

    {vars_text}

    These values should be coherent with the existing categorical values:
    {json.dumps(existing_values, indent=2)}

    Return ONLY a JSON object with the new variable values:
    {{
      "variable_name_1": value1,
      "variable_name_2": value2
    }}
    """

    for attempt in range(max_retries):
        try:
            response = call_model_api(
                model=st.session_state.model,
                prompt=prompt,
                max_tokens=1000,
                temperature=st.session_state.temperature,
            )

            result = response.strip()

            # Extract JSON
            json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
            json_match = re.search(json_pattern, result)

            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else result
                json_str = re.sub(r"```.*|```", "", json_str).strip()
                try:
                    values = json.loads(json_str, strict=False)
                    if isinstance(values, dict):
                        return values
                except:
                    pass
            else:
                try:
                    values = json.loads(result, strict=False)
                    if isinstance(values, dict):
                        return values
                except:
                    pass

        except Exception as e:
            if attempt == max_retries - 1:
                st.warning(f"Failed to generate non-categorical values: {str(e)}")

    # Fallback: generate empty values for all non-categorical variables
    return {var["name"]: get_default_value(var) for var in non_cat_vars}


def generate_single_row(all_vars, max_retries):
    """Generate a complete row of data for all variables."""
    # Format the variables for the prompt
    vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']})"
            + (
                f", Min: {var.get('min', 'N/A')}, Max: {var.get('max', 'N/A')}"
                if var["type"] in ["string", "int", "float", "categorical"]
                else ""
            )
            + (f", Options: {var['options']}" if var.get("options") else "")
            for var in all_vars
        ]
    )

    prompt = f"""
    You are a synthetic data generator. Generate 1 realistic sample with values for:

    {vars_text}

    Return ONLY a JSON object with all variable values:
    {{
      "variable_name_1": value1,
      "variable_name_2": value2
    }}

    For categorical variables with multiple selections, return an array of values.
    """

    for attempt in range(max_retries):
        try:
            response = call_model_api(
                model=st.session_state.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=st.session_state.temperature,
            )

            result = response.strip()

            # Extract JSON
            json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
            json_match = re.search(json_pattern, result)

            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else result
                json_str = re.sub(r"```.*|```", "", json_str).strip()
                try:
                    values = json.loads(json_str, strict=False)
                    if isinstance(values, dict):
                        return values
                except:
                    pass
            else:
                try:
                    values = json.loads(result, strict=False)
                    if isinstance(values, dict):
                        return values
                except:
                    pass

        except Exception as e:
            if attempt == max_retries - 1:
                st.warning(f"Failed to generate row: {str(e)}")

    # If all attempts fail, return None
    return None


def get_default_value(var):
    """Generate a default value for a variable based on its type."""
    var_type = var["type"]

    if var_type == "string":
        return "N/A"
    elif var_type == "int":
        min_val = var.get("min", 0)
        max_val = var.get("max", 100)
        return min_val
    elif var_type == "float":
        min_val = float(var.get("min", 0))
        max_val = float(var.get("max", 1))
        return min_val
    elif var_type == "bool":
        return False
    elif var_type == "categorical":
        options = var.get("options", [])
        min_sel = var.get("min", 1)

        if options:
            if min_sel == 1 and var.get("max", 1) == 1:
                return options[0]
            else:
                return options[:min_sel]
        else:
            return None

    return None


def suggest_variable_values_from_kb(
    variable_name, variable_type, knowledge_base, model="gpt-3.5-turbo"
):
    """
    Use LLM to suggest possible values for a variable based on the knowledge base content.
    Especially useful for categorical variables to extract options from documents.
    """
    if not knowledge_base:
        return None

    # Truncate knowledge base if it's too long
    kb_excerpt = (
        knowledge_base[:100000] + "..."
        if len(knowledge_base) > 100000
        else knowledge_base
    )

    prompt = f"""
    Based on the following knowledge base content, suggest appropriate values for a variable named "{variable_name}" of type "{variable_type}".

    KNOWLEDGE BASE EXCERPT:
    {kb_excerpt}

    TASK:
    Extract or suggest appropriate values for this variable from the knowledge base.

    If the variable type is "categorical", return a list of possible options found in the knowledge base.
    If the variable type is "string", suggest a few example values.
    If the variable type is "int" or "float", suggest appropriate min/max ranges.
    If the variable type is "bool", suggest appropriate true/false conditions.

    Return your response as a JSON object with the following structure:
    For categorical: {{"options": ["option1", "option2", ...]}}
    For string: {{"examples": ["example1", "example2", ...], "min": min_length, "max": max_length}}
    For int/float: {{"min": minimum_value, "max": maximum_value, "examples": [value1, value2, ...]}}
    For bool: {{"examples": ["condition for true", "condition for false"]}}

    Only include values that are actually present or strongly implied in the knowledge base.
    """

    try:
        result = call_model_api(
            model=model,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.3,
        )

        # Extract JSON from the response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
        json_match = re.search(json_pattern, result)

        if json_match:
            json_str = json_match.group(1) if json_match.group(1) else result
            json_str = re.sub(r"```.*|```", "", json_str).strip()
            try:
                suggestions = json.loads(json_str, strict=False)
                return suggestions
            except:
                pass
        else:
            try:
                suggestions = json.loads(result, strict=False)
                return suggestions
            except:
                pass

        return None
    except Exception as e:
        print(f"Error suggesting variable values: {str(e)}")
        return None


@st.cache_data
def analyze_knowledge_base(knowledge_base, model="gpt-4o-mini"):
    """
    Analyze the knowledge base to extract potential variable names and values.
    This can be used to suggest variables when creating a new template.
    """
    if not knowledge_base:
        return None

    # Truncate knowledge base if it's too long
    kb_excerpt = (
        knowledge_base[:100000] + "..."
        if len(knowledge_base) > 100000
        else knowledge_base
    )

    prompt = f"""
    Analyze the following knowledge base content and identify potential variables that could be used in a template.

    KNOWLEDGE BASE EXCERPT:
    {kb_excerpt}

    TASK:
    1. Identify key entities, attributes, or concepts that could be used as variables
    2. For each variable, suggest an appropriate type (string, int, float, bool, categorical)
    3. For categorical variables, suggest possible options

    Return your analysis as a JSON array with the following structure:
    [
      {{
        "name": "variable_name",
        "description": "what this variable represents",
        "type": "string/int/float/bool/categorical",
        "options": ["option1", "option2", ...] (only for categorical type)
      }},
      ...
    ]

    Focus on extracting variables that appear frequently or seem important in the knowledge base.
    """

    try:
        result = call_model_api(
            model=model,
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        # Extract JSON from the response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\[[\s\S]*\]\s*$"
        json_match = re.search(json_pattern, result)

        if json_match:
            json_str = json_match.group(1) if json_match.group(1) else result
            json_str = re.sub(r"```.*|```", "", json_str).strip()
            try:
                suggestions = json.loads(json_str, strict=False)
                return suggestions
            except:
                pass
        else:
            try:
                suggestions = json.loads(result, strict=False)
                return suggestions
            except:
                pass

        return None
    except Exception as e:
        print(f"Error analyzing knowledge base: {str(e)}")
        return None


def generate_missing_column_values(row_data, missing_var_defs, max_retries=3):
    """
    Generate values for missing columns based on existing row data.

    Args:
        row_data (dict): The existing row data
        missing_var_defs (list): List of variable definitions for missing columns
        max_retries (int): Maximum number of retry attempts

    Returns:
        dict: Generated values for missing columns
    """
    # Format the variables for the prompt
    vars_text = "\n".join(
        [
            f"- {var['name']}: {var['description']} (Type: {var['type']})"
            + (
                f", Min: {var.get('min', 'N/A')}, Max: {var.get('max', 'N/A')}"
                if var["type"] in ["string", "int", "float"]
                else ""
            )
            + (f", Options: {var['options']}" if var.get("options") else "")
            for var in missing_var_defs
        ]
    )

    # Create prompt with existing row data as context
    prompt = f"""
    As a synthetic data generator, create values for these missing columns:

    {vars_text}

    These values should be coherent with the existing row data:
    {json.dumps(row_data, indent=2)}

    Return ONLY a JSON object with the new variable values:
    {{
      "variable_name_1": value1,
      "variable_name_2": value2
    }}
    """

    for attempt in range(max_retries):
        try:
            response = call_model_api(
                model=st.session_state.model,
                prompt=prompt,
                max_tokens=1000,
                temperature=st.session_state.temperature,
            )

            result = response.strip()

            # Extract JSON
            json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
            json_match = re.search(json_pattern, result)

            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else result
                json_str = re.sub(r"```.*|```", "", json_str).strip()
                try:
                    values = json.loads(json_str, strict=False)
                    if isinstance(values, dict):
                        return values
                except:
                    pass
            else:
                try:
                    values = json.loads(result, strict=False)
                    if isinstance(values, dict):
                        return values
                except:
                    pass

        except Exception as e:
            if attempt == max_retries - 1:
                st.warning(f"Failed to generate missing column values: {str(e)}")

    # Fallback: generate default values for all missing columns
    return {var["name"]: get_default_value(var) for var in missing_var_defs}
