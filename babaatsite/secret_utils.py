import json
import os
from typing import Any, Dict

# Base directory where GCP Secret Manager mounts your secrets
# Default to '/secret', override with SECRETS_BASE_DIR env var if needed
SECRETS_BASE_DIR = os.getenv("SECRETS_BASE_DIR", "/secret")

# List your expected secret groups (use lowercase keys matching dir names)
EXPECTED_GROUPS = [
    "supabase",
    "s3",
    "django_secret",
    "redis",
    "hosts",
]


def _parse_value(raw: str) -> Any:
    """
    Attempt to parse a raw string as JSON; fallback to raw string.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def get_secret_group(group: str, base_dir: str = SECRETS_BASE_DIR) -> Any:
    """
    Load a single secret group by name.
    1. Check for an environment variable GROUP.upper(), parse JSON or raw.
    2. Else, look for secret file at {base_dir}/{group}/{GROUP.upper()}.txt.
    Raises FileNotFoundError if neither source exists.
    """
    key = group.upper()
    # 1) Environment variable override
    if key in os.environ:
        return _parse_value(os.environ[key])

    # 2) Secret Manager file mount
    file_path = os.path.join(base_dir, group, f"{key}.txt")
    if os.path.isfile(file_path):
        with open(file_path, "r") as f:
            raw = f.read().strip()
        return _parse_value(raw)

    # Not found
    raise FileNotFoundError(
        f"Secret '{group}' not found in env or at {file_path}"
    )


def load_all_secrets(base_dir: str = SECRETS_BASE_DIR) -> Dict[str, Any]:
    """
    Load all expected secret groups, returning a dict mapping group -> value.
    Skips any group where neither env nor file is present.
    """
    secrets: Dict[str, Any] = {}
    for group in EXPECTED_GROUPS:
        try:
            secrets[group] = get_secret_group(group, base_dir)
        except FileNotFoundError:
            continue
    return secrets
