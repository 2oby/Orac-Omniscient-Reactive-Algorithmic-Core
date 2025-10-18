# Sprint 1: Configuration Consolidation & Constants

## Deployment Target Information

**Target Machine:** NVIDIA Jetson Orin (orin4)
- **Hostname:** orin4
- **SSH Access:** `ssh orin4`
- **ORAC Location:** `/home/toby/ORAC`
- **Docker Container:** `orac`
- **API URL:** http://192.168.8.192:8000
- **Production HA URL:** http://192.168.8.99:8123

**How to Deploy:**
```bash
# Automatic deployment (commits, pushes, pulls on orin, copies to Docker, tests)
./deploy_and_test.sh "Your commit message here"

# The script automatically:
# 1. Commits changes to current branch
# 2. Pushes to GitHub
# 3. SSHs to orin4 and pulls latest from GitHub
# 4. Copies files into Docker container (including Python packages)
# 5. Restarts container
# 6. Runs verification tests
```

**Manual Operations on Orin:**
```bash
# SSH to orin
ssh orin4

# View Docker logs
docker logs orac --tail 50

# Enter Docker shell
docker exec -it orac bash

# Restart container
docker restart orac

# Test imports in container
docker exec orac python3 -c "from orac.config import NetworkConfig; print(NetworkConfig.DEFAULT_TIMEOUT)"
```

**Important Notes:**
- We ALWAYS build and test on orin4 (not locally on Mac)
- The deploy script automatically detects the current git branch
- All Python package directories (with `__init__.py`) are automatically copied
- Backups are created before each deployment in `backups/TIMESTAMP/`

---

## Current Progress (2025-10-18)

**Completed:**
- ✅ Created `cleanup` branch
- ✅ Created `orac/config/` module structure
  - ✅ `constants.py` - All configuration constants
  - ✅ `loader.py` - ConfigLoader class
  - ✅ `legacy.py` - Backward-compatible functions from old config.py
  - ✅ `__init__.py` - Module exports
- ✅ Updated `deploy_and_test.sh` to:
  - Auto-detect current branch
  - Copy Python package directories
- ✅ Deployed and verified on orin4
- ✅ All existing imports work (100% backward compatible)

**Next Session:**
- Replace magic numbers in `orac/api.py`
- Replace magic numbers in `orac/homeassistant/cache.py`
- Replace magic numbers in `orac/backend_manager.py`
- Replace magic numbers in `orac/dispatchers/homeassistant.py`
- Search for remaining magic numbers
- Final deployment and verification

---

## Prompt for Next LLM

You are tasked with completing Sprint 1 of the ORAC Core cleanup and productionization effort. This sprint focuses on **eliminating magic numbers** and **consolidating configuration management** across the codebase.

**Context:**
ORAC Core is a voice-command processing system that integrates with Home Assistant. It was developed rapidly across multiple sprints and now needs cleanup. The codebase has magic numbers scattered throughout (ports, timeouts, temperatures, etc.) and configuration spread across environment variables, YAML files, JSON files, and hardcoded values.

**Your Mission:**
1. ~~Create a centralized configuration system with constants~~ ✅ DONE
2. Replace ALL magic numbers with named constants (IN PROGRESS)
3. ~~Consolidate configuration loading logic~~ ✅ DONE
4. Ensure everything still works by deploying and testing

**Important:**
- You are working on the `cleanup` branch
- Use `./deploy_and_test.sh "message"` to deploy to orin4
- The orin4 machine is the ONLY build/test target (not local Mac)
- The test machine (orin4) is the source of truth - deployment must succeed there
- Commit frequently with meaningful messages via deploy script
- DO NOT break existing functionality

**What's Already Done:**
The config module (`orac/config/`) has been created and deployed successfully. All legacy functions are preserved for backward compatibility. Now we need to replace magic numbers throughout the codebase with references to the new constants.

---

