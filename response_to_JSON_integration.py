#!/usr/bin/env python3
"""
Response to JSON Integration Module for Smart Home Control
This module provides functions to extract structured JSON from model outputs
using regex pattern matching and validation.
"""

import re
import json
import logging
import os
import yaml
from typing import Dict, Any, Optional, List, Set
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logger = logging.getLogger("outlines-service")

# Path to config directory
CONFIG_DIR = os.environ.get("CONFIG_DIR", "config")

class SmartHomeCommand(BaseModel):
    """Schema for smart home commands"""
    device: str = Field(..., description="The target device (e.g., 'lights')")
    location: Optional[str] = Field(None, description="Optional location (e.g., 'kitchen')")
    action: str = Field(..., description="The action to perform (e.g., 'turn_on')")
    value: Optional[str] = Field(None, description="Optional value parameter (e.g., '72', 'jazz music')")

def load_validation_config() -> Dict[str, List[str]]:
    """
    Load validation configuration for supported devices, locations, actions, etc.
    """
    try:
        config_path = os.path.join(CONFIG_DIR, "validation.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Validation config file not found at {config_path}, using defaults")
            return {
                "devices": ["lights", "thermostat", "tv", "music_player", "fan", "blinds", "door"],
                "locations": ["kitchen", "living room", "bedroom", "bathroom", "office", "hallway"],
                "actions": ["turn_on", "turn_off", "set", "adjust", "open", "close", "play", "pause"],
                "synonyms": {
                    "locations": {
                        "all rooms": ["kitchen", "living room", "bedroom", "bathroom", "office", "hallway"],
                        "house": ["kitchen", "living room", "bedroom", "bathroom", "office", "hallway"]
                    }
                }
            }
    except Exception as e:
        logger.error(f"Error loading validation config: {e}")
        return {}

def load_prompt_template(model_id: str) -> Optional[str]:
    """
    Load model-specific prompt template from config directory
    
    Args:
        model_id: The model identifier (e.g., 'distilgpt2', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0')
    
    Returns:
        The prompt template as a string, or None if not found
    """
    # Clean the model_id to create a valid filename
    clean_model_id = model_id.replace('/', '_').replace('.', '_').replace('-', '_').lower()
    
    # First try exact model ID match
    template_path = os.path.join(CONFIG_DIR, f"prompt_{clean_model_id}.txt")
    
    if not os.path.exists(template_path):
        # Try to find a generic template for the model family
        if "gpt2" in model_id.lower():
            template_path = os.path.join(CONFIG_DIR, "prompt_gpt2.txt")
        elif "llama" in model_id.lower():
            template_path = os.path.join(CONFIG_DIR, "prompt_llama.txt")
        else:
            # Default template
            template_path = os.path.join(CONFIG_DIR, "prompt_default.txt")
    
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read()
        else:
            logger.warning(f"Prompt template not found for {model_id} at {template_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading prompt template for {model_id}: {e}")
        return None

def create_prompt(user_query: str, model_id: str = None) -> str:
    """
    Create a model-specific prompt for the user query
    
    Args:
        user_query: The user's command (e.g., "Turn on the kitchen lights")
        model_id: Optional model identifier for model-specific prompts
    
    Returns:
        The formatted prompt string
    """
    # Load model-specific template if available
    template = None
    if model_id:
        template = load_prompt_template(model_id)
    
    # Fall back to default template if needed
    if not template:
        template = """You are a smart home assistant. Convert the following command into a structured JSON object.

USER COMMAND: "{command}"

Your task is to generate a JSON object that matches the specified schema. Do not include any additional text or explanations; just output the JSON object.

The JSON object should have these fields:
- device: the device to control (e.g., "lights", "thermostat", "tv")
- location: where the device is (e.g., "kitchen", "bedroom") or null if unspecified
- action: the action to perform (e.g., "turn_on", "turn_off", "set", "adjust")
- value: any additional value (e.g., temperature value, brightness level) or null if none

Examples:
- For "Turn on the kitchen lights":
  {{"device": "lights", "location": "kitchen", "action": "turn_on", "value": null}}
- For "Set the living room thermostat to 72 degrees":
  {{"device": "thermostat", "location": "living room", "action": "set", "value": "72"}}
- For "Play some jazz music":
  {{"device": "music_player", "location": null, "action": "play", "value": "jazz music"}}

So, for the command "{command}", produce the corresponding JSON object.
JSON OUTPUT:
"""
    
    # Format the template with the user's command
    return template.format(command=user_query)

