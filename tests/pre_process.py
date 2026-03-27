# tests/pre_process.py
import base64
import os
import sys
from dotenv import load_dotenv, find_dotenv
from PIL import Image
from io import BytesIO


def load_environment():
    """Load environment variables"""
    # Locate and load the .env file.
    dotenv_path = find_dotenv()
    if not dotenv_path:
        print("Warning: The .env file was not found. Please ensure that a .env file exists in the project root directory.")
        sys.exit(1)
    load_dotenv(dotenv_path)
    print(f"Environment variable file loaded: {dotenv_path}.")


def get_env_variable(var_name, default=None):
    """Retrieve environment variables; if they do not exist, use the default value or report an error."""
    value = os.environ.get(var_name, default)
    if value is None:
        raise ValueError(f"Warning: Environment variable {var_name} is not set and has no default value.")
    return value


def _image_to_base64_data(image_path: str) -> str:
    """Local image → base64 string (used for data URL)"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}.")
    try:
        with Image.open(image_path).convert("RGB") as img:
            # Adjust size
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85, optimize=True)
            # Check file size
            if buffer.getbuffer().nbytes > 4 * 1024 * 1024:
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=75, optimize=True)
            b64 = base64.b64encode(buffer.getvalue()).decode()
            return b64
    except Exception as e:
        raise ValueError(f"Image processing failed: {str(e)}")
    finally:
        if 'buffer' in locals():
            buffer.close()
