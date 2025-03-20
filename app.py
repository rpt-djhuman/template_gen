import streamlit as st
import json
import PyPDF2
from docling.document_converter import DocumentConverter
import re
from io import BytesIO
import openai
import pandas as pd
import itertools
import random
import math
from tqdm import tqdm

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


@st.cache_resource
def get_document_converter():
    """Cache the DocumentConverter to prevent reloading on each interaction"""
    return None  # Return None initially


def get_or_create_document_converter():
    """Get existing converter or create a new one only when needed"""
    converter = get_document_converter()
    if converter is None:
        converter = DocumentConverter()
        # Update the cached value
        get_document_converter._cached_obj = converter
    return converter


def create_example_templates():
    examples = [
        {
            "name": "Character Generator",
            "description": "Generate fantasy character descriptions based on selected traits",
            "version": "1.0.0",
            "input": [
                {
                    "name": "race",
                    "description": "Character's fantasy race",
                    "type": "categorical",
                    "options": ["Human", "Elf", "Dwarf", "Orc", "Halfling"],
                    "min": 1,
                    "max": 1,
                },
                {
                    "name": "class",
                    "description": "Character's profession or class",
                    "type": "categorical",
                    "options": ["Warrior", "Mage", "Rogue", "Cleric", "Ranger"],
                    "min": 1,
                    "max": 1,
                },
                {
                    "name": "alignment",
                    "description": "Character's moral alignment",
                    "type": "categorical",
                    "options": [
                        "Lawful Good",
                        "Neutral",
                        "Chaotic Evil",
                        "Lawful Evil",
                        "Chaotic Good",
                    ],
                    "min": 1,
                    "max": 1,
                },
            ],
            "output": [
                {
                    "name": "character_name",
                    "description": "Generated character name",
                    "type": "string",
                    "min": 3,
                    "max": 30,
                },
                {
                    "name": "background",
                    "description": "Character background story",
                    "type": "string",
                    "min": 100,
                    "max": 500,
                },
            ],
            "prompt": "Create a fantasy character with the following traits:\nRace: {race}\nClass: {class}\nAlignment: {alignment}\n\nGenerate a suitable name and background story for this character.",
        },
        {
            "name": "Recipe Generator",
            "description": "Generate cooking recipes based on ingredients and cuisine",
            "version": "1.0.0",
            "input": [
                {
                    "name": "cuisine",
                    "description": "Style of cooking",
                    "type": "categorical",
                    "options": ["Italian", "Mexican", "Chinese", "Indian", "French"],
                    "min": 1,
                    "max": 1,
                },
                {
                    "name": "main_ingredient",
                    "description": "Primary ingredient",
                    "type": "categorical",
                    "options": ["Chicken", "Beef", "Fish", "Tofu", "Vegetables"],
                    "min": 1,
                    "max": 1,
                },
                {
                    "name": "dietary_restriction",
                    "description": "Dietary requirements",
                    "type": "categorical",
                    "options": [
                        "None",
                        "Vegetarian",
                        "Vegan",
                        "Gluten-free",
                        "Dairy-free",
                    ],
                    "min": 1,
                    "max": 1,
                },
            ],
            "output": [
                {
                    "name": "recipe_name",
                    "description": "Name of the recipe",
                    "type": "string",
                    "min": 5,
                    "max": 50,
                },
                {
                    "name": "ingredients",
                    "description": "List of ingredients needed",
                    "type": "string",
                    "min": 50,
                    "max": 300,
                },
                {
                    "name": "instructions",
                    "description": "Cooking instructions",
                    "type": "string",
                    "min": 100,
                    "max": 500,
                },
            ],
            "prompt": "Create a {cuisine} recipe using {main_ingredient} as the main ingredient. The recipe should be {dietary_restriction}.\n\nProvide a recipe name, list of ingredients, and cooking instructions.",
        },
        {
            "name": "Product Description",
            "description": "Generate marketing descriptions for products",
            "version": "1.0.0",
            "input": [
                {
                    "name": "product_type",
                    "description": "Type of product",
                    "type": "categorical",
                    "options": [
                        "Smartphone",
                        "Laptop",
                        "Headphones",
                        "Smartwatch",
                        "Camera",
                    ],
                    "min": 1,
                    "max": 1,
                },
                {
                    "name": "target_audience",
                    "description": "Target customer demographic",
                    "type": "categorical",
                    "options": [
                        "Students",
                        "Professionals",
                        "Gamers",
                        "Creatives",
                        "Seniors",
                    ],
                    "min": 1,
                    "max": 1,
                },
                {
                    "name": "price_tier",
                    "description": "Price category",
                    "type": "categorical",
                    "options": [
                        "Budget",
                        "Mid-range",
                        "Premium",
                        "Luxury",
                        "Enterprise",
                    ],
                    "min": 1,
                    "max": 1,
                },
            ],
            "output": [
                {
                    "name": "product_name",
                    "description": "Generated product name",
                    "type": "string",
                    "min": 5,
                    "max": 30,
                },
                {
                    "name": "tagline",
                    "description": "Short marketing tagline",
                    "type": "string",
                    "min": 10,
                    "max": 100,
                },
                {
                    "name": "description",
                    "description": "Full product description",
                    "type": "string",
                    "min": 100,
                    "max": 500,
                },
            ],
            "prompt": "Create a marketing description for a {price_tier} {product_type} targeted at {target_audience}.\n\nProvide a product name, catchy tagline, and compelling product description.",
        },
    ]

    return examples