## Sprint 1 Goals

- ✅ Eliminate all magic numbers from the codebase
- ✅ Create centralized configuration module
- ✅ Consolidate configuration loading logic
- ✅ Maintain backward compatibility
- ✅ Pass all deployment tests

**Estimated Time:** 2-3 days

---

## Task Breakdown

### Task 1.1: Create Configuration Module Structure

**Objective:** Set up the foundation for centralized configuration.

**Steps:**

1. Create the configuration module directory:
```bash
mkdir -p orac/config
touch orac/config/__init__.py
touch orac/config/constants.py
touch orac/config/loader.py
```

2. Create `orac/config/constants.py` with the following structure:

```python
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
```

3. Create `orac/config/__init__.py` to expose the constants:

```python
"""
Configuration module for ORAC Core.

Provides centralized access to constants and configuration loading.
"""

from .constants import (
    NetworkConfig,
    ModelConfig,
    CacheConfig,
    PathConfig,
    APIConfig,
    LogConfig
)
from .loader import ConfigLoader

__all__ = [
    'NetworkConfig',
    'ModelConfig',
    'CacheConfig',
    'PathConfig',
    'APIConfig',
    'LogConfig',
    'ConfigLoader'
]
```

**Verification:**
```bash
# Test that the module can be imported
python3 -c "from orac.config import NetworkConfig, ModelConfig; print('Config module created successfully')"
```

---

### Task 1.2: Create Configuration Loader

**Objective:** Centralize configuration loading logic.

**Steps:**

1. Create `orac/config/loader.py`:

```python
"""
Configuration loader for ORAC Core.

Handles loading configuration from multiple sources with precedence:
1. Environment variables (highest priority)
2. Configuration files (YAML, JSON)
3. Default constants (lowest priority)
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .constants import NetworkConfig, ModelConfig, PathConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Unified configuration loader."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the config loader.

        Args:
            data_dir: Base directory for configuration files
        """
        self.data_dir = Path(data_dir) if data_dir else Path(PathConfig.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_ha_url(self) -> str:
        """Get Home Assistant URL.

        Precedence: HA_URL env var > default
        """
        return os.getenv('HA_URL', f'http://{NetworkConfig.DEFAULT_HA_HOST}:{NetworkConfig.DEFAULT_HA_PORT}')

    def get_ha_token(self) -> str:
        """Get Home Assistant API token.

        Precedence: HA_TOKEN env var > empty string
        """
        return os.getenv('HA_TOKEN', '')

    def get_orac_port(self) -> int:
        """Get ORAC API port.

        Precedence: ORAC_PORT env var > default
        """
        return int(os.getenv('ORAC_PORT', str(NetworkConfig.DEFAULT_ORAC_PORT)))

    def get_models_path(self) -> str:
        """Get models directory path.

        Precedence: ORAC_MODELS_PATH env var > default
        """
        return os.getenv('ORAC_MODELS_PATH', PathConfig.MODELS_DIR)

    def get_data_dir(self) -> str:
        """Get data directory path.

        Precedence: DATA_DIR env var > default
        """
        return os.getenv('DATA_DIR', str(self.data_dir))

    def load_json_config(self, filename: str) -> Dict[str, Any]:
        """Load a JSON configuration file.

        Args:
            filename: Name of the JSON file (relative to data_dir)

        Returns:
            Configuration dictionary
        """
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return {}

        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON config {filepath}: {e}")
            return {}

    def load_yaml_config(self, filename: str) -> Dict[str, Any]:
        """Load a YAML configuration file.

        Args:
            filename: Name of the YAML file (relative to data_dir)

        Returns:
            Configuration dictionary
        """
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return {}

        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load YAML config {filepath}: {e}")
            return {}

    def save_json_config(self, filename: str, data: Dict[str, Any]) -> bool:
        """Save a JSON configuration file.

        Args:
            filename: Name of the JSON file (relative to data_dir)
            data: Configuration data to save

        Returns:
            True if successful
        """
        filepath = self.data_dir / filename

        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved config to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON config {filepath}: {e}")
            return False

    def save_yaml_config(self, filename: str, data: Dict[str, Any]) -> bool:
        """Save a YAML configuration file.

        Args:
            filename: Name of the YAML file (relative to data_dir)
            data: Configuration data to save

        Returns:
            True if successful
        """
        filepath = self.data_dir / filename

        try:
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            logger.info(f"Saved config to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save YAML config {filepath}: {e}")
            return False
```

