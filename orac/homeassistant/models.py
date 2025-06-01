# This file will contain the data models for Home Assistant integration, including:
# - EntityType enum for different types of entities
# - HomeAssistantEntity for representing devices and sensors
# - HomeAssistantService for representing available actions
# - HomeAssistantLocation for representing rooms/areas
# - HomeAssistantDevice for representing physical devices

"""
Data models for Home Assistant integration.

This module defines Pydantic models for representing Home Assistant data structures,
including:
- HomeAssistantEntity: Represents devices, sensors, and their states
- HomeAssistantService: Represents available actions and their parameters
- HomeAssistantLocation: Represents areas/rooms and their relationships
- HomeAssistantDevice: Represents physical devices and their groupings

These models support:
- Entity discovery and state management
- Service discovery and parameter validation
- Location/area management
- Device grouping for user-friendly commands
- Type safety and validation
"""
