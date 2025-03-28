# utils/data_utils.py
import pandas as pd
import json


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


def prepare_dataframe_for_parquet(df):
    """
    Convert DataFrame columns to types compatible with Parquet format.

    Args:
        df (pd.DataFrame): Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with converted types
    """
    df_copy = df.copy()

    for col in df_copy.columns:
        # Check if column contains lists or dictionaries
        if df_copy[col].apply(lambda x: isinstance(x, (list, dict))).any():
            # Convert lists and dictionaries to JSON strings
            df_copy[col] = df_copy[col].apply(
                lambda x: (json.dumps(x) if isinstance(x, (list, dict)) else x)
            )

        # Check for mixed types that might cause issues
        if df_copy[col].apply(lambda x: isinstance(x, (bool, int, float, str))).all():
            # Column has consistent primitive types, leave as is
            continue
        else:
            # Convert any complex or mixed types to strings
            df_copy[col] = df_copy[col].apply(str)

    return df_copy


def prepare_dataframe_with_json_columns(data, template_spec, show_json_columns=False):
    df = pd.DataFrame(data)

    # Create input and output JSON columns
    input_vars = [var["name"] for var in template_spec["input"]]
    output_vars = [var["name"] for var in template_spec["output"]]

    # Create input JSON column
    df["input"] = df.apply(
        lambda row: json.dumps({var: row[var] for var in input_vars if var in row}),
        axis=1,
    )

    # Create output JSON column
    df["output"] = df.apply(
        lambda row: json.dumps({var: row[var] for var in output_vars if var in row}),
        axis=1,
    )

    # If not showing JSON columns in UI, remove them for display only
    if not show_json_columns:
        display_df = df.drop(columns=["input", "output"])
        return df, display_df

    return df, df