**Verification:**
```bash
python3 -c "from orac.config import ConfigLoader; loader = ConfigLoader(); print(f'HA URL: {loader.get_ha_url()}')"
```

---

### Task 1.3: Replace Magic Numbers in orac/api.py

**Objective:** Replace all hardcoded values in the main API file.

**Files to modify:** `orac/api.py`

**Specific Changes:**

1. Add import at the top:
```python
from orac.config import NetworkConfig, ModelConfig, APIConfig
```

2. **Line 70-74:** Update FastAPI app initialization:
```python
# BEFORE:
app = FastAPI(
    title="ORAC",
    description="Omniscient Reactive Algorithmic Core - Web Interface and API",
    version="0.2.0"
)

# AFTER:
app = FastAPI(
    title=APIConfig.TITLE,
    description=APIConfig.DESCRIPTION,
    version=APIConfig.VERSION
)
```

3. **Line 758:** Update timeout value:
```python
# BEFORE:
timeout=30,  # Set a 30-second timeout for the API endpoint

# AFTER:
timeout=NetworkConfig.DEFAULT_TIMEOUT,
```

4. **Line 1184-1187:** Update model settings:
```python
# BEFORE:
temperature=0.1,  # Use 0.1 for grammar-constrained generation
top_p=0.9,
top_k=10,

# AFTER:
temperature=ModelConfig.GRAMMAR_TEMPERATURE,
top_p=ModelConfig.GRAMMAR_TOP_P,
top_k=ModelConfig.GRAMMAR_TOP_K,
```

5. **Line 1197-1200:** Update fallback model settings:
```python
# BEFORE:
temperature=0.1,
top_p=0.9,
top_k=10,

# AFTER:
temperature=ModelConfig.GRAMMAR_TEMPERATURE,
top_p=ModelConfig.GRAMMAR_TOP_P,
top_k=ModelConfig.GRAMMAR_TOP_K,
```

6. **Line 1207-1210:** Update default JSON settings:
```python
# BEFORE:
temperature=0.7,
top_p=0.7,
top_k=40,

# AFTER:
temperature=ModelConfig.DEFAULT_TEMPERATURE,
top_p=ModelConfig.DEFAULT_TOP_P,
top_k=ModelConfig.DEFAULT_TOP_K,
```

**Verification:**
```bash
# Check that api.py imports the config module
grep -n "from orac.config import" orac/api.py

# Check that magic numbers are replaced
grep -n "timeout=30" orac/api.py  # Should return nothing
grep -n "temperature=0.1" orac/api.py  # Should return nothing
```

---

### Task 1.4: Replace Magic Numbers in orac/config.py

**Objective:** Update the existing config module to use new constants.

**Files to modify:** `orac/config.py`

**Specific Changes:**

1. Add import at the top:
```python
from orac.config.constants import ModelConfig
```

2. **Line 30-35:** Update DEFAULT_FAVORITES:
```python
# BEFORE:
"default_settings": {
    "temperature": 0.7,
    "top_p": 0.7,
    "top_k": 40,
    "max_tokens": 512
}

# AFTER:
"default_settings": {
    "temperature": ModelConfig.DEFAULT_TEMPERATURE,
    "top_p": ModelConfig.DEFAULT_TOP_P,
    "top_k": ModelConfig.DEFAULT_TOP_K,
    "max_tokens": ModelConfig.DEFAULT_MAX_TOKENS
}
```

