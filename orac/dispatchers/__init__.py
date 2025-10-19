"""
ORAC Dispatcher Package

Provides pluggable dispatchers for executing LLM outputs
through different systems (Home Assistant, etc.)
"""

from .base import BaseDispatcher

__all__ = ['BaseDispatcher']