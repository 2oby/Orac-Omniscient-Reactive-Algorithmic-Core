import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import logging

from orac.topic_models.topic import Topic, TopicSettings, GrammarConfig

logger = logging.getLogger(__name__)


class TopicManager:
    """Manages topic configurations and operations"""
    
    def __init__(self, data_dir: str = None):
        """Initialize the topic manager
        
        Args:
            data_dir: Directory to store topic configurations
        """
        if data_dir is None:
            # Check if DATA_DIR environment variable is set (from docker-compose)
            data_dir = os.getenv('DATA_DIR')
            if not data_dir:
                # Fall back to default relative to this file
                base_dir = Path(__file__).parent.parent
                data_dir = base_dir / "data"
        
        self.data_dir = Path(data_dir)
        self.topics_file = self.data_dir / "topics.yaml"
        self.topics: Dict[str, Topic] = {}
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        logger.info(f"TopicManager using data directory: {self.data_dir}")
        logger.info(f"Topics file path: {self.topics_file}")
        
        # Load existing topics
        self.load_topics()
        
        # Ensure default topic exists
        self._ensure_default_topic()
    
    def load_topics(self) -> None:
        """Load topics from YAML file"""
        logger.info(f"Attempting to load topics from {self.topics_file}")
        
        if not self.topics_file.exists():
            logger.info(f"Topics file does not exist at {self.topics_file}, creating empty topics")
            self.topics = {}
            return
        
        try:
            with open(self.topics_file, 'r') as f:
                data = yaml.safe_load(f) or {}
                topics_data = data.get('topics', {})
                
                logger.info(f"Found {len(topics_data)} topics in file")
                
                self.topics = {}
                for topic_id, topic_data in topics_data.items():
                    try:
                        # Handle datetime fields specially
                        if 'first_seen' in topic_data and isinstance(topic_data['first_seen'], str):
                            topic_data['first_seen'] = datetime.fromisoformat(topic_data['first_seen'])
                        if 'last_used' in topic_data and isinstance(topic_data['last_used'], str):
                            topic_data['last_used'] = datetime.fromisoformat(topic_data['last_used'])
                        
                        # Ensure nested objects exist
                        if 'settings' not in topic_data:
                            topic_data['settings'] = {}
                        if 'grammar' not in topic_data:
                            topic_data['grammar'] = {}
                        
                        self.topics[topic_id] = Topic(**topic_data)
                        # Log more details about loaded topic
                        if topic_id == 'general' and 'settings' in topic_data:
                            system_prompt = topic_data.get('settings', {}).get('system_prompt', 'N/A')
                            logger.info(f"Loaded topic: {topic_id} with system prompt: {system_prompt[:50]}...")
                        else:
                            logger.info(f"Loaded topic: {topic_id}")
                    except Exception as e:
                        logger.error(f"Failed to load topic {topic_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to load topics file: {e}")
            self.topics = {}
    
    def save_topics(self) -> None:
        """Save topics to YAML file"""
        try:
            topics_data = {}
            for topic_id, topic in self.topics.items():
                topic_dict = topic.dict()
                # Convert datetime objects to ISO format strings
                if topic_dict.get('first_seen'):
                    topic_dict['first_seen'] = topic_dict['first_seen'].isoformat()
                if topic_dict.get('last_used'):
                    topic_dict['last_used'] = topic_dict['last_used'].isoformat()
                topics_data[topic_id] = topic_dict
            
            data = {'topics': topics_data}
            
            with open(self.topics_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Saved {len(self.topics)} topics to {self.topics_file}")
        except Exception as e:
            logger.error(f"Failed to save topics: {e}")
            raise
    
    def _ensure_default_topic(self) -> None:
        """Ensure the default 'general' topic exists"""
        if 'general' not in self.topics:
            logger.info("Creating default 'general' topic")
            # Only create a new general topic if topics.yaml doesn't exist
            # This prevents overwriting user customizations after container restart
            self.topics['general'] = Topic(
                name="General",
                description="General purpose AI assistant",
                enabled=True,
                model="Qwen3-0.6B-Q8_0.gguf",  # Default model
                settings=TopicSettings(
                    system_prompt="You are a helpful AI assistant.",
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    max_tokens=500
                ),
                grammar=GrammarConfig(enabled=False),
                auto_discovered=False,
                first_seen=datetime.now(),
                last_used=None
            )
            self.save_topics()
        else:
            logger.info(f"General topic already exists with system prompt: {self.topics['general'].settings.system_prompt[:50]}...")
    
    def get_topic(self, topic_id: str) -> Optional[Topic]:
        """Get a topic by ID
        
        Args:
            topic_id: The topic identifier
            
        Returns:
            Topic instance or None if not found
        """
        return self.topics.get(topic_id)
    
    def create_topic(self, topic_id: str, topic_data: Dict[str, Any], auto_discovered: bool = False) -> Topic:
        """Create a new topic
        
        Args:
            topic_id: Unique identifier for the topic
            topic_data: Topic configuration data
            auto_discovered: Whether this topic was auto-created
            
        Returns:
            Created Topic instance
        """
        if topic_id in self.topics:
            raise ValueError(f"Topic '{topic_id}' already exists")
        
        # Add metadata
        topic_data['auto_discovered'] = auto_discovered
        topic_data['first_seen'] = datetime.now()
        
        # Ensure required fields have defaults
        if 'name' not in topic_data:
            topic_data['name'] = topic_id.replace('_', ' ').title()
        if 'model' not in topic_data:
            topic_data['model'] = "Qwen3-0.6B-Q8_0.gguf"  # Default model
        
        topic = Topic(**topic_data)
        self.topics[topic_id] = topic
        self.save_topics()
        
        logger.info(f"Created topic: {topic_id} (auto_discovered={auto_discovered})")
        return topic
    
    def update_topic(self, topic_id: str, topic_data: Dict[str, Any]) -> Topic:
        """Update an existing topic
        
        Args:
            topic_id: Topic identifier
            topic_data: Updated configuration data
            
        Returns:
            Updated Topic instance
        """
        if topic_id not in self.topics:
            raise ValueError(f"Topic '{topic_id}' does not exist")
        
        # Preserve metadata fields
        existing_topic = self.topics[topic_id]
        topic_data['auto_discovered'] = existing_topic.auto_discovered
        topic_data['first_seen'] = existing_topic.first_seen
        
        # Update the topic
        self.topics[topic_id] = Topic(**topic_data)
        self.save_topics()
        
        logger.info(f"Updated topic: {topic_id}")
        return self.topics[topic_id]
    
    def delete_topic(self, topic_id: str) -> bool:
        """Delete a topic
        
        Args:
            topic_id: Topic identifier
            
        Returns:
            True if deleted, False if not found
        """
        if topic_id == 'general':
            raise ValueError("Cannot delete the default 'general' topic")
        
        if topic_id in self.topics:
            del self.topics[topic_id]
            self.save_topics()
            logger.info(f"Deleted topic: {topic_id}")
            return True
        return False
    
    def mark_topic_used(self, topic_id: str) -> None:
        """Mark a topic as used (update last_used timestamp)
        
        Args:
            topic_id: Topic identifier
        """
        if topic_id in self.topics:
            self.topics[topic_id].last_used = datetime.now()
            self.save_topics()
    
    def auto_discover_topic(self, topic_id: str) -> Topic:
        """Auto-discover and create a new topic with default settings
        
        Args:
            topic_id: Topic identifier
            
        Returns:
            Newly created Topic instance
        """
        logger.info(f"Auto-discovering topic: {topic_id}")
        
        # Create with default settings similar to general topic
        topic_data = {
            'name': topic_id.replace('_', ' ').title(),
            'description': f"Auto-discovered topic for {topic_id}",
            'enabled': True,
            'model': "Qwen3-0.6B-Q8_0.gguf",
            'settings': {
                'system_prompt': f"You are an AI assistant specialized in {topic_id.replace('_', ' ')}.",
                'temperature': 0.7,
                'top_p': 0.9,
                'top_k': 40,
                'max_tokens': 500
            },
            'grammar': {
                'enabled': False
            }
        }
        
        return self.create_topic(topic_id, topic_data, auto_discovered=True)
    
    def list_topics(self) -> Dict[str, Topic]:
        """Get all topics
        
        Returns:
            Dictionary of topic_id -> Topic
        """
        return self.topics.copy()
    
    def get_available_models(self) -> list:
        """Get list of available models from model configs
        
        Returns:
            List of model filenames
        """
        model_configs_file = self.data_dir / "model_configs.yaml"
        
        if not model_configs_file.exists():
            return ["Qwen3-0.6B-Q8_0.gguf"]  # Default fallback
        
        try:
            with open(model_configs_file, 'r') as f:
                data = yaml.safe_load(f) or {}
                models = list(data.get('models', {}).keys())
                return models if models else ["Qwen3-0.6B-Q8_0.gguf"]
        except Exception as e:
            logger.error(f"Failed to load available models: {e}")
            return ["Qwen3-0.6B-Q8_0.gguf"]
    
    def get_available_grammars(self) -> list:
        """Get list of available grammar files
        
        Returns:
            List of grammar filenames
        """
        grammar_dir = self.data_dir / "test_grammars"
        
        if not grammar_dir.exists():
            return []
        
        try:
            # List all .gbnf files in the grammar directory
            grammars = [f.name for f in grammar_dir.glob("*.gbnf")]
            return sorted(grammars)
        except Exception as e:
            logger.error(f"Failed to list grammar files: {e}")
            return []