# Create a function to display example outputs
def create_example_outputs(template):
    # Predefined outputs for each template
    if template["name"] == "Character Generator":
        outputs = {
            "Human Warrior Lawful Good": {
                "character_name": "Sir Galahad Ironheart",
                "background": "Born to a noble family in the kingdom of Valorhaven, Sir Galahad trained from childhood in the arts of combat. After saving the king's daughter from bandits, he was knighted and now serves as captain of the royal guard. His unwavering dedication to justice and honor has made him a legend throughout the realm, though his strict adherence to the code of chivalry sometimes puts him at odds with more pragmatic allies.",
            },
            "Elf Mage Chaotic Good": {
                "character_name": "Lyraniel Starweaver",
                "background": "Raised in the ancient forest of Eldrath, Lyraniel discovered her affinity for arcane magic when she accidentally set a tree ablaze during an argument. Rather than follow the structured magical traditions of her people, she left to study diverse magical practices across the continent. She now uses her considerable powers to protect the innocent and fight tyranny, though her methods are often unpredictable and sometimes cause as much chaos as they resolve.",
            },
            "Dwarf Rogue Neutral": {
                "character_name": "Grimble Lockpick",
                "background": "Once a respected jeweler in the mountain halls of Karak-Dûm, Grimble's curiosity about the perfect lock led him down a different path. Neither malicious nor heroic, he sees himself as a professional who offers specialized services for the right price. His reputation for being able to open any lock or disarm any trap has made him sought after by adventurers and nobles alike, though he remains careful to avoid political entanglements that might limit his freedom.",
            },
        }
    elif template["name"] == "Recipe Generator":
        outputs = {
            "Italian Chicken None": {
                "recipe_name": "Tuscan Herb-Roasted Chicken",
                "ingredients": "- 4 chicken breasts\n- 3 tbsp olive oil\n- 4 cloves garlic, minced\n- 1 tbsp fresh rosemary, chopped\n- 1 tbsp fresh thyme, chopped\n- 1 lemon, zested and juiced\n- 1 cup cherry tomatoes, halved\n- 1/2 cup chicken broth\n- 1/4 cup dry white wine\n- Salt and pepper to taste\n- Fresh basil for garnish",
                "instructions": "1. Preheat oven to 375°F (190°C).\n2. Season chicken breasts with salt and pepper.\n3. In a large oven-safe skillet, heat olive oil over medium-high heat.\n4. Sear chicken breasts for 3-4 minutes per side until golden brown.\n5. Add garlic, rosemary, and thyme to the pan and cook for 1 minute until fragrant.\n6. Add lemon zest, lemon juice, cherry tomatoes, chicken broth, and white wine.\n7. Transfer skillet to the oven and roast for 20-25 minutes until chicken is cooked through.\n8. Garnish with fresh basil before serving.",
            },
            "Mexican Vegetables Vegetarian": {
                "recipe_name": "Roasted Vegetable Enchiladas Verde",
                "ingredients": "- 2 zucchini, diced\n- 1 red bell pepper, diced\n- 1 yellow bell pepper, diced\n- 1 red onion, sliced\n- 2 cups mushrooms, sliced\n- 3 tbsp olive oil\n- 2 tsp cumin\n- 1 tsp chili powder\n- 1 tsp oregano\n- 8 corn tortillas\n- 2 cups salsa verde\n- 1 1/2 cups shredded Monterey Jack cheese\n- 1 avocado, sliced\n- 1/4 cup cilantro, chopped\n- Lime wedges for serving",
                "instructions": "1. Preheat oven to 425°F (220°C).\n2. Toss zucchini, bell peppers, onion, and mushrooms with olive oil, cumin, chili powder, oregano, salt, and pepper.\n3. Spread vegetables on a baking sheet and roast for 20 minutes, stirring halfway through.\n4. Reduce oven temperature to 375°F (190°C).\n5. Warm tortillas slightly to make them pliable.\n6. Fill each tortilla with roasted vegetables and roll up.\n7. Place enchiladas seam-side down in a baking dish.\n8. Pour salsa verde over enchiladas and sprinkle with cheese.\n9. Bake for 20-25 minutes until cheese is melted and bubbly.\n10. Garnish with avocado slices and cilantro. Serve with lime wedges.",
            },
        }
    elif template["name"] == "Product Description":
        outputs = {
            "Smartphone Professionals Premium": {
                "product_name": "ExecuTech Pro X9",
                "tagline": "Seamless productivity meets uncompromising elegance.",
                "description": 'The ExecuTech Pro X9 redefines what a business smartphone can be. Crafted with aerospace-grade materials and featuring our revolutionary 6.7" CrystalClear AMOLED display, the Pro X9 ensures your presentations and video conferences look impeccable in any lighting condition. The advanced 5-lens camera system with AI enhancement captures professional-quality images for your reports and social media, while the dedicated security co-processor keeps your sensitive data protected with military-grade encryption. With an impressive 36-hour battery life and our proprietary RapidCharge technology, the Pro X9 keeps pace with your demanding schedule. Experience the perfect balance of performance and sophistication that successful professionals deserve.',
            },
            "Headphones Gamers Mid-range": {
                "product_name": "SonicStrike GT-500",
                "tagline": "Hear every move. Dominate every game.",
                "description": "Level up your gaming experience with the SonicStrike GT-500 gaming headset. Engineered specifically for competitive gamers, these headphones feature our proprietary 50mm UltraBass drivers that deliver thunderous lows while maintaining crystal-clear highs, allowing you to hear enemy footsteps with pinpoint accuracy. The detachable boom microphone with noise-cancellation ensures your teammates hear your callouts clearly, even in the heat of battle. With memory foam ear cushions wrapped in breathable mesh fabric, the GT-500 remains comfortable during marathon gaming sessions. Compatible with all major gaming platforms and featuring customizable RGB lighting through our GameSync app, the SonicStrike GT-500 offers premium features at a price that won't break the bank. Your gaming advantage starts here.",
            },
        }
    else:
        outputs = {}

    return outputs


