# main.py
import os
import yaml
from src.evaluator import CultureEvaluator
import sys
from dotenv import load_dotenv, find_dotenv


def load_environment():
    """Load environment variables"""
    # Locate and load the .env file. If not found, print a warning and exit.
    dotenv_path = find_dotenv()
    if not dotenv_path:
        print(".env file not found. Please ensure it exists in the project root directory.")
        sys.exit(1)
    load_dotenv(dotenv_path)
    print(f"Environment variable file loaded: {dotenv_path}")


def main():
    load_environment()
    # Use absolute path or handle relative path
    config_dir = "configs"
    config_path = os.path.join(config_dir, "default.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    evaluator = CultureEvaluator(config)
    evaluator.run()


if __name__ == "__main__":
    main()