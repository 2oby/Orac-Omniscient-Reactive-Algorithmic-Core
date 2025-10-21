# ORAC Core Developer Guide

Complete guide for developing and contributing to ORAC Core.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Code Structure](#code-structure)
4. [Development Workflow](#development-workflow)
5. [API Reference](#api-reference)
6. [Testing](#testing)
7. [Adding Features](#adding-features)
8. [Coding Standards](#coding-standards)
9. [Contributing](#contributing)

---

## Architecture Overview

### System Architecture

```
Voice Command → STT → ORAC Core → Backend Service
                        ↓
                   LLM (Grammar)
                        ↓
                   Topic Manager
                        ↓
                  Backend Executor
```

### Core Components

**1. API Layer** (`orac/api_old.py`)
- FastAPI application
- REST endpoint routing
- Request/response handling
- CORS middleware

**2. LLM Client** (`orac/llama_cpp_client.py`)
- llama.cpp wrapper
- Model loading/unloading
- Grammar-constrained generation
- Output parsing

**3. Topic Manager** (`orac/topic_manager.py`)
- Load topics from YAML
- Resolve topics by ID or wake word
- Topic validation

**4. Backend System**
- **Backend Manager** (`orac/backend_manager.py`) - CRUD operations
- **Backend Factory** (`orac/backends/backend_factory.py`) - Instance creation
- **Abstract Backend** (`orac/backends/abstract_backend.py`) - Interface
- **Home Assistant Backend** (`orac/backends/homeassistant_backend.py`) - Implementation

**5. Grammar System** (`orac/grammars/parser.py`)
- Parse GBNF files
- Extract vocabulary
- Validate LLM output

### Data Flow

```
1. Client Request → POST /v1/generate
2. Topic Resolution → TopicManager.get_topic()
3. Grammar Loading → Load GBNF file
4. LLM Generation → LlamaCppClient.generate()
5. Backend Execution → Backend.execute_command()
6. Response → JSON with timing data
```

### Key Design Patterns

**Factory Pattern:**
```python
class BackendFactory:
    @staticmethod
    def create(backend_type: str, config: dict) -> AbstractBackend:
        if backend_type == "homeassistant":
            return HomeAssistantBackend(config)
        raise ValueError(f"Unknown backend type: {backend_type}")
```

**Abstract Interface:**
```python
class AbstractBackend(ABC):
    @abstractmethod
    def execute_command(self, command: dict) -> dict:
        pass
```

---

## Development Setup

### Prerequisites

- Python 3.8+
- Docker & Docker Compose
- Git
- NVIDIA GPU (optional for local testing)

### Local Setup

```bash
# 1. Clone repository
git clone https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git
cd Orac-Omniscient-Reactive-Algorithmic-Core

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Set up environment
cp .env.example .env
nano .env

# 5. Create directories
mkdir -p models/gguf logs data/grammars cache

# 6. Place test model
cp /path/to/tinyllama.gguf models/gguf/
```

### Remote Development (Jetson)

**SSH Config** (`~/.ssh/config`):
```
Host orin4
    HostName 192.168.8.192
    User toby
    IdentityFile ~/.ssh/id_rsa
    ServerAliveInterval 60
```

**Test Connection:**
```bash
ssh orin4 "echo 'Connected'"
```

### Running Locally

```bash
# Development mode with auto-reload
uvicorn orac.api:app --reload --host 0.0.0.0 --port 8000

# Or with Docker
docker compose up

# Test
curl http://localhost:8000/health
```

---

## Code Structure

```
orac/
├── api_old.py                    # Main FastAPI app
├── api_topics.py                 # Topic endpoints
├── api_heartbeat.py              # Health endpoints
├── llama_cpp_client.py           # llama.cpp wrapper
├── topic_manager.py              # Topic management
├── backend_manager.py            # Backend lifecycle
├── backend_grammar_generator.py  # Grammar generation
├── models.py                     # Pydantic models
├── logger.py                     # Logging
│
├── backends/
│   ├── abstract_backend.py       # Interface
│   ├── backend_factory.py        # Factory
│   └── homeassistant_backend.py  # HA implementation
│
├── config/
│   ├── loader.py                 # Config loading
│   └── constants.py              # Constants
│
├── grammars/
│   └── parser.py                 # GBNF parser
│
├── homeassistant/
│   ├── client.py                 # HA API client
│   ├── discovery_service.py      # Entity discovery
│   └── domain_mapper.py          # Domain mapping
│
└── core/
    └── timing.py                 # Performance monitoring

data/
├── model_configs.yaml            # Model configs
├── topics.yaml                   # Topics
├── grammars/                     # GBNF files
└── backends/                     # Backend configs

tests/
├── unit/
├── integration/
└── e2e/
```

---

## Development Workflow

### Typical Development Cycle

```
1. Create feature branch
   └─> git checkout -b feature/new-feature

2. Write code
   └─> Edit files

3. Test locally
   └─> pytest
   └─> Manual testing

4. Deploy to test environment
   └─> ./deploy_and_test.sh "Test feature"

5. Create pull request
   └─> git push origin feature/new-feature
```

### Using deploy_and_test.sh

```bash
# Standard deployment
./deploy_and_test.sh "Fixed backend connection"

# With rebuild
./deploy_and_test.sh --rebuild "Updated dependencies"
```

The script:
1. Commits changes
2. Pushes to GitHub
3. Pulls on remote device
4. Restarts container
5. Runs health checks

---

## API Reference

### Core Endpoints

**Health Check:**
```bash
GET /health
Response: {"status":"healthy","timestamp":"..."}
```

**List Models:**
```bash
GET /v1/models
Response: {"object":"list","data":[...]}
```

**Generate Text:**
```bash
POST /v1/generate
Body: {
  "model": "qwen.gguf",
  "prompt": "turn on lights",
  "topic": "home_assistant",
  "temperature": 0.1
}
Response: {
  "model": "qwen.gguf",
  "output": "{\"action\":\"turn on\",...}",
  "timing": {...}
}
```

### Backend Endpoints

```bash
# Create backend
POST /api/backends
Body: {"name":"HA","type":"homeassistant","connection":{...}}

# List backends
GET /api/backends

# Get backend
GET /api/backends/{id}

# Fetch entities
GET /api/backends/{id}/entities

# Generate grammar
POST /api/backends/{id}/grammar

# Test connection
POST /api/backends/{id}/test
```

### Topic Endpoints

```bash
# Create topic
POST /api/topics
Body: {"name":"home","model":"qwen.gguf",...}

# List topics
GET /api/topics

# Get topic
GET /api/topics/{id}

# Update topic
PUT /api/topics/{id}

# Delete topic
DELETE /api/topics/{id}
```

---

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_backend_manager.py

# With coverage
pytest --cov=orac --cov-report=html

# View coverage
open htmlcov/index.html
```

### Writing Unit Tests

```python
# tests/test_backend_manager.py
import pytest
from orac.backend_manager import BackendManager

def test_create_backend():
    manager = BackendManager()
    backend = manager.create_backend(
        name="Test",
        backend_type="homeassistant",
        connection={"url": "http://test:8123", "token": "test"}
    )
    assert backend is not None
    assert backend['name'] == "Test"

def test_invalid_backend_type():
    manager = BackendManager()
    with pytest.raises(ValueError):
        manager.create_backend("Test", "invalid", {})
```

### Integration Tests

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from orac.api import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_generate_endpoint():
    response = client.post(
        "/v1/generate",
        json={
            "model": "tinyllama.gguf",
            "prompt": "test",
            "max_tokens": 10
        }
    )
    assert response.status_code == 200
    assert "output" in response.json()
```

### Using Fixtures

```python
# conftest.py
import pytest

@pytest.fixture
def backend_manager():
    return BackendManager()

@pytest.fixture
def sample_config():
    return {
        "name": "Test",
        "type": "homeassistant",
        "connection": {"url": "http://test:8123", "token": "test"}
    }

# tests/test_backend.py
def test_with_fixtures(backend_manager, sample_config):
    backend = backend_manager.create_backend(**sample_config)
    assert backend['name'] == "Test"
```

---

## Adding Features

### Adding a New Backend

**1. Create Backend Class:**

`orac/backends/myservice_backend.py`:

```python
from typing import Dict, Any
from .abstract_backend import AbstractBackend
import logging

logger = logging.getLogger(__name__)

class MyServiceBackend(AbstractBackend):
    """MyService integration backend."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config['connection']['url']
        self.api_key = config['connection']['api_key']

    def execute_command(self, command: dict) -> dict:
        """Execute command on MyService."""
        try:
            action = command.get('action')
            device = command.get('device')

            # Call MyService API
            response = self._call_api(action, device)

            return {
                'success': True,
                'result': response
            }
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def fetch_entities(self) -> dict:
        """Fetch entities from MyService."""
        # Implementation
        pass

    def test_connection(self) -> bool:
        """Test connection."""
        # Implementation
        pass

    def generate_grammar(self) -> str:
        """Generate GBNF grammar."""
        # Implementation
        pass

    def _call_api(self, action, device):
        """Internal API helper."""
        # Implementation
        pass
```

**2. Register Backend:**

In `orac/backends/backend_factory.py`:

```python
from .myservice_backend import MyServiceBackend

class BackendFactory:
    @staticmethod
    def create(backend_type: str, config: dict) -> AbstractBackend:
        if backend_type == "homeassistant":
            return HomeAssistantBackend(config)
        elif backend_type == "myservice":
            return MyServiceBackend(config)
        else:
            raise ValueError(f"Unknown backend: {backend_type}")
```

**3. Test:**

```bash
curl -X POST http://localhost:8000/api/backends \
  -d '{"name":"MyService","type":"myservice",...}'
```

### Adding an API Endpoint

In `orac/api_old.py`:

```python
@app.get("/api/custom/endpoint", tags=["Custom"])
async def custom_endpoint(param: str) -> Dict[str, Any]:
    """Custom endpoint."""
    try:
        result = process_custom_logic(param)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Adding a Grammar

Create `data/grammars/my_grammar.gbnf`:

```gbnf
root ::= "{" ws "\"command\"" ws ":" ws command ws "}"
command ::= "\"start\"" | "\"stop\"" | "\"pause\""
ws ::= [ \t\n]*
```

Update `data/grammars.yaml`:

```yaml
grammars:
  my_grammar:
    description: "Custom grammar"
    grammar_file: "my_grammar.gbnf"
```

---

## Coding Standards

### Python Style

Follow PEP 8:

**Type Hints:**
```python
def create_backend(name: str, config: Dict[str, Any]) -> BackendConfig:
    """Create backend."""
    pass
```

**Docstrings (Google Style):**
```python
def complex_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    One-line summary.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Dict containing result

    Raises:
        ValueError: If param1 invalid
    """
    pass
```

**Imports:**
```python
# Standard library
import os
from typing import Dict, Optional

# Third-party
from fastapi import FastAPI

# Local
from orac.models import BackendConfig
```

### Code Formatting

```bash
# Format code
black orac tests

# Sort imports
isort orac tests

# Lint
flake8 orac tests

# Type check
mypy orac
```

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100

[tool.isort]
profile = "black"
line_length = 100
```

### Error Handling

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

---

## Contributing

### Git Workflow

**Branch Strategy:**
- `master` - Production code
- `cleanup` - Current development
- `feature/*` - Feature branches
- `bugfix/*` - Bug fixes

**Commit Messages:**
```
<type>: <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Example:**
```
feat: Add MQTT backend support

- Implement MQTTBackend class
- Add MQTT client handling
- Update factory

Closes #123
```

### Pull Request Process

**Before Submitting:**
- [ ] Tests pass (`pytest`)
- [ ] Linters pass (`flake8`, `black`)
- [ ] Documentation updated
- [ ] No sensitive data in code

**PR Template:**
```markdown
## Description
Brief description

## Changes
- Change 1
- Change 2

## Testing
How tested

## Checklist
- [ ] Tests added
- [ ] Docs updated
- [ ] Linters pass
```

### Development Best Practices

1. **Write tests first** (TDD approach)
2. **Keep functions focused** (single responsibility)
3. **Use type hints** everywhere
4. **Document complex logic**
5. **Handle errors gracefully**
6. **Log appropriately** (not too much, not too little)
7. **Test on real hardware** before PR

---

## Debugging

### Enable Debug Logging

```python
# In .env
LOG_LEVEL=DEBUG

# Restart
docker restart orac

# View logs
docker logs -f orac | grep DEBUG
```

### Using pdb

```python
import pdb; pdb.set_trace()
```

### VS Code Debug Config

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["orac.api:app", "--reload"]
    }
  ]
}
```

### Remote Debugging

```bash
# View logs
ssh orin4 "docker logs -f orac"

# Execute in container
ssh orin4 "docker exec orac python -c 'import orac; print(orac.__version__)'"

# Interactive Python
ssh orin4 "docker exec -it orac python"
```

---

## Performance Considerations

### Optimization Tips

1. **GPU Offloading:** Maximize `gpu_layers`
2. **Quantization:** Use Q4_K_M for speed
3. **Context Size:** Minimize for specific use cases
4. **Grammar Simplification:** Keep grammars minimal
5. **Caching:** Cache backend entities

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

---

## Quick Reference

### Essential Commands

```bash
# Setup
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black orac tests
isort orac tests

# Lint
flake8 orac tests

# Type check
mypy orac

# Run locally
uvicorn orac.api:app --reload

# Deploy
./deploy_and_test.sh "Changes"
```

### Project Structure

```
orac/          # Python package
docs/          # Documentation
data/          # Configuration
tests/         # Test suite
models/gguf/   # GGUF models
logs/          # Log files
cache/         # Cache data
```

---

For user-facing documentation, see [USER_GUIDE.md](USER_GUIDE.md).

*Last Updated: October 2025*
