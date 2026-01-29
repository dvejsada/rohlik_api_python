from typing import Any

def mask_data(input_dict: Any) -> Any:
    """Takes a dictionary and replaces all non-null values with "XXXXXXX". Null values (None) remain unchanged."""
    if not isinstance(input_dict, dict):
        return input_dict

    result = {}
    for key, value in input_dict.items():
        if value is None:
            result[key] = None
        elif isinstance(value, dict):
            result[key] = mask_data(value)
        elif isinstance(value, list):
            result[key] = [mask_data(item) if isinstance(item, dict)
                           else "XXXXXXX" if item is not None else None
                           for item in value]
        else:
            result[key] = "XXXXXXX"

    return result
