"""
Home Assistant Dispatcher

Dispatcher that controls Home Assistant devices by parsing
JSON output from the LLM and executing the appropriate actions.
"""

import os
import json
import requests
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from .base import BaseDispatcher
from .mapping_resolver import MappingResolver, UnmappedError, InvalidEntityError
from .mapping_generator import MappingGenerator

logger = logging.getLogger(__name__)


class HomeAssistantDispatcher(BaseDispatcher):
    """
    Home Assistant dispatcher that parses JSON commands.
    
    Parses JSON output from LLM with device/action/location fields
    and controls the appropriate Home Assistant entities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Home Assistant dispatcher.

        Args:
            config: Optional configuration (can override HA_URL and HA_TOKEN)
        """
        super().__init__(config)

        # Get configuration from environment or config dict
        self.ha_url = config.get('ha_url') if config else None
        self.ha_token = config.get('ha_token') if config else None

        # Fall back to environment variables (using correct HA_URL)
        if not self.ha_url:
            self.ha_url = os.getenv('HA_URL', 'http://192.168.8.99:8123')
        if not self.ha_token:
            self.ha_token = os.getenv('HA_TOKEN', '')

        # Initialize mapping system
        self.resolver = MappingResolver(self.ha_url, self.ha_token)
        self.generator = MappingGenerator(self.ha_url, self.ha_token)

        # Timing tracking
        self.last_command_timing = {}

        # Legacy entity mappings (for backward compatibility)
        self.entity_mappings = {
            'living room': {
                'lights': 'switch.tretakt_smart_plug'
            },
            'lounge': {
                'lights': 'switch.tretakt_smart_plug'
            }
        }
    
    def execute(self, llm_output: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the LLM output by parsing JSON and calling HA API.

        Args:
            llm_output: The raw output from the LLM (expected to be JSON)
            context: Optional context (topic configuration, etc.)

        Returns:
            A dictionary with execution results
        """
        try:
            # Start timing
            start_time = datetime.now()
            self.last_command_timing = {'dispatcher_start': start_time.isoformat()}

            logger.info(f"HomeAssistantDispatcher executing with output: {llm_output}")

            # Parse JSON output from LLM
            try:
                command = json.loads(llm_output.strip())
                logger.debug(f"Parsed command: {command}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return {
                    'success': False,
                    'result': None,
                    'error': f'Invalid JSON output from LLM: {str(e)}'
                }

            # Extract fields from JSON
            device = command.get('device', '').lower()
            action = command.get('action', '').lower()
            location = command.get('location', '').lower()

            logger.info(f"Command details - Device: {device}, Action: {action}, Location: {location}")

            # Get topic ID from context for mapping resolution
            topic_id = None
            if context:
                topic_id = context.get('topic_id') or context.get('topic', {}).get('id')

            # Resolve action to HA service
            service = self.resolver.resolve_action(action)
            if not service:
                logger.warning(f"Unknown action: {action}")
                return {
                    'success': False,
                    'result': None,
                    'error': f'Unknown action: {action}'
                }

            # Try to resolve entity using new mapping system
            entity_id = None
            mapping_source = "unmapped"

            if topic_id:
                try:
                    # Check if mapping file exists, generate if not
                    mapping_file = self.resolver.mappings_dir / f"topic_{topic_id}.yaml"
                    if not mapping_file.exists() and context and 'grammar_file' in context:
                        logger.info(f"Generating mapping file for topic {topic_id}")
                        self.generator.generate_mapping_file(
                            context['grammar_file'],
                            topic_id
                        )

                    # Resolve entity using mapping system
                    entity_id = self.resolver.resolve(location, device, topic_id)
                    mapping_source = "mapping_file"
                    logger.info(f"Resolved entity via mapping: {entity_id}")

                except UnmappedError as e:
                    logger.warning(f"Unmapped combination: {e}")
                    # Fall through to legacy mapping
                except InvalidEntityError as e:
                    logger.error(f"Invalid entity: {e}")
                    # Fall through to legacy mapping

            # Fall back to legacy mappings if new system didn't resolve
            if not entity_id:
                if location in self.entity_mappings:
                    if device in self.entity_mappings[location]:
                        entity_id = self.entity_mappings[location][device]
                        mapping_source = "legacy"
                        logger.info(f"Found legacy entity mapping: {entity_id}")

            # Final fallback
            if not entity_id:
                logger.warning(f"No entity mapping for {device} in {location}")
                # Fallback to lounge lamp for any light command
                if device == 'lights':
                    entity_id = 'switch.tretakt_smart_plug'
                    mapping_source = "fallback"
                    logger.info(f"Using fallback entity: {entity_id}")
                else:
                    return {
                        'success': False,
                        'result': None,
                        'error': f'No entity mapping found for {device} in {location}'
                    }

            # Determine domain from entity_id
            domain = entity_id.split('.')[0]

            # Record pre-API call timing
            self.last_command_timing['ha_api_call'] = datetime.now().isoformat()

            # Call Home Assistant API
            logger.info(f"Calling HA service: {domain}/{service} for entity {entity_id}")
            result = self._call_ha_service(domain, service, entity_id)

            # Record completion timing
            end_time = datetime.now()
            self.last_command_timing['ha_response'] = end_time.isoformat()
            self.last_command_timing['dispatcher_complete'] = end_time.isoformat()

            # Calculate duration
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return {
                'success': True,
                'result': {
                    'entity': entity_id,
                    'action': service,
                    'command': command,
                    'ha_response': result,
                    'mapping_source': mapping_source,
                    'timing': {
                        'duration_ms': duration_ms,
                        'timestamps': self.last_command_timing
                    }
                },
                'error': None
            }

        except Exception as e:
            logger.error(f"Error in HomeAssistantDispatcher: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    def _call_ha_service(self, domain: str, service: str, entity_id: str) -> Dict[str, Any]:
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., 'light')
            service: Service name (e.g., 'turn_on')
            entity_id: Entity to control
        
        Returns:
            Response from Home Assistant
        """
        url = f"{self.ha_url}/api/services/{domain}/{service}"
        headers = {
            'Authorization': f'Bearer {self.ha_token}',
            'Content-Type': 'application/json'
        }
        data = {
            'entity_id': entity_id
        }
        
        logger.info(f"Calling HA API: {url} with entity: {entity_id}")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        return response.json() if response.text else {'status': 'success'}
    
    def get_mapping_stats(self, topic_id: str) -> Dict[str, Any]:
        """
        Get mapping statistics for a topic.

        Args:
            topic_id: Topic ID to get stats for

        Returns:
            Dictionary with mapping statistics
        """
        return self.resolver.get_mapping_stats(topic_id)

    def refresh_mappings(self, topic_id: str, grammar_file: str) -> bool:
        """
        Refresh mappings for a topic with new HA entities.

        Args:
            topic_id: Topic ID
            grammar_file: Path to grammar file

        Returns:
            True if successful
        """
        try:
            # Generate or update mapping file
            mapping_file = self.generator.generate_mapping_file(
                grammar_file,
                topic_id,
                force=False
            )

            # Update with new entities
            new_count = self.generator.update_with_new_entities(mapping_file)

            # Clear cache for this topic
            self.resolver.clear_cache(topic_id)

            logger.info(f"Refreshed mappings for topic {topic_id}, {new_count} new entities")
            return True

        except Exception as e:
            logger.error(f"Error refreshing mappings: {e}")
            return False

    @property
    def name(self) -> str:
        """Return the display name of this dispatcher."""
        return "Home Assistant"

    @property
    def description(self) -> str:
        """Return a brief description of what this dispatcher does."""
        return "Controls Home Assistant devices via JSON commands using grammar-aware mappings"