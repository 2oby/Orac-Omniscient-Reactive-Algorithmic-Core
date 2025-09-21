"""Mapping file generator for dispatcher entity mappings."""

import os
import yaml
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from ..grammars import GBNFParser

logger = logging.getLogger(__name__)


class MappingGenerator:
    """Generates and maintains mapping files between grammar terms and HA entities."""

    def __init__(self, ha_url: Optional[str] = None, ha_token: Optional[str] = None):
        """
        Initialize the mapping generator.

        Args:
            ha_url: Home Assistant URL (defaults to env var)
            ha_token: Home Assistant API token (defaults to env var)
        """
        self.ha_url = ha_url or os.getenv("HA_URL", "http://192.168.8.107:8123")
        self.ha_token = ha_token or os.getenv("HA_TOKEN", "")
        self.parser = GBNFParser()
        self.mappings_dir = Path(__file__).parent / "mappings"
        self.mappings_dir.mkdir(exist_ok=True)

    def generate_mapping_file(
        self,
        grammar_file: str,
        topic_id: str,
        force: bool = False
    ) -> str:
        """
        Generate a YAML mapping file from a grammar file.

        Args:
            grammar_file: Path to GBNF grammar file
            topic_id: Topic identifier for naming the mapping file
            force: Force regeneration even if file exists

        Returns:
            Path to generated mapping file
        """
        mapping_file = self.mappings_dir / f"topic_{topic_id}.yaml"

        # Check if file exists and force is False
        if mapping_file.exists() and not force:
            logger.info(f"Mapping file already exists: {mapping_file}")
            return str(mapping_file)

        # Parse grammar to get vocabulary
        grammar = self.parser.parse_grammar(grammar_file)
        if not grammar:
            logger.error(f"Failed to parse grammar file: {grammar_file}")
            return ""

        # Get all combinations
        combinations = self.parser.get_combinations(grammar)

        # Fetch available HA entities
        ha_entities = self.fetch_ha_entities()

        # Load existing mappings if file exists
        existing_mappings = {}
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                existing_data = yaml.safe_load(f)
                if existing_data and 'mappings' in existing_data:
                    existing_mappings = existing_data['mappings']

        # Generate mapping structure
        mapping_data = {
            'metadata': {
                'grammar_file': grammar_file,
                'topic_id': topic_id,
                'generated': datetime.now().isoformat(),
                'last_ha_sync': datetime.now().isoformat(),
                'unmapped_count': 0
            },
            'mappings': {},
            'available_entities': ha_entities
        }

        # Create mappings with existing values preserved
        unmapped_count = 0
        for combo in combinations:
            if combo in existing_mappings:
                # Preserve existing mapping
                mapping_data['mappings'][combo] = existing_mappings[combo]
            else:
                # New combination, mark as TODO
                mapping_data['mappings'][combo] = ""
                unmapped_count += 1

        mapping_data['metadata']['unmapped_count'] = unmapped_count

        # Add header comments
        yaml_content = self._generate_yaml_with_comments(mapping_data, ha_entities)

        # Write to file
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        logger.info(f"Generated mapping file: {mapping_file} with {unmapped_count} unmapped items")
        return str(mapping_file)

    def fetch_ha_entities(self) -> Dict[str, List[str]]:
        """
        Fetch all entities from Home Assistant API.

        Returns:
            Dictionary categorized by entity type
        """
        entities = {
            'lights': [],
            'switches': [],
            'climate': [],
            'covers': [],
            'sensors': [],
            'binary_sensors': [],
            'scenes': [],
            'scripts': [],
            'automations': []
        }

        if not self.ha_token:
            logger.warning("No HA token configured, returning empty entity list")
            return entities

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

                for state in states:
                    entity_id = state['entity_id']
                    domain = entity_id.split('.')[0]

                    # Categorize by domain
                    if domain == 'light':
                        entities['lights'].append(entity_id)
                    elif domain == 'switch':
                        entities['switches'].append(entity_id)
                    elif domain == 'climate':
                        entities['climate'].append(entity_id)
                    elif domain == 'cover':
                        entities['covers'].append(entity_id)
                    elif domain == 'sensor':
                        entities['sensors'].append(entity_id)
                    elif domain == 'binary_sensor':
                        entities['binary_sensors'].append(entity_id)
                    elif domain == 'scene':
                        entities['scenes'].append(entity_id)
                    elif domain == 'script':
                        entities['scripts'].append(entity_id)
                    elif domain == 'automation':
                        entities['automations'].append(entity_id)

                logger.info(f"Fetched {sum(len(v) for v in entities.values())} entities from HA")
            else:
                logger.error(f"Failed to fetch HA entities: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching HA entities: {e}")

        return entities

    def update_with_new_entities(self, mapping_file: str) -> int:
        """
        Update mapping file with newly discovered HA entities.

        Args:
            mapping_file: Path to existing mapping file

        Returns:
            Number of new entities added
        """
        if not Path(mapping_file).exists():
            logger.error(f"Mapping file not found: {mapping_file}")
            return 0

        # Load existing mapping
        with open(mapping_file, 'r') as f:
            mapping_data = yaml.safe_load(f)

        # Fetch current HA entities
        current_entities = self.fetch_ha_entities()

        # Compare with stored entities
        stored_entities = mapping_data.get('available_entities', {})
        new_entities = self._find_new_entities(stored_entities, current_entities)

        if not new_entities:
            logger.info("No new entities found")
            return 0

        # Update mapping file
        mapping_data['available_entities'] = current_entities
        mapping_data['metadata']['last_ha_sync'] = datetime.now().isoformat()

        # Generate updated YAML with new entities highlighted
        yaml_content = self._generate_yaml_with_comments(
            mapping_data,
            current_entities,
            new_entities=new_entities
        )

        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        new_count = sum(len(v) for v in new_entities.values())
        logger.info(f"Added {new_count} new entities to mapping file")
        return new_count

    def _find_new_entities(
        self,
        stored: Dict[str, List[str]],
        current: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Find entities that are in current but not in stored."""
        new_entities = {}

        for category, current_list in current.items():
            stored_list = stored.get(category, [])
            new_items = [e for e in current_list if e not in stored_list]

            if new_items:
                new_entities[category] = new_items

        return new_entities

    def _generate_yaml_with_comments(
        self,
        mapping_data: Dict,
        ha_entities: Dict,
        new_entities: Optional[Dict] = None
    ) -> str:
        """
        Generate YAML content with helpful comments.

        Args:
            mapping_data: The mapping data structure
            ha_entities: Available HA entities
            new_entities: Newly discovered entities to highlight

        Returns:
            YAML string with comments
        """
        lines = []

        # Header
        lines.append(f"# Dispatcher mapping for topic: {mapping_data['metadata']['topic_id']}")
        lines.append(f"# Auto-generated from: {mapping_data['metadata']['grammar_file']}")
        lines.append(f"# Generated: {mapping_data['metadata']['generated']}")
        lines.append(f"# Last HA Sync: {mapping_data['metadata']['last_ha_sync']}")
        lines.append("")

        # Metadata
        lines.append("metadata:")
        for key, value in mapping_data['metadata'].items():
            if isinstance(value, str) and ' ' in value:
                lines.append(f'  {key}: "{value}"')
            else:
                lines.append(f"  {key}: {value}")
        lines.append("")

        # Mappings
        lines.append("mappings:")
        lines.append("  # Format: \"location|device\": \"entity_id\"")
        lines.append("  # Use \"IGNORE\" to skip a combination")
        lines.append("  # Leave empty \"\" for TODO items")
        lines.append("")

        for combo, entity in sorted(mapping_data['mappings'].items()):
            if entity == "":
                lines.append(f'  "{combo}": ""  # TODO: Map this')
            elif entity == "IGNORE":
                lines.append(f'  "{combo}": "IGNORE"  # Explicitly ignored')
            else:
                lines.append(f'  "{combo}": "{entity}"')
        lines.append("")

        # New entities section (if any)
        if new_entities:
            lines.append("# NEW ENTITIES DISCOVERED")
            lines.append(f"# Added: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append("# Uncomment and map if needed:")
            for category, entities in new_entities.items():
                lines.append(f"# {category}:")
                for entity in entities:
                    lines.append(f"#   - {entity}")
            lines.append("")

        # Available entities
        lines.append("# AVAILABLE HOME ASSISTANT ENTITIES")
        lines.append(f"# Fetched: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("available_entities:")

        has_entities = any(entities for entities in ha_entities.values())
        if has_entities:
            for category, entities in ha_entities.items():
                if entities:
                    lines.append(f"  {category}:")
                    for entity in sorted(entities):
                        # Mark new entities
                        if new_entities and entity in new_entities.get(category, []):
                            lines.append(f"    - {entity}  # NEW")
                        else:
                            lines.append(f"    - {entity}")
        else:
            # No entities available, create empty dict
            lines.append("  {}")

        return '\n'.join(lines)

    def validate_mappings(self, mapping_file: str) -> Dict[str, List[str]]:
        """
        Validate all mappings in a file.

        Args:
            mapping_file: Path to mapping file

        Returns:
            Dictionary of validation results
        """
        results = {
            'unmapped': [],
            'invalid_entities': [],
            'valid': []
        }

        if not Path(mapping_file).exists():
            logger.error(f"Mapping file not found: {mapping_file}")
            return results

        with open(mapping_file, 'r') as f:
            mapping_data = yaml.safe_load(f)

        if not mapping_data:
            logger.error(f"Empty or invalid mapping file: {mapping_file}")
            return results

        # Fetch current entities
        ha_entities = self.fetch_ha_entities()
        all_entities = set()
        for entity_list in ha_entities.values():
            all_entities.update(entity_list)

        # Check each mapping
        for combo, entity in mapping_data.get('mappings', {}).items():
            if entity == "":
                results['unmapped'].append(combo)
            elif entity == "IGNORE":
                results['valid'].append(combo)
            elif entity not in all_entities:
                results['invalid_entities'].append(f"{combo} -> {entity}")
            else:
                results['valid'].append(combo)

        return results


def test_generator():
    """Test the mapping generator."""
    generator = MappingGenerator()

    # Test with a real grammar file
    grammar_file = "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core/data/grammars/static_actions.gbnf"

    if Path(grammar_file).exists():
        # Generate mapping file
        mapping_file = generator.generate_mapping_file(
            grammar_file,
            "test_topic",
            force=True
        )

        print(f"Generated mapping file: {mapping_file}")

        # Validate mappings
        results = generator.validate_mappings(mapping_file)
        print(f"Validation results: {results}")
    else:
        print(f"Grammar file not found: {grammar_file}")


if __name__ == "__main__":
    test_generator()