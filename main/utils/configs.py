import json
from functools import wraps

def with_config(config_path):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with open(config_path, 'r') as file:
                    config = json.load(file)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print("Error loading config:", e)
                config = {}
            return func(*args, config=config, **kwargs)
        return wrapper
    return decorator