3. **Similar updates for model configs** - Search for all temperature, top_p, top_k, max_tokens values and replace with constants.

**Verification:**
```bash
grep -n "temperature.*0\.[0-9]" orac/config.py  # Should return nothing
```

---

### Task 1.5: Replace Magic Numbers in orac/homeassistant/cache.py

**Objective:** Replace cache configuration magic numbers.

**Files to modify:** `orac/homeassistant/cache.py`

**Specific Changes:**

1. Add import at the top:
```python
from orac.config import CacheConfig
```

2. **Line 62:** Update __init__ default parameters:
```python
# BEFORE:
def __init__(self, ttl: int = 300, max_size: int = 1000, cache_dir: Optional[Path] = None):

# AFTER:
def __init__(self, ttl: int = CacheConfig.DEFAULT_TTL, max_size: int = CacheConfig.MAX_CACHE_SIZE, cache_dir: Optional[Path] = None):
```

**Verification:**
```bash
grep -n "ttl.*300" orac/homeassistant/cache.py  # Should return nothing
grep -n "max_size.*1000" orac/homeassistant/cache.py  # Should return nothing
```

---

### Task 1.6: Replace Magic Numbers in orac/backend_manager.py

**Objective:** Replace hardcoded port and connection values.

**Files to modify:** `orac/backend_manager.py`

**Specific Changes:**

1. Add import at the top:
```python
from orac.config import NetworkConfig
```

2. **Line 103, 349, 369-373:** Update port references:
```python
# Search for all instances of port 8123 and replace with NetworkConfig.DEFAULT_HA_PORT
# Search for timeout values (10) and replace with NetworkConfig.HA_TIMEOUT
```

3. **Line 349-350:** Update default URL construction:
```python
# BEFORE:
url = connection.get('url', '')
port = connection.get('port', 8123)

# AFTER:
url = connection.get('url', '')
port = connection.get('port', NetworkConfig.DEFAULT_HA_PORT)
```

4. **Line 373:** Update timeout:
```python
# BEFORE:
timeout=connection.get('timeout', 10)

# AFTER:
timeout=connection.get('timeout', NetworkConfig.HA_TIMEOUT)
```

**Apply similar changes throughout the file.**

**Verification:**
```bash
grep -n "8123" orac/backend_manager.py  # Should only appear in comments
grep -n "timeout.*10" orac/backend_manager.py  # Should return nothing
```

---

### Task 1.7: Replace Magic Numbers in orac/dispatchers/homeassistant.py

**Objective:** Replace hardcoded HA URL.

**Files to modify:** `orac/dispatchers/homeassistant.py`

**Specific Changes:**

1. Add import at the top:
```python
from orac.config import NetworkConfig
```

2. **Line 44:** Update default HA URL:
```python
# BEFORE:
self.ha_url = os.getenv('HA_URL', 'http://192.168.8.99:8123')

# AFTER:
self.ha_url = os.getenv('HA_URL', f'http://{NetworkConfig.DEFAULT_HA_HOST}:{NetworkConfig.DEFAULT_HA_PORT}')
```

**Note:** The IP 192.168.8.99 is specific to your setup. You may want to keep this as an environment variable default or add it to constants as PRODUCTION_HA_HOST.

**Verification:**
```bash
grep -n "192.168.8.99" orac/dispatchers/homeassistant.py  # Should return nothing (unless documented)
```

---

### Task 1.8: Update orac/config.py to Use ConfigLoader

**Objective:** Refactor existing config.py to use the new ConfigLoader.

**Files to modify:** `orac/config.py`

**Specific Changes:**

1. Add import:
```python
from orac.config.loader import ConfigLoader
```

2. Create module-level ConfigLoader instance:
```python
# At module level, after imports
_config_loader = ConfigLoader()
```

