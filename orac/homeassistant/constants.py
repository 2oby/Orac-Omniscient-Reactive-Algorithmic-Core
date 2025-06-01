"""
Constants for Home Assistant integration.

This module defines truly constant values used throughout the Home Assistant integration,
including API endpoints, entity types, and error messages. These values should never
change during runtime.
"""

# API Endpoints
API_STATES = "/api/states"
API_SERVICES = "/api/services"
API_AREAS = "/api/areas"

# Grammar Configuration
GRAMMAR_FILE = "data/grammars.yaml"
GRAMMAR_SECTION = "grammars"
CONSTRAINTS_SECTION = "home_automation_constraints"
MAPPING_SECTION = "mapping"

# Entity Types
ENTITY_TYPE_LIGHT = "light"
ENTITY_TYPE_SWITCH = "switch"
ENTITY_TYPE_COVER = "cover"
ENTITY_TYPE_CLIMATE = "climate"
ENTITY_TYPE_SENSOR = "sensor"

# Service Domains
DOMAIN_LIGHT = "light"
DOMAIN_SWITCH = "switch"
DOMAIN_COVER = "cover"
DOMAIN_CLIMATE = "climate"

# Error Messages
ERROR_INVALID_COMMAND = "Invalid command or device"
ERROR_CONNECTION = "Failed to connect to Home Assistant"
ERROR_AUTHENTICATION = "Authentication failed"
ERROR_SERVICE_CALL = "Service call failed" 