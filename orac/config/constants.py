"""
Centralized constants for ORAC Core.

All magic numbers and hardcoded values should be defined here.
This provides a single source of truth for configuration values.
"""

# Network Configuration
class NetworkConfig:
    """Network-related constants."""
    DEFAULT_HA_HOST = "localhost"
    DEFAULT_HA_PORT = 8123
    DEFAULT_ORAC_PORT = 8000
    DEFAULT_ORAC_HOST = "0.0.0.0"

    # Timeouts (in seconds)
    DEFAULT_TIMEOUT = 30
    HA_TIMEOUT = 10
    SHORT_TIMEOUT = 5

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1


# Model Configuration
class ModelConfig:
    """LLM model-related constants."""
    # Temperature settings
    DEFAULT_TEMPERATURE = 0.7
    GRAMMAR_TEMPERATURE = 0.1
    LOW_TEMPERATURE = 0.1
    HIGH_TEMPERATURE = 0.9

    # Sampling parameters
    DEFAULT_TOP_P = 0.9
    GRAMMAR_TOP_P = 0.9
    LOW_TOP_P = 0.2

    DEFAULT_TOP_K = 40
    GRAMMAR_TOP_K = 10
    LOW_TOP_K = 5

    # Token limits
    DEFAULT_MAX_TOKENS = 512
    GRAMMAR_MAX_TOKENS = 50
    SHORT_MAX_TOKENS = 50
    LONG_MAX_TOKENS = 500

    # Default model
    DEFAULT_MODEL = "Qwen3-0.6B-Q8_0.gguf"


# Cache Configuration
class CacheConfig:
    """Cache-related constants."""
    DEFAULT_TTL = 300  # 5 minutes
    MAX_CACHE_SIZE = 1000
    ENTITY_CACHE_TTL = 300
    SERVICE_CACHE_TTL = 600
    GRAMMAR_CACHE_TTL = 3600  # 1 hour


# Path Configuration
class PathConfig:
    """File and directory path constants."""
    DATA_DIR = "data"
    MODELS_DIR = "models/gguf"
    GRAMMARS_DIR = "data/grammars"
    BACKENDS_DIR = "data/backends"
    STATIC_DIR = "orac/static"
    TEMPLATES_DIR = "orac/templates"

    # Configuration files
    FAVORITES_FILE = "data/favorites.json"
    MODEL_CONFIGS_FILE = "data/model_configs.yaml"
    TOPICS_FILE = "data/topics.yaml"


# API Configuration
class APIConfig:
    """API-related constants."""
    TITLE = "ORAC"
    DESCRIPTION = "Omniscient Reactive Algorithmic Core - Web Interface and API"
    VERSION = "0.2.0"

    # CORS
    CORS_ALLOW_ALL = True  # TODO: Restrict in production


# Logging Configuration
class LogConfig:
    """Logging-related constants."""
    DEFAULT_LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MAX_LOG_SIZE = 10485760  # 10MB
    BACKUP_COUNT = 3