3. **Refactor load_favorites()** to use ConfigLoader:
```python
def load_favorites() -> Dict[str, Any]:
    """Load favorites configuration, creating default if missing."""
    config = _config_loader.load_json_config('favorites.json')

    if not config:
        logger.info("Creating default favorites.json")
        config = DEFAULT_FAVORITES
        _config_loader.save_json_config('favorites.json', config)

    # Handle legacy format conversion...
    return config
```

4. **Similar refactoring for:**
- `load_model_configs()` - use `_config_loader.load_yaml_config('model_configs.yaml')`
- `save_favorites()` - use `_config_loader.save_json_config()`
- `save_model_configs()` - use `_config_loader.save_yaml_config()`

**Verification:**
```bash
# Test that config loading still works
python3 -c "from orac.config import load_favorites, load_model_configs; print('Config loading works')"
```

---

### Task 1.9: Search and Replace Remaining Magic Numbers

**Objective:** Find and replace any remaining magic numbers in the codebase.

**Steps:**

1. Search for common magic number patterns:
```bash
# Find temperature values
grep -rn "temperature.*0\.[0-9]" orac/ --include="*.py" | grep -v "config/constants.py"

# Find timeout values
grep -rn "timeout.*[0-9]" orac/ --include="*.py" | grep -v "config/constants.py"

# Find port numbers
grep -rn "port.*8[0-9][0-9][0-9]" orac/ --include="*.py" | grep -v "config/constants.py"

# Find top_p values
grep -rn "top_p.*0\.[0-9]" orac/ --include="*.py" | grep -v "config/constants.py"

# Find top_k values
grep -rn "top_k.*[0-9]" orac/ --include="*.py" | grep -v "config/constants.py"

# Find max_tokens values
grep -rn "max_tokens.*[0-9]" orac/ --include="*.py" | grep -v "config/constants.py"
```

2. For each occurrence found:
   - Determine if it's a magic number or a legitimate variable value
   - If magic number, add to constants.py if not already there
   - Replace with constant reference

3. Common files that likely need updates:
   - `orac/llama_cpp_client.py` - model parameters
   - `orac/homeassistant/client.py` - timeouts
   - `orac/homeassistant/config.py` - defaults
   - `orac/topic_manager.py` - model defaults
   - Any test files with hardcoded values

**Verification:**
```bash
# Create a verification script
cat > verify_no_magic_numbers.sh << 'EOF'
#!/bin/bash
echo "Checking for remaining magic numbers..."

# Exclude the constants file itself and test files
FILES=$(find orac -name "*.py" ! -path "*/config/constants.py" ! -path "*/tests/*")

FOUND=0

for pattern in "temperature=0\.[0-9]" "top_p=0\.[0-9]" "top_k=[0-9]" "timeout=[0-9]" "port=8[0-9][0-9][0-9]"; do
    echo "Checking pattern: $pattern"
    MATCHES=$(grep -rn "$pattern" $FILES 2>/dev/null || true)
    if [ ! -z "$MATCHES" ]; then
        echo "$MATCHES"
        FOUND=1
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "✅ No magic numbers found!"
else
    echo "❌ Magic numbers still present - please review above"
fi
EOF

chmod +x verify_no_magic_numbers.sh
./verify_no_magic_numbers.sh
```

---

### Task 1.10: Update Tests

**Objective:** Ensure tests use constants and still pass.

**Steps:**

1. Create a basic test for the config module:

```python
# tests/test_config_constants.py
"""Tests for configuration constants and loader."""

import pytest
from orac.config import (
    NetworkConfig,
    ModelConfig,
    CacheConfig,
    PathConfig,
    APIConfig,
    ConfigLoader
)


def test_network_config_has_required_constants():
    """Test that NetworkConfig has all required constants."""
    assert hasattr(NetworkConfig, 'DEFAULT_HA_PORT')
    assert hasattr(NetworkConfig, 'DEFAULT_ORAC_PORT')
    assert hasattr(NetworkConfig, 'DEFAULT_TIMEOUT')
    assert hasattr(NetworkConfig, 'HA_TIMEOUT')

    # Verify types
    assert isinstance(NetworkConfig.DEFAULT_HA_PORT, int)
    assert isinstance(NetworkConfig.DEFAULT_ORAC_PORT, int)
    assert isinstance(NetworkConfig.DEFAULT_TIMEOUT, int)


def test_model_config_has_required_constants():
    """Test that ModelConfig has all required constants."""
    assert hasattr(ModelConfig, 'DEFAULT_TEMPERATURE')
    assert hasattr(ModelConfig, 'GRAMMAR_TEMPERATURE')
    assert hasattr(ModelConfig, 'DEFAULT_TOP_P')
    assert hasattr(ModelConfig, 'DEFAULT_TOP_K')
    assert hasattr(ModelConfig, 'DEFAULT_MAX_TOKENS')

    # Verify reasonable ranges
    assert 0.0 <= ModelConfig.DEFAULT_TEMPERATURE <= 1.0
    assert 0.0 <= ModelConfig.GRAMMAR_TEMPERATURE <= 1.0
    assert 0.0 <= ModelConfig.DEFAULT_TOP_P <= 1.0


def test_cache_config_has_required_constants():
    """Test that CacheConfig has all required constants."""
    assert hasattr(CacheConfig, 'DEFAULT_TTL')
    assert hasattr(CacheConfig, 'MAX_CACHE_SIZE')

    assert isinstance(CacheConfig.DEFAULT_TTL, int)
    assert isinstance(CacheConfig.MAX_CACHE_SIZE, int)


def test_config_loader_initialization():
    """Test that ConfigLoader can be initialized."""
    loader = ConfigLoader()
    assert loader is not None

    # Test with custom data dir
    loader2 = ConfigLoader(data_dir="/tmp/test_orac")
    assert loader2 is not None


def test_config_loader_ha_url():
    """Test HA URL configuration."""
    loader = ConfigLoader()
    url = loader.get_ha_url()
    assert url is not None
    assert isinstance(url, str)
    assert url.startswith('http')


def test_config_loader_orac_port():
    """Test ORAC port configuration."""
    loader = ConfigLoader()
    port = loader.get_orac_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535
```

2. Run the new test:
```bash
pytest tests/test_config_constants.py -v
```

3. Update any existing tests that use magic numbers:
```bash
# Search for tests with hardcoded values
grep -rn "temperature.*0\." tests/ --include="*.py"
grep -rn "8123\|8000" tests/ --include="*.py"
```

4. Update found tests to import and use constants:
```python
# Example update
# BEFORE:
assert response.temperature == 0.1

# AFTER:
from orac.config import ModelConfig
assert response.temperature == ModelConfig.GRAMMAR_TEMPERATURE
```

**Verification:**
```bash
# Run all tests
pytest tests/ -v

# Check test coverage for config module
pytest tests/test_config_constants.py --cov=orac.config --cov-report=term-missing
```

---

## Final Testing & Verification

### Pre-Deployment Checklist

Before running the deployment script, verify:

- [ ] All imports work correctly
- [ ] No syntax errors in modified files
- [ ] Config module can be imported
- [ ] Tests pass locally
- [ ] No magic numbers remain (run verification script)

```bash
# Run syntax check
python3 -m py_compile orac/config/*.py
python3 -m py_compile orac/api.py
python3 -m py_compile orac/backend_manager.py

# Run local tests
pytest tests/ -v

# Verify config module
python3 << EOF
from orac.config import NetworkConfig, ModelConfig, CacheConfig
print(f"Network timeout: {NetworkConfig.DEFAULT_TIMEOUT}")
print(f"Model temperature: {ModelConfig.DEFAULT_TEMPERATURE}")
print(f"Cache TTL: {CacheConfig.DEFAULT_TTL}")
print("✅ Config module working!")
EOF
```