# Add this function after generate_categorical_permutations function
def calculate_cartesian_product_size(categorical_vars):
    """Calculate the size of the Cartesian product based on selected options."""
    if not categorical_vars:
        return 0

    # Calculate the product size
    product_size = 1
    var_counts = []

    for var in categorical_vars:
        options = var.get("options", [])
        selected_options = var.get("selected_options", options)
        min_sel = var.get("min", 1)
        max_sel = var.get("max", 1)

        # Use only selected options for calculation
        options_to_use = [opt for opt in options if opt in selected_options]

        # If no options selected, use all options
        if not options_to_use:
            options_to_use = options

        # Single selection case
        if min_sel == 1 and max_sel == 1:
            count = len(options_to_use)
        else:
            # Multi-selection case - calculate combinations
            count = 0
            # Include min selections
            from math import comb

            if len(options_to_use) >= min_sel:
                count += comb(len(options_to_use), min_sel)

            # Include max selections if different from min
            if max_sel != min_sel and len(options_to_use) >= max_sel:
                count += comb(len(options_to_use), max_sel)

            # Include some intermediate selections if applicable
            for size in range(min_sel + 1, max_sel):
                if len(options_to_use) >= size:
                    count += min(
                        3, comb(len(options_to_use), size)
                    )  # Take up to 3 samples

        var_counts.append({"name": var["name"], "count": count})
        product_size *= max(count, 1)  # Avoid multiplying by zero

    return product_size, var_counts