def normalize_location(location: str, validation_config: Dict[str, Any]) -> Optional[str]:
    """
    Normalize location names, handling synonyms
    
    Args:
        location: The location string from the parsed command
        validation_config: The validation configuration
    
    Returns:
        Normalized location string or the original if no normalization needed
    """
    if not location:
        return None
        
    # Lowercase for case-insensitive matching
    location_lower = location.lower()
    
    # Check if this is a known valid location
    locations = validation_config.get("locations", [])
    if location_lower in [loc.lower() for loc in locations]:
        # Return it with original casing from the validation list if possible
        for loc in locations:
            if loc.lower() == location_lower:
                return loc
        return location  # Fallback to original
    
    # Check synonyms
    synonyms = validation_config.get("synonyms", {}).get("locations", {})
    for synonym, expansions in synonyms.items():
        if synonym.lower() == location_lower:
            # For now, we'll just use the first location in the expansion list
            # In a real system, this might require additional context or user clarification
            if expansions and len(expansions) > 0:
                logger.info(f"Expanded location '{location}' to '{expansions[0]}'")
                return expansions[0]
    
    # No normalization needed/possible
    return location

def extract_json_from_text(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract and validate JSON from raw model output
    
    Args:
        raw_text: Raw text output from the model
    
    Returns:
        A validated dictionary containing the command parameters or None if extraction fails
    """
    if not raw_text:
        logger.warning("No text to extract JSON from")
        return None
    
    logger.debug(f"Extracting JSON from text: {raw_text}")
    
    # Look for JSON OUTPUT: marker and extract content after it
    json_output_marker = "JSON OUTPUT:"
    json_start_idx = raw_text.find(json_output_marker)
    if json_start_idx >= 0:
        raw_text = raw_text[json_start_idx + len(json_output_marker):].strip()
    
    # Try to find JSON object patterns in the text
    json_pattern = r'({[\s\S]*?})'
    
    # Strategy 1: Find all JSON-like patterns and try them one by one
    potential_jsons = re.findall(json_pattern, raw_text)
    
    for json_str in potential_jsons:
        try:
            # Try to parse this as JSON
            parsed_json = json.loads(json_str)
            
            # Validate with our schema
            command = SmartHomeCommand(**parsed_json)
            logger.info(f"Successfully extracted JSON: {command.model_dump()}")
            return command.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            logger.debug(f"JSON validation failed for: {json_str}, error: {str(e)}")
            continue
    
    # Strategy 2: If we couldn't find valid JSON objects, try to extract individual fields
    logger.debug("No valid JSON found, attempting field extraction")
    
    # Define patterns for individual fields
    field_patterns = {
        'device': r'"device"\s*:\s*"([^"]+)"',
        'location': r'"location"\s*:\s*"?([^",}]+)"?',  # Handle null or string
        'action': r'"action"\s*:\s*"([^"]+)"',
        'value': r'"value"\s*:\s*"?([^",}]+)"?'  # Handle null or string or number
    }
    
    extracted_fields = {}
    
    for field, pattern in field_patterns.items():
        match = re.search(pattern, raw_text)
        if match:
            value = match.group(1).strip()
            if value.lower() == 'null' or value == '':
                if field in ['location', 'value']:
                    # These fields can be null
                    extracted_fields[field] = None
                else:
                    # Required fields can't be null
                    logger.debug(f"Required field '{field}' is null")
            else:
                extracted_fields[field] = value
    
    # Ensure required fields are present
    if 'device' in extracted_fields and 'action' in extracted_fields:
        # Add null for optional fields if missing
        if 'location' not in extracted_fields:
            extracted_fields['location'] = None
        if 'value' not in extracted_fields:
            extracted_fields['value'] = None
            
        try:
            # Validate with our schema
            command = SmartHomeCommand(**extracted_fields)
            logger.info(f"Successfully extracted fields: {command.model_dump()}")
            return command.model_dump()
        except ValidationError as e:
            logger.warning(f"Extracted fields validation failed: {str(e)}")
    
    logger.warning("Failed to extract valid JSON or fields")
    return None

def process_command(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Process a model's raw text output into a structured command
    
    Args:
        raw_text: Raw text output from the model
    
    Returns:
        A validated and normalized command dictionary or None if processing fails
    """
    # Extract the initial JSON
    command_json = extract_json_from_text(raw_text)
    if not command_json:
        return None
    
    # Load validation configuration
    validation_config = load_validation_config()
    
    # Normalize location if present
    if command_json.get('location'):
        command_json['location'] = normalize_location(
            command_json['location'], 
            validation_config
        )
    
    # Additional normalization could be done here for devices, actions, values
    
    return command_json

async def generate_json_from_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Asynchronous wrapper for processing the command
    
    Args:
        raw_text: Raw text output from the model
        
    Returns:
        A processed command dictionary or None if processing fails
    """
    try:
        return process_command(raw_text)
    except Exception as e:
        logger.error(f"Error generating JSON from response: {str(e)}")
        return None
