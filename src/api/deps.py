"""Shared router dependencies."""

from __future__ import annotations

from fastapi import Request

from .feeds import FeedStore


def get_store(request: Request) -> FeedStore:
    """The per-process feed store, attached in the app factory."""
    return request.app.state.store