@st.cache_data
def parse_documents(uploaded_files):
    """Parse multiple document files and extract their text content."""
    if not uploaded_files:
        return ""

    import tempfile
    import os

    converter = get_or_create_document_converter()
    content = ""

    for file in uploaded_files:
        try:
            file_type = file.name.split(".")[-1].lower()

            # Handle text files directly
            if file_type == "txt":
                content += file.getvalue().decode("utf-8")
            # Use converter for other supported file types
            elif file_type in ["pdf", "docx", "html"]:
                # Create a temporary file with the correct extension
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f".{file_type}"
                ) as tmp_file:
                    # Write the uploaded file content to the temp file
                    tmp_file.write(file.getvalue())
                    tmp_path = tmp_file.name

                # Convert using the file path instead of the UploadedFile object
                source = converter.convert(tmp_path)
                content += source.document.export_to_markdown()

                # Clean up the temporary file
                os.unlink(tmp_path)
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

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=st.session_state.get("temperature", 0.7),
        )

        result = response.choices[0].message.content

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
        response = client.chat.completions.create(
            model=st.session_state.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
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
        response = client.chat.completions.create(
            model=st.session_state.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
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


def generate_synthetic_inputs_hybrid(template_spec, num_samples=10, max_retries=3):
    """
    Generate synthetic input data using a hybrid approach:
    - Programmatically generate combinations of categorical variables
    - Use LLM to fill in non-categorical variables
    - Process row by row for resilience
    """
    client = get_openai_client()
    if not client:
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
                        non_categorical_vars, perm, client, max_retries
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
                row = generate_single_row(input_vars, client, max_retries)
                if row:
                    results.append(row)

        # Ensure we have the requested number of samples
        while len(results) < num_samples:
            # Generate additional rows if needed
            row = generate_single_row(input_vars, client, max_retries)
            if row:
                results.append(row)

        # Ensure progress bar completes
        progress_bar.progress(1.0)

    return results[:num_samples]


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


def generate_non_categorical_values(non_cat_vars, existing_values, client, max_retries):
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
            response = client.chat.completions.create(
                model=st.session_state.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=st.session_state.temperature,
            )

            result = response.choices[0].message.content.strip()

            # Extract JSON
            json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
            json_match = re.search(json_pattern, result)

            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else result
                json_str = re.sub(r"```.*|```", "", json_str).strip()
                try:
                    values = json.loads(json_str)
                    if isinstance(values, dict):
                        return values
                except:
                    pass
            else:
                try:
                    values = json.loads(result)
                    if isinstance(values, dict):
                        return values
                except:
                    pass

        except Exception as e:
            if attempt == max_retries - 1:
                st.warning(f"Failed to generate non-categorical values: {str(e)}")

    # Fallback: generate empty values for all non-categorical variables
    return {var["name"]: get_default_value(var) for var in non_cat_vars}


def generate_single_row(all_vars, client, max_retries):
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
            response = client.chat.completions.create(
                model=st.session_state.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=st.session_state.temperature,
            )

            result = response.choices[0].message.content.strip()

            # Extract JSON
            json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
            json_match = re.search(json_pattern, result)

            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else result
                json_str = re.sub(r"```.*|```", "", json_str).strip()
                try:
                    values = json.loads(json_str)
                    if isinstance(values, dict):
                        return values
                except:
                    pass
            else:
                try:
                    values = json.loads(result)
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
            print(generation_prompt)
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=st.session_state.model,
                        messages=[{"role": "user", "content": generation_prompt}],
                        max_tokens=2000,
                        temperature=st.session_state.temperature,
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


def suggest_variable_values_from_kb(
    variable_name, variable_type, knowledge_base, client, model="gpt-3.5-turbo"
):
    """
    Use LLM to suggest possible values for a variable based on the knowledge base content.
    Especially useful for categorical variables to extract options from documents.
    """
    if not knowledge_base or not client:
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
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3,
        )

        result = response.choices[0].message.content

        # Extract JSON from the response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\{[\s\S]*\}\s*$"
        json_match = re.search(json_pattern, result)

        if json_match:
            json_str = json_match.group(1) if json_match.group(1) else result
            json_str = re.sub(r"```.*|```", "", json_str).strip()
            try:
                suggestions = json.loads(json_str)
                return suggestions
            except:
                pass
        else:
            try:
                suggestions = json.loads(result)
                return suggestions
            except:
                pass

        return None
    except Exception as e:
        print(f"Error suggesting variable values: {str(e)}")
        return None


@st.cache_data
def analyze_knowledge_base(knowledge_base, _client, model="gpt-4o-mini"):
    """
    Analyze the knowledge base to extract potential variable names and values.
    This can be used to suggest variables when creating a new template.
    """
    if not knowledge_base or not client:
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
        response = _client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )

        result = response.choices[0].message.content

        # Extract JSON from the response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*\[[\s\S]*\]\s*$"
        json_match = re.search(json_pattern, result)

        if json_match:
            json_str = json_match.group(1) if json_match.group(1) else result
            json_str = re.sub(r"```.*|```", "", json_str).strip()
            try:
                suggestions = json.loads(json_str)
                return suggestions
            except:
                pass
        else:
            try:
                suggestions = json.loads(result)
                return suggestions
            except:
                pass

        return None
    except Exception as e:
        print(f"Error analyzing knowledge base: {str(e)}")
        return None


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
        options=["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4-turbo"],
        index=0,
    )

