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

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

class EntityType(str, Enum):
    """Types of entities in Home Assistant."""
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    CLIMATE = "climate"
    COVER = "cover"
    FAN = "fan"
    MEDIA_PLAYER = "media_player"
    VACUUM = "vacuum"
    CAMERA = "camera"
    LOCK = "lock"
    ALARM_CONTROL_PANEL = "alarm_control_panel"
    AUTOMATION = "automation"
    SCRIPT = "script"
    SCENE = "scene"
    INPUT_BOOLEAN = "input_boolean"
    INPUT_SELECT = "input_select"
    INPUT_NUMBER = "input_number"
    INPUT_TEXT = "input_text"
    INPUT_DATETIME = "input_datetime"
    PERSON = "person"
    ZONE = "zone"
    GROUP = "group"
    UNKNOWN = "unknown"

class HomeAssistantEntity(BaseModel):
    """Model representing a Home Assistant entity (device, sensor, etc.)."""
    entity_id: str = Field(..., description="Unique identifier for the entity")
    state: str = Field(..., description="Current state of the entity")
    type: EntityType = Field(EntityType.UNKNOWN, description="Type of entity")
    friendly_name: Optional[str] = Field(None, description="User-friendly name")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    last_changed: Optional[str] = Field(None, description="Last state change timestamp")
    area_id: Optional[str] = Field(None, description="Associated area ID")
    device_id: Optional[str] = Field(None, description="Associated device ID")

    class Config:
        """Pydantic model configuration."""
        use_enum_values = True
        allow_population_by_field_name = True

class ServiceParameter(BaseModel):
    """Model for a service parameter."""
    name: str = Field(..., description="Parameter name")
    description: Optional[str] = Field(None, description="Parameter description")
    required: bool = Field(False, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value")
    selector: Optional[Dict[str, Any]] = Field(None, description="UI selector configuration")

class HomeAssistantService(BaseModel):
    """Model representing a Home Assistant service."""
    domain: str = Field(..., description="Service domain (e.g., 'light', 'switch')")
    service: str = Field(..., description="Service name")
    name: Optional[str] = Field(None, description="User-friendly name")
    description: Optional[str] = Field(None, description="Service description")
    target: Optional[Dict[str, Any]] = Field(None, description="Target entity configuration")
    parameters: List[ServiceParameter] = Field(default_factory=list, description="Service parameters")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Additional service fields")

    class Config:
        """Pydantic model configuration."""
        allow_population_by_field_name = True

class HomeAssistantLocation(BaseModel):
    """Model representing a Home Assistant area/location."""
    area_id: str = Field(..., description="Unique identifier for the area")
    name: str = Field(..., description="Area name")
    picture: Optional[str] = Field(None, description="Area picture URL")
    parent_id: Optional[str] = Field(None, description="Parent area ID")
    aliases: List[str] = Field(default_factory=list, description="Alternative names for the area")

class HomeAssistantDevice(BaseModel):
    """Model representing a Home Assistant device."""
    device_id: str = Field(..., description="Unique identifier for the device")
    name: str = Field(..., description="Device name")
    model: Optional[str] = Field(None, description="Device model")
    manufacturer: Optional[str] = Field(None, description="Device manufacturer")
    area_id: Optional[str] = Field(None, description="Associated area ID")
    entities: List[str] = Field(default_factory=list, description="Associated entity IDs")
    configuration_url: Optional[str] = Field(None, description="Device configuration URL")
    entry_type: Optional[str] = Field(None, description="Device entry type")
    identifiers: List[List[str]] = Field(default_factory=list, description="Device identifiers")
    connections: List[List[str]] = Field(default_factory=list, description="Device connections")
    sw_version: Optional[str] = Field(None, description="Software version")
    hw_version: Optional[str] = Field(None, description="Hardware version")
    via_device_id: Optional[str] = Field(None, description="Parent device ID")
