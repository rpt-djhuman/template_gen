# utils/template_utils.py
import json
import streamlit as st


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


def parse_template_file(uploaded_template):
    """Parse an uploaded template JSON file and validate its structure."""
    try:
        # Read the file content
        if uploaded_template.name.endswith(".json"):
            template_content = uploaded_template.getvalue().decode("utf-8")
            template_spec = json.loads(template_content)

            # Sanitize the template to remove UI-specific keys
            template_spec = sanitize_template_spec(template_spec)

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


def sanitize_template_spec(template_spec):
    """
    Remove UI-specific keys from template specification that shouldn't be part of the template.

    Args:
        template_spec (dict): The template specification to sanitize

    Returns:
        dict: Sanitized template specification
    """
    if not template_spec:
        return template_spec

    # Create a deep copy to avoid modifying the original
    sanitized_spec = template_spec.copy()

    # List of UI-specific keys that should be removed
    ui_specific_keys = ["previous_options", "selected_options"]

    # Clean input variables
    if "input" in sanitized_spec and isinstance(sanitized_spec["input"], list):
        for i, var in enumerate(sanitized_spec["input"]):
            # Remove UI-specific keys from each variable
            sanitized_spec["input"][i] = {
                k: v for k, v in var.items() if k not in ui_specific_keys
            }

    # Clean output variables
    if "output" in sanitized_spec and isinstance(sanitized_spec["output"], list):
        for i, var in enumerate(sanitized_spec["output"]):
            # Remove UI-specific keys from each variable
            sanitized_spec["output"][i] = {
                k: v for k, v in var.items() if k not in ui_specific_keys
            }

    return sanitized_spec