# Main application layout
st.title("Template Generator")

# Create tabs for workflow
tab1, tab2, tab3 = st.tabs(["Setup", "Edit and Use Template", "Generate Data"])

with tab1:
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

                    # Rerun to update the UI
                    # st.rerun()

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
                with st.expander("Template Preview", expanded=False):
                    st.json(template_spec)

                # Button to use this template
                if st.button("Use This Template"):
                    st.session_state.template_spec = template_spec
                    st.session_state.show_template_editor = True
                    st.success(
                        "Template loaded! Go to the 'Edit Template' tab to customize it."
                    )

    elif setup_option == "Create new template from documents":
        # Step 1: Upload Knowledge Base
        st.subheader("Step 1: Upload Knowledge Base")
        uploaded_files = st.file_uploader(
            "Upload documents to use as knowledge base",
            accept_multiple_files=True,
            type=["pdf", "txt", "html"],
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

    elif setup_option == "Create an empty template":
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

with tab2:
    if st.session_state.show_template_editor and st.session_state.template_spec:
        st.header("Template Editor")
        st.subheader(st.session_state.template_spec["name"])

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

        # Create main layout with left (settings) and right (generation) columns
        left_col, right_col = st.columns([3, 2])

        # LEFT COLUMN - Settings
        with left_col:
            # Basic template information
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
                st.info(
                    "Use {variable_name} to refer to input variables in your template"
                )

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

            # Knowledge Base Analysis Section
            if st.session_state.knowledge_base:
                with st.expander("Knowledge Base Analysis", expanded=False):
                    st.info(
                        "Analyze the knowledge base to suggest variables and values"
                    )

                    if st.button(
                        "Analyze Knowledge Base for Variables",
                        key="analyze_kb_button_input",
                    ):
                        client = get_openai_client()
                        if not client:
                            st.error(
                                "Please provide an OpenAI API key to analyze the knowledge base."
                            )
                        else:
                            with st.spinner("Analyzing knowledge base..."):
                                suggested_vars = analyze_knowledge_base(
                                    st.session_state.knowledge_base, client
                                )
                                if suggested_vars:
                                    st.session_state.suggested_variables = (
                                        suggested_vars
                                    )
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
                                    st.session_state.template_spec["input"].append(
                                        new_var
                                    )

                                    # Mark this variable as added
                                    st.session_state.added_suggestions.add(var_id)

                                    # Show success message
                                    st.success(
                                        f"Added {var['name']} to input variables!"
                                    )

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
                            # Create the appropriate input field based on variable type
                            if var_type == "string":
                                st.session_state.user_inputs[var_name] = st.text_input(
                                    f"Enter value for {var_name}", key=f"use_{var_name}"
                                )
                            elif var_type == "int":
                                st.session_state.user_inputs[var_name] = (
                                    st.number_input(
                                        f"Enter value for {var_name}",
                                        min_value=input_var.get("min", None),
                                        max_value=input_var.get("max", None),
                                        step=1,
                                        key=f"use_{var_name}",
                                    )
                                )
                            elif var_type == "float":
                                st.session_state.user_inputs[var_name] = (
                                    st.number_input(
                                        f"Enter value for {var_name}",
                                        min_value=float(input_var.get("min", 0)),
                                        max_value=float(input_var.get("max", 100)),
                                        key=f"use_{var_name}",
                                    )
                                )
                            elif var_type == "bool":
                                st.session_state.user_inputs[var_name] = st.checkbox(
                                    f"Select value for {var_name}",
                                    key=f"use_{var_name}",
                                )
                            elif var_type == "categorical":
                                options = input_var.get("options", [])
                                min_selections = input_var.get("min", 1)
                                max_selections = input_var.get("max", 1)

                                if options:
                                    if min_selections == 1 and max_selections == 1:
                                        # Single selection
                                        st.session_state.user_inputs[var_name] = (
                                            st.selectbox(
                                                f"Select value for {var_name}",
                                                options=options,
                                                key=f"use_{var_name}",
                                            )
                                        )
                                    else:
                                        # Multi-selection
                                        st.session_state.user_inputs[var_name] = (
                                            st.multiselect(
                                                f"Select {min_selections}-{max_selections} values for {var_name}",
                                                options=options,
                                                default=(
                                                    options[:min_selections]
                                                    if len(options) >= min_selections
                                                    else options
                                                ),
                                                key=f"use_{var_name}",
                                            )
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
                                st.markdown(
                                    f"##### Variable Settings: {input_var['name']}"
                                )

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
                                                f"Suggesting options for {input_var['name']}..."
                                            ):
                                                suggestions = (
                                                    suggest_variable_values_from_kb(
                                                        input_var["name"],
                                                        "categorical",
                                                        st.session_state.knowledge_base,
                                                        client,
                                                    )
                                                )
                                                if (
                                                    suggestions
                                                    and "options" in suggestions
                                                ):
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
                for i, output_var in enumerate(
                    st.session_state.template_spec["output"]
                ):
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(
                            f"**{output_var['name']}** - {output_var['description']}"
                        )

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
                            st.markdown(
                                f"##### Edit Output Variable: {output_var['name']}"
                            )

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
                                            suggestions = (
                                                suggest_variable_values_from_kb(
                                                    output_var["name"],
                                                    "categorical",
                                                    st.session_state.knowledge_base,
                                                    client,
                                                )
                                            )
                                            if suggestions and "options" in suggestions:
                                                output_var["options"] = suggestions[
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

        # RIGHT COLUMN - Generation
        with right_col:
            st.header("Generation")

            # Handle the lore/knowledge base as a special variable
            prompt_template = st.session_state.template_spec["prompt"]
            if "{lore}" in prompt_template:
                with st.expander("Document Knowledge Base", expanded=False):
                    st.markdown("##### Document Knowledge Base")

                    # Display info about the knowledge base
                    if st.session_state.knowledge_base:
                        st.success(
                            f"Using content from {len(st.session_state.uploaded_filenames) if 'uploaded_filenames' in st.session_state else 'uploaded'} documents as knowledge base"
                        )

                        # Use a button to toggle knowledge base content view instead of an expander
                        if st.button(
                            "View/Hide Knowledge Base Content", key="toggle_kb_view"
                        ):
                            st.session_state.show_kb_content = not st.session_state.get(
                                "show_kb_content", False
                            )

                        if st.session_state.get("show_kb_content", False):
                            st.text_area(
                                "Knowledge base content",
                                value=st.session_state.knowledge_base[:2000]
                                + (
                                    "..."
                                    if len(st.session_state.knowledge_base) > 2000
                                    else ""
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
                        st.warning(
                            "No documents uploaded. You can provide custom lore below."
                        )
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
                            output_vars = [
                                var["name"] for var in template_spec_copy["output"]
                            ]
                            output_data = {
                                k: v
                                for k, v in generated_outputs[0].items()
                                if k in output_vars
                            }
                            st.session_state.generated_output = output_data
                        else:
                            st.session_state.generated_output = {
                                "error": "Failed to generate output"
                            }

            # Display generated output
            if (
                "generated_output" in st.session_state
                and st.session_state.generated_output
            ):
                st.header("Generated Output")

                # Check if the output is a dictionary (JSON)
                if isinstance(st.session_state.generated_output, dict):
                    # Display as JSON
                    st.json(st.session_state.generated_output)

                    # Option to save the output as JSON
                    output_json = json.dumps(
                        st.session_state.generated_output, indent=2
                    )
                    st.download_button(
                        label="Download Output (JSON)",
                        data=output_json,
                        file_name="generated_output.json",
                        mime="application/json",
                    )
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
    else:
        st.info(
            "No template has been generated yet. Go to the 'Setup' tab to create one."
        )

with tab3:
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

        # Add option selection for categorical variables
        categorical_vars = [
            var
            for var in st.session_state.template_spec["input"]
            if var["type"] == "categorical" and var.get("options")
        ]

        # In tab3, modify the categorical variable options section
        if categorical_vars:
            st.subheader("Categorical Variable Options")
            st.info(
                "Select which options to include in the permutations for each categorical variable."
            )

            # Create a copy of the template spec for modification
            template_spec_copy = st.session_state.template_spec.copy()
            template_spec_copy["input"] = st.session_state.template_spec["input"].copy()

            # For each categorical variable, allow selecting options
            for i, var in enumerate(
                [
                    v
                    for v in template_spec_copy["input"]
                    if v["type"] == "categorical" and v.get("options")
                ]
            ):
                with st.expander(
                    f"{var['name']} - {var['description']}", expanded=False
                ):
                    options = var.get("options", [])

                    # Initialize selected_options if not present
                    if "selected_options" not in var:
                        # First time initialization
                        var["selected_options"] = options.copy()
                    else:
                        # Filter selected_options to only include valid options
                        var["selected_options"] = [
                            opt
                            for opt in var.get("selected_options", [])
                            if opt in options
                        ]

                        # Check for new options that need to be automatically selected
                        previous_options = var.get("previous_options", [])

                        # Find new options that weren't in the previous options list
                        new_options = [
                            opt for opt in options if opt not in previous_options
                        ]

                        # Add new options to selected_options
                        if new_options:
                            var["selected_options"].extend(new_options)

                    # Store current options for future comparison
                    var["previous_options"] = options.copy()

                    # Add "Select All" and "Clear All" buttons
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button(
                            f"Select All Options for {var['name']}",
                            key=f"select_all_{i}",
                        ):
                            var["selected_options"] = options.copy()
                    with col2:
                        if st.button(
                            f"Clear All Options for {var['name']}", key=f"clear_all_{i}"
                        ):
                            var["selected_options"] = []

                    # Create multiselect for options
                    var["selected_options"] = st.multiselect(
                        f"Select options to include for {var['name']}",
                        options=options,
                        default=var.get(
                            "selected_options", []
                        ),  # Use empty list as fallback
                        key=f"options_select_{i}",
                    )

                    # Show selected count
                    st.write(
                        f"Selected {len(var['selected_options'])} out of {len(options)} options"
                    )

                # Update the template spec with the selected options
                for j, input_var in enumerate(template_spec_copy["input"]):
                    if input_var["name"] == var["name"]:
                        template_spec_copy["input"][j] = var
                        break

            # Calculate and display Cartesian product size
            product_size, var_counts = calculate_cartesian_product_size(
                [v for v in template_spec_copy["input"] if v["type"] == "categorical"]
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

        # Generate inputs button
        if st.button("Generate Synthetic Inputs"):
            if not st.session_state.get("api_key"):
                st.error("Please provide an OpenAI API key in the sidebar.")
            else:
                with st.spinner(f"Generating {num_samples} synthetic input samples..."):
                    # Use the modified template spec with selected options
                    if categorical_vars:
                        st.session_state.synthetic_inputs = (
                            generate_synthetic_inputs_hybrid(
                                template_spec_copy, num_samples=num_samples
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

            # Sample selection for output generation
            st.subheader("Generate Outputs")

            # Initialize the modified prompt template if not already done
            if not st.session_state.modified_prompt_template:
                st.session_state.modified_prompt_template = (
                    st.session_state.template_spec["prompt"]
                )

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
                    st.session_state.modified_prompt_template = (
                        st.session_state.template_spec["prompt"]
                    )
                    st.success("Prompt template reset to original")

            # Sample selection options
            selection_method = st.radio(
                "Select samples for output generation",
                options=["Generate for all samples", "Select specific samples"],
                index=0,
            )

            if selection_method == "Select specific samples":
                # Create a list of sample indices for selection
                sample_options = [
                    f"Sample {i+1}"
                    for i in range(len(st.session_state.synthetic_inputs))
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
                        filled_prompt = filled_prompt.replace(
                            f"{{{var_name}}}", str(var_value)
                        )

                    # Replace {lore} with knowledge base if present
                    if "{lore}" in filled_prompt:
                        filled_prompt = filled_prompt.replace(
                            "{lore}", st.session_state.knowledge_base
                        )

                    # Show the filled prompt
                    st.text_area(
                        "Filled Prompt", value=filled_prompt, height=300, disabled=True
                    )

            # Generate outputs button
            if st.button("Generate Outputs for Selected Samples"):
                if not st.session_state.get("api_key"):
                    st.error("Please provide an OpenAI API key in the sidebar.")
                elif not st.session_state.selected_samples:
                    st.error("No samples selected for output generation.")
                else:
                    # Create a copy of the template spec with the modified prompt
                    modified_template = st.session_state.template_spec.copy()
                    modified_template["prompt"] = (
                        st.session_state.modified_prompt_template
                    )

                    # Get only the selected samples
                    selected_inputs = [
                        st.session_state.synthetic_inputs[i]
                        for i in st.session_state.selected_samples
                    ]

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
                            # If we're generating for specific samples, update only those samples
                            # First, ensure combined_data exists and has the right size
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

                        st.success(
                            f"Generated outputs for {len(generated_outputs)} samples"
                        )

        # Display combined data if available
        if st.session_state.combined_data:
            st.subheader("Complete Dataset (Inputs + Outputs)")

            # Create a function to prepare the dataframe with JSON columns
            def prepare_dataframe_with_json_columns(
                data, template_spec, show_json_columns=False
            ):
                df = pd.DataFrame(data)

                # Create input and output JSON columns
                input_vars = [var["name"] for var in template_spec["input"]]
                output_vars = [var["name"] for var in template_spec["output"]]

                # Create input JSON column
                df["input"] = df.apply(
                    lambda row: json.dumps(
                        {var: row[var] for var in input_vars if var in row}
                    ),
                    axis=1,
                )

                # Create output JSON column
                df["output"] = df.apply(
                    lambda row: json.dumps(
                        {var: row[var] for var in output_vars if var in row}
                    ),
                    axis=1,
                )

                # If not showing JSON columns in UI, remove them for display only
                if not show_json_columns:
                    display_df = df.drop(columns=["input", "output"])
                    return df, display_df

                return df, df

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
                    # Write the DataFrame to the BytesIO object in Parquet format
                    full_df.to_parquet(parquet_buffer, index=False)
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
    else:
        st.info(
            "No template has been generated yet. Go to the 'Setup' tab to create one."
        )
