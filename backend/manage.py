#!/usr/bin/env python
"""
Utility script for running administrative tasks in the Django project.

This script exposes the `django-admin` command-line utility for
administrative tasks. It loads environment variables from a `.env` file if present
before delegating execution to Django's management command.
"""
import os
import sys
from pathlib import Path

try:
    # Attempt to read environment variables from a .env file. This allows
    # developers to specify secrets like the Django SECRET_KEY or database
    # credentials in a local file that is not committed to version control.
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None  # type: ignore


def main() -> None:
    """Run administrative tasks."""
    # If python-dotenv is available, load variables from `.env`. The `.env`
    # file should live in the project root (one directory above this script).
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(dotenv_path=env_path)

    # Set the default settings module for the 'django' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()