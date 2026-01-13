"""Decompression validator runner.

Calls the Rust deco validation HTTP endpoint for optimal performance.
Falls back to subprocess binary if HTTP is unavailable.
"""

import json
import logging
import subprocess

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# HTTP endpoint (same service as pricing)
RUST_DECO_URL = getattr(settings, "RUST_DECO_URL", None) or getattr(
    settings, "RUST_PRICING_URL", "http://localhost:8080/api/pricing"
).replace("/api/pricing", "/api/deco")


def _run_deco_http(input_data: dict) -> dict | None:
    """Call Rust deco HTTP endpoint. Returns None if unavailable."""
    try:
        timeout = getattr(settings, "RUST_DECO_TIMEOUT", 5.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(f"{RUST_DECO_URL}/validate", json=input_data)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Deco HTTP returned {response.status_code}: {response.text[:200]}")
                return response.json()  # Return error response from Rust
    except httpx.ConnectError:
        logger.debug("Deco HTTP endpoint unavailable, falling back to binary")
        return None
    except Exception as e:
        logger.warning(f"Deco HTTP error: {e}, falling back to binary")
        return None


def _run_deco_binary(input_data: dict) -> dict:
    """Call Rust deco binary via subprocess (fallback)."""
    validator_path = getattr(
        settings, "DECO_VALIDATOR_PATH", "/usr/local/bin/diveops-deco-validate"
    )
    timeout = getattr(settings, "DECO_VALIDATOR_TIMEOUT", 10)

    try:
        result = subprocess.run(
            [validator_path],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        logger.error(f"Validator binary not found: {validator_path}")
        return {"error": "validator_not_found", "tool": "diveops-deco-validate"}
    except subprocess.TimeoutExpired:
        logger.error(f"Validator timed out after {timeout}s")
        return {"error": "timeout", "tool": "diveops-deco-validate"}
    except Exception as e:
        logger.exception(f"Validator execution failed: {e}")
        return {"error": "execution_failed", "tool": "diveops-deco-validate"}

    if result.returncode != 0:
        logger.error(f"Validator failed (exit {result.returncode}): {result.stderr}")
        return {
            "error": "validator_failed",
            "tool": "diveops-deco-validate",
            "stderr": result.stderr[:500] if result.stderr else None,
            "returncode": result.returncode,
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from validator: {e}")
        return {
            "error": "invalid_json",
            "tool": "diveops-deco-validate",
            "stdout": result.stdout[:500] if result.stdout else None,
        }


def run_deco_validator(input_data: dict) -> dict:
    """Run deco validator, return normalized result.

    Tries HTTP endpoint first for optimal performance (~1ms vs ~50ms subprocess).
    Falls back to subprocess binary if HTTP is unavailable.

    Args:
        input_data: Dict with segments, gas, gf_low, gf_high

    Returns:
        Dict with validation results including:
        - tool, tool_version, model
        - ceiling_m, tts_min, ndl_min, deco_required
        - stops (list of depth_m/duration_min dicts)
        - input_hash
        - error (if validation failed)
    """
    # Try HTTP first (much faster - no subprocess overhead)
    result = _run_deco_http(input_data)
    if result is not None:
        return result

    # Fall back to binary
    return _run_deco_binary(input_data)
