"""Kapoor Galleries backend API package.

A thin FastAPI layer that turns the inventory pipeline's generated
feeds into a queryable REST API for the public website.
"""

from .app import create_app

__all__ = ["create_app"]