### Deployment & Testing

1. **Commit your changes:**
```bash
git add orac/config/
git add orac/api.py
git add orac/backend_manager.py
git add orac/homeassistant/cache.py
git add orac/dispatchers/homeassistant.py
git add tests/test_config_constants.py
git commit -m "Sprint 1: Add centralized configuration and eliminate magic numbers

- Created orac/config module with constants and loader
- Replaced magic numbers in api.py with named constants
- Updated backend_manager.py to use configuration constants
- Refactored cache.py to use CacheConfig
- Updated dispatcher to use NetworkConfig
- Added tests for configuration module
- All magic numbers now defined in orac/config/constants.py"
```

2. **Deploy and test:**
```bash
./deploy_and_test.sh "Sprint 1: Configuration consolidation"
```

3. **Verify on Orin:**
```bash
ssh orin4 << 'EOF'
cd /home/toby/ORAC

# Check that API starts successfully
docker logs orac --tail 20

# Test that config is loaded
docker exec orac python3 -c "from orac.config import NetworkConfig; print(f'Config OK: {NetworkConfig.DEFAULT_TIMEOUT}')"
EOF
```

### Rollback Plan

If deployment fails:

```bash
# Check what changed
git diff HEAD~1

# Rollback if needed
git revert HEAD
./deploy_and_test.sh "Rollback Sprint 1"

# Or restore specific file
git checkout HEAD~1 -- orac/api.py
./deploy_and_test.sh "Partial rollback Sprint 1"
```

---

## Success Criteria

Sprint 1 is complete when:

- ✅ `orac/config/` module exists with constants.py and loader.py
- ✅ All magic numbers replaced with named constants
- ✅ Configuration loader centralizes config file access
- ✅ All tests pass (locally and on deployment)
- ✅ `./deploy_and_test.sh` completes successfully
- ✅ API starts and responds on Orin
- ✅ No hardcoded timeouts, ports, or model parameters in code (except in constants.py)
- ✅ Changes committed with clear commit message

---

## Common Issues & Solutions

### Issue: Import errors after creating config module

**Solution:** Make sure `orac/config/__init__.py` properly exports all classes:
```python
from .constants import NetworkConfig, ModelConfig, CacheConfig, PathConfig, APIConfig, LogConfig
from .loader import ConfigLoader

__all__ = ['NetworkConfig', 'ModelConfig', 'CacheConfig', 'PathConfig', 'APIConfig', 'LogConfig', 'ConfigLoader']
```

### Issue: Circular import between orac.config and orac/config/

**Solution:** The new config module is `orac/config/` (directory). The old `orac/config.py` should be updated to import from `orac.config.constants`. They should not import each other - constants should be pure data with no imports from orac modules.

### Issue: Tests fail after changes

**Solution:**
1. Check that test imports are updated
2. Verify constants match the old hardcoded values
3. Run tests with verbose output: `pytest -vv -s`

### Issue: Deployment test fails

**Solution:**
1. Check docker logs: `ssh orin4 'docker logs orac --tail 50'`
2. Verify files were copied: `ssh orin4 'docker exec orac ls -la /app/orac/config/'`
3. Test imports in container: `ssh orin4 'docker exec orac python3 -c "from orac.config import NetworkConfig"'`

---

## Next Steps

After Sprint 1 is successfully completed:

1. Update sprint status in `cleanup.MD`
2. Commit final state
3. Move to Sprint 2: API Decomposition

---

## Notes

- Keep the old `orac/config.py` for now - it will be refactored to use the new config system
- Don't worry about perfect constant names yet - we can refine in later sprints
- Focus on correctness over elegance - functionality must not break
- The IP address 192.168.8.99 is specific to your setup and should probably stay as an environment variable default
