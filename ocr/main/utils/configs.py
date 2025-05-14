import functools
import json


def with_config(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        # Extract the config argument (path to the config file)
        config_path = kwargs.pop("config", None)

        # Load the config file if a path is provided
        if config_path:
            with open(config_path, "r") as file:
                config = json.load(file)
            kwargs["config"] = (
                config  # Pass the loaded config dictionary to the function
            )

        return func(*args, **kwargs)

    return decorator


def load_config(config_path):
    """Load a JSON config file."""
    with open(config_path, "r") as f:
        return json.load(f)
