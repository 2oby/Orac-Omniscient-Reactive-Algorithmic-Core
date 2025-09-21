"""Mapping resolver for entity resolution from grammar terms to HA entities."""

import os
import yaml
import logging
import requests
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UnmappedError(Exception):
    """Raised when a combination has no mapping."""
    pass


class InvalidEntityError(Exception):
    """Raised when a mapped entity doesn't exist in HA."""
    pass


class MappingResolver:
    """Resolves grammar terms to Home Assistant entity IDs using mapping files."""

    def __init__(
        self,
        ha_url: Optional[str] = None,
        ha_token: Optional[str] = None,
        cache_ttl: int = 300
    ):
        """
        Initialize the mapping resolver.

        Args:
            ha_url: Home Assistant URL
            ha_token: Home Assistant API token
            cache_ttl: Cache TTL in seconds (default 5 minutes)
        """
        self.ha_url = ha_url or os.getenv("HA_URL", "http://192.168.8.107:8123")
        self.ha_token = ha_token or os.getenv("HA_TOKEN", "")
        self.cache_ttl = cache_ttl

        # Caches
        self.mapping_cache = {}
        self.entity_cache = {}
        self.entity_cache_time = None

        # Mappings directory
        self.mappings_dir = Path(__file__).parent / "mappings"

    def load_mapping_file(self, topic_id: str) -> Dict:
        """
        Load mapping file for a specific topic.

        Args:
            topic_id: Topic identifier

        Returns:
            Mapping data dictionary
        """
        # Check cache first
        if topic_id in self.mapping_cache:
            return self.mapping_cache[topic_id]

        mapping_file = self.mappings_dir / f"topic_{topic_id}.yaml"

        if not mapping_file.exists():
            logger.error(f"Mapping file not found for topic {topic_id}: {mapping_file}")
            return {}

        try:
            with open(mapping_file, 'r') as f:
                mapping_data = yaml.safe_load(f)

            # Cache the loaded mapping
            self.mapping_cache[topic_id] = mapping_data
            logger.info(f"Loaded mapping file for topic {topic_id}")

            return mapping_data

        except Exception as e:
            logger.error(f"Error loading mapping file: {e}")
            return {}

    def resolve(
        self,
        location: str,
        device: str,
        topic_id: str
    ) -> Optional[str]:
        """
        Resolve location and device to a Home Assistant entity ID.

        Args:
            location: Location from grammar (e.g., "bedroom")
            device: Device from grammar (e.g., "lights")
            topic_id: Topic ID for selecting mapping file

        Returns:
            Entity ID or None if ignored

        Raises:
            UnmappedError: If combination is not mapped
            InvalidEntityError: If entity doesn't exist in HA
        """
        # Load mappings for topic
        mapping_data = self.load_mapping_file(topic_id)

        if not mapping_data:
            raise UnmappedError(f"No mapping data available for topic {topic_id}")

        mappings = mapping_data.get('mappings', {}) if mapping_data else {}

        # Create combination key
        key = f"{location}|{device}"

        # Check if combination exists in mappings
        if key not in mappings:
            # Try alternate formats
            alt_key = f"{device}|{location}"
            if alt_key in mappings:
                key = alt_key
            else:
                raise UnmappedError(f"No mapping found for {key}")

        mapping = mappings[key]

        # Handle special cases
        if mapping == "":
            raise UnmappedError(f"TODO: Map {key} - no entity assigned")

        if mapping == "IGNORE":
            logger.debug(f"Combination {key} is marked as IGNORE")
            return None

        # Validate entity exists
        if not self.entity_exists(mapping):
            raise InvalidEntityError(
                f"Entity {mapping} not found in Home Assistant"
            )

        logger.debug(f"Resolved {key} to {mapping}")
        return mapping

    def resolve_with_fallback(
        self,
        location: str,
        device: str,
        topic_id: str,
        fallback: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve with fallback for unmapped combinations.

        Args:
            location: Location from grammar
            device: Device from grammar
            topic_id: Topic ID
            fallback: Fallback entity ID to use if unmapped

        Returns:
            Entity ID, fallback, or None
        """
        try:
            return self.resolve(location, device, topic_id)
        except UnmappedError as e:
            logger.warning(f"Using fallback for unmapped combination: {e}")
            return fallback
        except InvalidEntityError as e:
            logger.error(f"Invalid entity, using fallback: {e}")
            return fallback

    def entity_exists(self, entity_id: str) -> bool:
        """
        Check if an entity exists in Home Assistant.

        Args:
            entity_id: Entity ID to check

        Returns:
            True if entity exists
        """
        # Update cache if expired
        if self._cache_expired():
            self._update_entity_cache()

        return entity_id in self.entity_cache

    def _cache_expired(self) -> bool:
        """Check if entity cache has expired."""
        if self.entity_cache_time is None:
            return True

        age = datetime.now() - self.entity_cache_time
        return age > timedelta(seconds=self.cache_ttl)

    def _update_entity_cache(self):
        """Update the entity cache from Home Assistant."""
        if not self.ha_token:
            logger.warning("No HA token, skipping entity validation")
            self.entity_cache = {}
            self.entity_cache_time = datetime.now()
            return

        try:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{self.ha_url}/api/states",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                states = response.json()
                self.entity_cache = {
                    state['entity_id']: state
                    for state in states
                }
                self.entity_cache_time = datetime.now()
                logger.debug(f"Updated entity cache with {len(self.entity_cache)} entities")
            else:
                logger.error(f"Failed to fetch entities: {response.status_code}")

        except Exception as e:
            logger.error(f"Error updating entity cache: {e}")

    def get_unmapped_count(self, topic_id: str) -> int:
        """
        Get count of unmapped combinations for a topic.

        Args:
            topic_id: Topic ID

        Returns:
            Number of unmapped combinations
        """
        mapping_data = self.load_mapping_file(topic_id)

        if not mapping_data:
            return 0

        mappings = mapping_data.get('mappings', {}) if mapping_data else {}
        unmapped = sum(1 for v in mappings.values() if v == "")

        return unmapped

    def get_unmapped_combinations(self, topic_id: str) -> List[str]:
        """
        Get list of unmapped combinations for a topic.

        Args:
            topic_id: Topic ID

        Returns:
            List of unmapped combination keys
        """
        mapping_data = self.load_mapping_file(topic_id)

        if not mapping_data:
            return []

        mappings = mapping_data.get('mappings', {}) if mapping_data else {}
        unmapped = [k for k, v in mappings.items() if v == ""]

        return unmapped

    def get_mapping_stats(self, topic_id: str) -> Dict:
        """
        Get statistics about mappings for a topic.

        Args:
            topic_id: Topic ID

        Returns:
            Dictionary with mapping statistics
        """
        mapping_data = self.load_mapping_file(topic_id)

        if not mapping_data:
            return {
                'total': 0,
                'mapped': 0,
                'unmapped': 0,
                'ignored': 0,
                'invalid': 0
            }

        mappings = mapping_data.get('mappings', {}) if mapping_data else {}

        stats = {
            'total': len(mappings),
            'mapped': 0,
            'unmapped': 0,
            'ignored': 0,
            'invalid': 0
        }

        # Update entity cache
        if self._cache_expired():
            self._update_entity_cache()

        for combo, entity in mappings.items():
            if entity == "":
                stats['unmapped'] += 1
            elif entity == "IGNORE":
                stats['ignored'] += 1
            elif entity not in self.entity_cache:
                stats['invalid'] += 1
            else:
                stats['mapped'] += 1

        return stats

    def resolve_action(self, action: str) -> str:
        """
        Resolve action to Home Assistant service.

        Args:
            action: Action from grammar (e.g., "on", "off", "toggle")

        Returns:
            HA service name
        """
        action_map = {
            'on': 'turn_on',
            'off': 'turn_off',
            'toggle': 'toggle',
            'open': 'open_cover',
            'close': 'close_cover',
            'stop': 'stop_cover',
            'lock': 'lock',
            'unlock': 'unlock'
        }

        return action_map.get(action, action)

    def clear_cache(self, topic_id: Optional[str] = None):
        """
        Clear cached mappings.

        Args:
            topic_id: Specific topic to clear, or None for all
        """
        if topic_id:
            self.mapping_cache.pop(topic_id, None)
            logger.info(f"Cleared cache for topic {topic_id}")
        else:
            self.mapping_cache.clear()
            self.entity_cache.clear()
            self.entity_cache_time = None
            logger.info("Cleared all caches")


def test_resolver():
    """Test the mapping resolver."""
    resolver = MappingResolver()

    # Test topic
    test_topic = "test_topic"

    try:
        # Try to resolve a combination
        entity = resolver.resolve("bedroom", "lights", test_topic)
        print(f"Resolved bedroom lights to: {entity}")

        # Get stats
        stats = resolver.get_mapping_stats(test_topic)
        print(f"Mapping stats: {stats}")

        # Get unmapped
        unmapped = resolver.get_unmapped_combinations(test_topic)
        print(f"Unmapped combinations: {unmapped}")

    except UnmappedError as e:
        print(f"Unmapped error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_resolver()