"""
ORAC Dispatcher Package

Provides pluggable dispatchers for executing LLM outputs
through different systems (Home Assistant, etc.)
"""

from .base import BaseDispatcher
from .registry import dispatcher_registry

__all__ = ['BaseDispatcher', 'dispatcher_registry']