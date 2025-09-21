# ORAC Core: Backend-First Architecture Implementation Plan

## Codebase Analysis & Integration Strategy

### Current ORAC Core Architecture

Based on the developer guide analysis, ORAC Core has a well-structured architecture that we'll extend with backend management:

```
/orac/
├── api.py                     # Main API endpoints (+ backend endpoints)
├── topic_manager.py           # Topic management
├── backend_manager.py         # NEW: Backend management
├── grammars/
│   └── parser.py             # GBNF grammar parsing
├── dispatchers/
│   ├── base.py               # Base dispatcher interface
│   ├── homeassistant.py      # HA integration
│   ├── registry.py           # Dispatcher registration
│   ├── mapping_generator.py  # Auto-generate mappings
│   ├── mapping_resolver.py   # Resolve entities
│   └── mappings/             # Generated mapping files
├── backends/                  # NEW: Backend implementations
│   ├── base.py               # Base backend interface
│   ├── homeassistant.py      # HA backend implementation
│   └── registry.py           # Backend type registration
└── core/
    └── timing.py             # Performance monitoring

/data/
├── topics/                   # Topic configurations
├── backends/                 # NEW: Backend configurations
└── grammars/                 # GBNF grammar files
```

### Integration Points for Backend-First Architecture

**Primary Integration: Backend Management System**

The new architecture introduces backends as first-class citizens alongside topics:

1. **Backend Management** - Create, configure, and manage external service connections
2. **Entity Import Wizard** - Import and configure entities from backends
3. **Topic-Backend Association** - Topics select from existing backends or create new ones
4. **Grammar Generation** - Generate grammars based on backend entity configurations

**Secondary Integration: Enhanced Topic Workflow**

1. **Topic Creation Wizard** - Select backend, then generate grammar
2. **Topic Editing Interface** - Update backend association or regenerate grammar
3. **Grammar Validation** - Test generated grammars with backend connections
4. **Backend Validation** - Test backend connectivity and entity access

## Backend-First Implementation Strategy

### Phase 1: Backend Management & Entity Import (Current Focus)

This initial phase focuses on creating the foundation for backend management and entity import, without grammar generation or dispatching (which will be implemented in future sprints).

#### 1.1 Backend Management System

**Backend Storage Structure** `/data/backends/`
```
/data/backends/
├── ha_main.json              # Primary HA backend
├── ha_remote.json            # Secondary HA backend (same server, different entities)
├── spotify_main.json         # Future: Spotify backend
└── ...
```

**Backend Configuration Format**
```json
{
  "id": "ha_main",
  "name": "Home Assistant Main",
  "type": "homeassistant",
  "config": {
    "url": "http://192.168.8.99:8123",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "validate_ssl": false
  },
  "entities": {
    "scene.lounge_evening": {
      "enabled": true,
      "friendly_name": "Lounge Evening",
      "original_name": "Lounge Evening Scene"
    },
    "group.bedroom_lights": {
      "enabled": true,
      "friendly_name": "Bedroom Lights",
      "original_name": "Bedroom Light Group"
    },
    "light.kitchen_ceiling": {
      "enabled": false,
      "friendly_name": "Kitchen Ceiling",
      "original_name": "Kitchen Ceiling Light"
    }
  },
  "last_sync": "2024-09-21T10:30:00Z",
  "connection_status": "connected"
}
```

#### 1.2 Backend Types & Registry

**Pluggable Backend Architecture**
```python
# /orac/backends/base.py
class BaseBackend:
    """Base backend interface for all external services"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def test_connection(self) -> ConnectionResult:
        """Test if backend is accessible"""
        raise NotImplementedError

    async def discover_entities(self) -> List[Entity]:
        """Discover all available entities from backend"""
        raise NotImplementedError

    async def get_entity_details(self, entity_id: str) -> EntityDetails:
        """Get detailed information about specific entity"""
        raise NotImplementedError

    def get_backend_type(self) -> str:
        """Return backend type identifier"""
        raise NotImplementedError

# /orac/backends/homeassistant.py
class HomeAssistantBackend(BaseBackend):
    """Home Assistant backend implementation"""

    def get_backend_type(self) -> str:
        return "homeassistant"

    async def test_connection(self) -> ConnectionResult:
        """Test HA API connectivity"""
        # Implementation for HA connection testing

    async def discover_entities(self) -> List[Entity]:
        """Discover entities using HA API"""
        # Implementation for HA entity discovery

# /orac/backends/registry.py
class BackendRegistry:
    """Registry for available backend types"""

    _backends = {
        "homeassistant": HomeAssistantBackend,
        # Future: "spotify": SpotifyBackend,
    }

    @classmethod
    def get_backend_class(cls, backend_type: str) -> Type[BaseBackend]:
        return cls._backends.get(backend_type)

    @classmethod
    def get_available_types(cls) -> List[str]:
        return list(cls._backends.keys())
```

#### 1.3 Backend Manager Service

```python
# /orac/backend_manager.py
class BackendManager:
    """Manages backend configurations and operations"""

    def __init__(self, data_dir: str = "/data/backends"):
        self.data_dir = data_dir
        self.backends_cache = {}

    async def create_backend(self, backend_id: str, backend_type: str, config: Dict) -> Backend:
        """Create new backend configuration"""
        backend_class = BackendRegistry.get_backend_class(backend_type)
        backend = backend_class(config)

        # Test connection
        connection_result = await backend.test_connection()
        if not connection_result.success:
            raise BackendConnectionError(f"Cannot connect to {backend_type}: {connection_result.error}")

        # Save configuration
        backend_config = {
            "id": backend_id,
            "name": config.get("name", backend_id),
            "type": backend_type,
            "config": config,
            "entities": {},  # Initially empty, populated by entity import wizard
            "last_sync": datetime.utcnow().isoformat(),
            "connection_status": "connected"
        }

        await self._save_backend_config(backend_id, backend_config)
        return backend

    async def get_backend(self, backend_id: str) -> Optional[Backend]:
        """Load backend by ID"""
        config = await self._load_backend_config(backend_id)
        if not config:
            return None

        backend_class = BackendRegistry.get_backend_class(config["type"])
        return backend_class(config["config"])

    async def list_backends(self) -> List[BackendSummary]:
        """List all configured backends"""
        backend_files = glob.glob(f"{self.data_dir}/*.json")
        summaries = []

        for file_path in backend_files:
            config = await self._load_backend_config_from_file(file_path)
            summaries.append(BackendSummary(
                id=config["id"],
                name=config["name"],
                type=config["type"],
                connection_status=config["connection_status"],
                entity_count=len([e for e in config["entities"].values() if e["enabled"]]),
                last_sync=config["last_sync"]
            ))

        return summaries

    async def import_entities(self, backend_id: str) -> EntityImportResult:
        """Run entity import wizard for backend"""
        backend = await self.get_backend(backend_id)
        entities = await backend.discover_entities()

        return EntityImportResult(
            backend_id=backend_id,
            discovered_entities=entities,
            total_count=len(entities)
        )

    async def update_entity_config(self, backend_id: str, entity_id: str,
                                 enabled: bool, friendly_name: str) -> bool:
        """Update entity configuration in backend"""
        config = await self._load_backend_config(backend_id)

        if entity_id not in config["entities"]:
            # Add new entity configuration
            config["entities"][entity_id] = {
                "enabled": enabled,
                "friendly_name": friendly_name,
                "original_name": entity_id  # Will be updated with actual name
            }
        else:
            # Update existing entity configuration
            config["entities"][entity_id]["enabled"] = enabled
            config["entities"][entity_id]["friendly_name"] = friendly_name

        await self._save_backend_config(backend_id, config)
        return True
```

#### 1.4 Entity Import Wizard Flow

**User Experience Flow:**
1. **Backend Creation/Selection** - User creates new backend or selects existing one
2. **Entity Discovery** - System connects to backend and discovers all entities
3. **Entity Configuration** - User sees tile-based interface to enable/disable and configure entities
4. **Save Configuration** - Selected entities and friendly names saved to backend config

**Entity Import UI Components:**
```
Backend: Home Assistant Main                     [Test Connection] [Refresh Entities]
═══════════════════════════════════════════════════════════════════════════════════

Entity Import Wizard                            [124 entities discovered] [Save Config]

Filter: [All] [Scenes] [Groups] [Lights] [Climate] [Switches]    🔍 Search: _______

┌─ SCENES ─────────────────────────────────────────────────────────────────────┐
│ ✅ scene.lounge_evening        │ ⚙️  │ Lounge Evening                          │
│    scene.lounge_evening                       Controls 6 entities             │
│                                                                               │
│ ❌ scene.movie_time            │ ⚙️  │ Movie Time                              │
│    scene.movie_time                           Controls 12 entities            │
│                                                                               │
│ ✅ scene.bedtime_routine       │ ⚙️  │ Bedtime Routine                         │
│    scene.bedtime_routine                      Controls 8 entities             │
└───────────────────────────────────────────────────────────────────────────────┘

┌─ GROUPS ─────────────────────────────────────────────────────────────────────┐
│ ✅ group.bedroom_lights        │ ⚙️  │ Bedroom Lights                          │
│    group.bedroom_lights                       Contains 3 lights              │
│                                                                               │
│ ❌ group.kitchen_appliances    │ ⚙️  │ Kitchen Appliances                      │
│    group.kitchen_appliances                   Contains 4 switches            │
└───────────────────────────────────────────────────────────────────────────────┘

┌─ RAW ENTITIES ───────────────────────────────────────────────────────────────┐
│ ❌ light.bedroom_ceiling       │ ⚙️  │ Bedroom Ceiling                         │
│    light.bedroom_ceiling                      Single light entity            │
│                                                                               │
│ ❌ switch.kitchen_kettle       │ ⚙️  │ Kitchen Kettle                          │
│    switch.kitchen_kettle                      Single switch entity           │
└───────────────────────────────────────────────────────────────────────────────┘

Selected: 14/124 entities                       [Select Recommended] [Select All] [Clear All]
```

**Entity Configuration Modal (⚙️ button):**
```
┌─ Configure Entity ───────────────────────────────────────────────────────────┐
│                                                                              │
│ Entity ID: scene.lounge_evening                                              │
│ Original Name: Lounge Evening Scene                                          │
│                                                                              │
│ Friendly Name: [Lounge Evening                    ]                         │
│                                                                              │
│ ☑️ Enable for voice control                                                 │
│                                                                              │
│ Entity Details:                                                              │
│ • Type: Scene                                                                │
│ • Domain: scene                                                              │
│ • Controls: 6 entities (3 lights, 1 cover, 1 climate, 1 media_player)      │
│ • Last Changed: 2 hours ago                                                  │
│                                                                              │
│                                    [Cancel] [Save]                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### 1.5 API Endpoints for Backend Management

```python
# /orac/api.py (additions)

@app.route('/backends', methods=['GET'])
async def list_backends():
    """List all configured backends"""
    backend_manager = BackendManager()
    backends = await backend_manager.list_backends()
    return jsonify([backend.to_dict() for backend in backends])

@app.route('/backends', methods=['POST'])
async def create_backend():
    """Create new backend"""
    data = request.get_json()
    backend_manager = BackendManager()

    try:
        backend = await backend_manager.create_backend(
            backend_id=data['id'],
            backend_type=data['type'],
            config=data['config']
        )
        return jsonify({"success": True, "backend_id": data['id']})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/backends/<backend_id>/entities/import', methods=['POST'])
async def import_backend_entities(backend_id: str):
    """Import entities from backend"""
    backend_manager = BackendManager()

    try:
        result = await backend_manager.import_entities(backend_id)
        return jsonify(result.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/backends/<backend_id>/entities/<entity_id>', methods=['PUT'])
async def update_entity_config(backend_id: str, entity_id: str):
    """Update entity configuration"""
    data = request.get_json()
    backend_manager = BackendManager()

    try:
        success = await backend_manager.update_entity_config(
            backend_id=backend_id,
            entity_id=entity_id,
            enabled=data['enabled'],
            friendly_name=data['friendly_name']
        )
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/backends/<backend_id>/test', methods=['POST'])
async def test_backend_connection(backend_id: str):
    """Test backend connection"""
    backend_manager = BackendManager()

    try:
        backend = await backend_manager.get_backend(backend_id)
        result = await backend.test_connection()
        return jsonify(result.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/backend-types', methods=['GET'])
async def get_available_backend_types():
    """Get list of available backend types"""
    from .backends.registry import BackendRegistry
    types = BackendRegistry.get_available_types()
    return jsonify({"backend_types": types})
```

### Future Phases (Not in Current Sprint)

#### Phase 2: Grammar Generation Integration
- Modify grammar wizard to work with backend entity configurations
- Generate grammars based on selected entities from backends
- Associate topics with backends

#### Phase 3: Dispatcher Integration
- Update dispatchers to work with backend entity mappings
- Route commands through appropriate backend connections
- Handle value conversions and service calls

#### Phase 4: Advanced Backend Features
- Multiple backend support per topic
- Backend synchronization and updates
- Advanced entity filtering and organization

## Terminal UI Design Philosophy

### Cyberpunk Nuclear Submarine Aesthetic

**Design Principles:**
- **Monospace Green Text** - Classic terminal phosphor green (#00FF41) on black
- **ASCII Art Borders** - Box drawing characters and retro separators
- **Matrix-Style Scrolling** - Text reveals progressively with typing effects
- **Command Prompt Feel** - User inputs look like terminal commands
- **Scanning Animation** - "Scanning HA entities..." with progress bars
- **System Status Displays** - Connection status, entity counts, error states

**Color Palette:**
```
Background:     #000000 (Pure Black)
Primary Text:   #00FF41 (Matrix Green)
Secondary:      #00AA2E (Dim Green)
Accent:         #00FFFF (Cyan)
Warning:        #FFFF00 (Yellow)
Error:          #FF0000 (Red)
Success:        #00FF00 (Bright Green)
```

### Terminal UI Components

**1. ASCII Art Headers**
```
    ╔══════════════════════════════════════════════════════════════╗
    ║  O R A C   C O R E   -   G R A M M A R   G E N E R A T O R  ║
    ║                    [ TOPIC CONFIGURATION ]                   ║
    ╚══════════════════════════════════════════════════════════════╝
```

**2. Progress Indicators**
```
    [████████████████████████████████████████] 100% COMPLETE

    Scanning Home Assistant...
    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ 65%
```

**3. Entity Selection Matrix**
```
    ┌─ ENTITY MATRIX ─────────────────────────────────────────────┐
    │ [✓] scene.lounge_evening      │ TYPE: SCENE    │ ENT: 6    │
    │ [✓] group.bedroom_lights      │ TYPE: GROUP    │ ENT: 3    │
    │ [ ] light.kitchen_ceiling     │ TYPE: LIGHT    │ ENT: 1    │
    │ [ ] automation.morning_wake   │ TYPE: AUTO     │ ENT: --   │
    └─────────────────────────────────────────────────────────────┘
```

**4. Grammar Preview Terminal**
```
    ┌─ GENERATED GRAMMAR ─────────────────────────────────────────┐
    │ > root ::= "{" location "," device "," action "," value "}" │
    │ > location ::= "lounge" | "bedroom" | "kitchen"             │
    │ > device ::= "lights" | "climate" | "entertainment"         │
    │ > action ::= "on" | "off" | "set"                           │
    │ > value ::= [1-9][0-9]? | "null"                            │
    └─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Core Terminal Framework

#### 1.1 Terminal UI Library
**File**: `/orac/terminal_gui/__init__.py`

```python
class TerminalGUI:
    """Cyberpunk terminal interface framework"""

    def __init__(self):
        self.colors = {
            'green': '\033[92m',
            'cyan': '\033[96m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'reset': '\033[0m'
        }

    def print_header(self, title: str):
        """ASCII art header with title"""

    def print_box(self, content: List[str], title: str = ""):
        """Draw bordered box with content"""

    def progress_bar(self, percentage: int, label: str = ""):
        """Animated progress bar"""

    def matrix_type(self, text: str, delay: float = 0.03):
        """Matrix-style typing animation"""

    def entity_matrix(self, entities: List[Entity], selected: Set[str]):
        """Entity selection grid with checkboxes"""
```

#### 1.2 Grammar Wizard Framework
**File**: `/orac/terminal_gui/grammar_wizard.py`

```python
class GrammarWizard:
    """Step-by-step grammar generation wizard"""

    def __init__(self, topic_id: str, ha_client: HomeAssistantClient):
        self.topic_id = topic_id
        self.ha_client = ha_client
        self.terminal = TerminalGUI()
        self.state = WizardState()

    async def run_wizard(self) -> GrammarConfig:
        """Main wizard flow"""
        self.terminal.print_header("GRAMMAR GENERATOR")

        # Step 1: HA Connection & Scanning
        await self.step_ha_scan()

        # Step 2: Entity Discovery & Classification
        await self.step_entity_discovery()

        # Step 3: Entity Selection
        await self.step_entity_selection()

        # Step 4: Grammar Component Building
        await self.step_grammar_building()

        # Step 5: Smart Mapping
        await self.step_smart_mapping()

        # Step 6: Testing & Validation
        await self.step_testing()

        # Step 7: Save & Deploy
        await self.step_save()

        return self.state.grammar_config
```

### Phase 2: Home Assistant Integration

#### 2.1 Enhanced Entity Discovery
**File**: `/orac/terminal_gui/ha_discovery.py`

```python
class HADiscoveryService:
    """Terminal-based HA entity discovery with setup validation"""

    async def scan_entities_with_progress(self) -> EntityScanResult:
        """Scan HA entities with terminal progress display"""
        terminal = TerminalGUI()

        terminal.matrix_type(">>> CONNECTING TO HOME ASSISTANT...")
        await asyncio.sleep(0.5)

        if not await self.test_connection():
            terminal.print_error("CONNECTION FAILED - CHECK HA_URL AND TOKEN")
            return None

        terminal.matrix_type(">>> CONNECTION ESTABLISHED")
        terminal.matrix_type(">>> SCANNING ENTITY REGISTRY...")

        entities = []
        total_domains = len(self.SCAN_DOMAINS)

        for i, domain in enumerate(self.SCAN_DOMAINS):
            progress = int((i / total_domains) * 100)
            terminal.progress_bar(progress, f"Scanning {domain}...")

            domain_entities = await self.scan_domain(domain)
            entities.extend(domain_entities)
            await asyncio.sleep(0.1)  # Visual delay

        terminal.progress_bar(100, "Scan complete")
        return self.classify_entities(entities)

    def display_scan_results(self, results: EntityScanResult):
        """Display scan results in terminal format"""
        terminal = TerminalGUI()

        terminal.print_header("ENTITY SCAN RESULTS")

        # Setup Quality Score
        score = self.calculate_setup_score(results)
        color = 'green' if score > 80 else 'yellow' if score > 60 else 'red'

        terminal.print_box([
            f"HA SETUP QUALITY: {score}% {self.get_score_label(score)}",
            "",
            f"✓ {len(results.scenes)} SCENES FOUND",
            f"✓ {len(results.groups)} GROUPS FOUND",
            f"✓ {len(results.areas)} AREAS CONFIGURED",
            f"⚠ {len(results.raw_lights)} RAW LIGHTS (consider grouping)",
            f"⚠ {len(results.raw_switches)} RAW SWITCHES (create scenes?)"
        ], "SYSTEM ANALYSIS")

        if score < 70:
            terminal.print_box([
                "RECOMMENDATION: Improve HA organization before proceeding",
                "• Create groups for related lights/devices",
                "• Set up scenes for common behaviors",
                "• Configure areas for all devices",
                "",
                "[C] Continue anyway  [G] Setup guide  [Q] Quit"
            ], "SETUP GUIDANCE")
```

#### 2.2 Smart Entity Classification
**File**: `/orac/terminal_gui/entity_classifier.py`

```python
class TerminalEntityClassifier:
    """Classify entities with terminal display"""

    def classify_with_display(self, entities: List[Entity]) -> ClassifiedEntities:
        terminal = TerminalGUI()

        terminal.matrix_type(">>> ANALYZING ENTITY STRUCTURE...")

        # Classify by abstraction level
        classified = self.classify_by_abstraction(entities)

        # Display classification results
        self.display_classification_matrix(classified)

        return classified

    def display_classification_matrix(self, classified: ClassifiedEntities):
        terminal = TerminalGUI()

        sections = [
            ("SCENES (RECOMMENDED)", classified.scenes, "✓"),
            ("GROUPS (RECOMMENDED)", classified.groups, "✓"),
            ("HELPERS (RECOMMENDED)", classified.helpers, "✓"),
            ("RAW DEVICES (FALLBACK)", classified.raw_devices, "⚠"),
            ("COMPLEX ENTITIES (ADVANCED)", classified.complex, "○")
        ]

        for title, entities, symbol in sections:
            if entities:
                content = []
                for entity in entities[:5]:  # Show first 5
                    complexity = f"→ {entity.complexity_score} ent" if hasattr(entity, 'complexity_score') else ""
                    content.append(f"[{symbol}] {entity.entity_id:<30} {complexity}")

                if len(entities) > 5:
                    content.append(f"... and {len(entities) - 5} more")

                terminal.print_box(content, title)
```

### Phase 3: Grammar Generation Engine

#### 3.1 Terminal Grammar Builder
**File**: `/orac/terminal_gui/grammar_builder.py`

```python
class TerminalGrammarBuilder:
    """Interactive grammar building with terminal interface"""

    async def build_grammar_interactively(self, entities: ClassifiedEntities) -> GrammarComponents:
        terminal = TerminalGUI()
        components = GrammarComponents()

        # Step 1: Location Building
        terminal.print_header("STEP 1: LOCATION CONFIGURATION")
        components.locations = await self.build_locations_interactive()

        # Step 2: Device Types
        terminal.print_header("STEP 2: DEVICE TYPE MAPPING")
        components.devices = await self.build_devices_interactive(entities)

        # Step 3: Actions
        terminal.print_header("STEP 3: ACTION DEFINITIONS")
        components.actions = await self.build_actions_interactive()

        return components

    async def build_locations_interactive(self) -> Dict[str, List[str]]:
        terminal = TerminalGUI()

        # Auto-import from HA areas
        ha_areas = await self.ha_client.get_areas()

        terminal.print_box([
            "Importing locations from Home Assistant areas...",
            "",
            "Found areas:"
        ] + [f"• {area.name}" for area in ha_areas], "HA AREA IMPORT")

        locations = {}
        for area in ha_areas:
            # Generate primary term and synonyms
            primary = self.normalize_area_name(area.name)
            synonyms = self.generate_synonyms(area.name)

            terminal.print_box([
                f"Area: {area.name}",
                f"Primary term: '{primary}'",
                f"Synonyms: {', '.join(synonyms)}",
                "",
                "[A] Accept  [E] Edit  [S] Skip"
            ], f"CONFIGURE: {area.name.upper()}")

            choice = await terminal.get_input("Choice: ")
            if choice.lower() == 'a':
                locations[primary] = synonyms
            elif choice.lower() == 'e':
                # Edit workflow
                edited = await self.edit_location_terms(primary, synonyms)
                locations[primary] = edited

        return locations

    def display_grammar_preview(self, components: GrammarComponents):
        terminal = TerminalGUI()

        # Generate GBNF
        gbnf = self.generate_gbnf(components)

        # Display in terminal
        lines = gbnf.split('\n')
        terminal.print_box([f"> {line}" for line in lines], "GENERATED GRAMMAR")

        # Show combinations count
        total_combinations = self.calculate_combinations(components)
        terminal.print_box([
            f"Total voice command combinations: {total_combinations}",
            f"Locations: {len(components.locations)}",
            f"Devices: {len(components.devices)}",
            f"Actions: {len(components.actions)}",
            "",
            "This grammar will constrain the LLM to generate only",
            "valid JSON matching your entity structure."
        ], "GRAMMAR STATISTICS")
```

### Phase 4: Smart Mapping Interface

#### 4.1 Terminal Mapping Wizard
**File**: `/orac/terminal_gui/mapping_wizard.py`

```python
class TerminalMappingWizard:
    """Interactive entity mapping with visual connections"""

    async def run_mapping_wizard(self, components: GrammarComponents, entities: ClassifiedEntities) -> MappingConfig:
        terminal = TerminalGUI()

        # Generate all combinations
        combinations = self.generate_combinations(components)

        terminal.print_header("SMART ENTITY MAPPING")
        terminal.print_box([
            f"Generated {len(combinations)} grammar combinations",
            "Now mapping to Home Assistant entities...",
            "",
            "Prioritizing: Scenes > Groups > Helpers > Raw Devices"
        ], "MAPPING STRATEGY")

        mappings = {}
        for i, combo in enumerate(combinations):
            terminal.progress_bar(int((i / len(combinations)) * 100), f"Mapping {i+1}/{len(combinations)}")

            mapping = await self.map_combination_interactive(combo, entities)
            if mapping:
                mappings[combo.key] = mapping

        return MappingConfig(mappings)

    async def map_combination_interactive(self, combo: GrammarCombination, entities: ClassifiedEntities) -> Optional[EntityMapping]:
        terminal = TerminalGUI()

        # Display combination
        terminal.print_box([
            f"Grammar: {combo.location} + {combo.device} + {combo.action}",
            f"Example: \"Turn {combo.action} the {combo.device} in the {combo.location}\"",
            "",
            "Searching for matching entities..."
        ], "MAPPING TARGET")

        # Get suggestions
        suggestions = self.get_mapping_suggestions(combo, entities)

        if not suggestions:
            return await self.handle_no_suggestions(combo)

        # Display suggestions in matrix format
        self.display_suggestion_matrix(suggestions)

        choice = await terminal.get_input("Select option [1-9] or [S]kip: ")

        if choice.lower() == 's':
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                return self.create_mapping(combo, suggestions[idx])
        except ValueError:
            pass

        return None

    def display_suggestion_matrix(self, suggestions: List[MappingSuggestion]):
        terminal = TerminalGUI()

        content = []
        for i, suggestion in enumerate(suggestions, 1):
            confidence_bar = "█" * int(suggestion.confidence / 10)
            complexity_info = f"→ {suggestion.complexity}" if suggestion.complexity else ""

            content.append(
                f"[{i}] {suggestion.entity_id:<35} "
                f"[{confidence_bar:<10}] {int(suggestion.confidence)}% "
                f"{complexity_info}"
            )

        content.extend([
            "",
            "[S] Skip this combination",
            "[C] Create new scene/group in HA",
        ])

        terminal.print_box(content, "MAPPING SUGGESTIONS")
```

#### 4.2 Value Conversion Interface
**File**: `/orac/terminal_gui/value_converter.py`

```python
class TerminalValueConverter:
    """Interactive value conversion setup"""

    def setup_value_conversions(self, mappings: MappingConfig) -> ConversionConfig:
        terminal = TerminalGUI()

        terminal.print_header("VALUE CONVERSION SETUP")

        # Find mappings that need value conversion
        numeric_mappings = [m for m in mappings.values() if m.requires_values]

        if not numeric_mappings:
            terminal.print_box([
                "No numeric value mappings detected.",
                "All your mappings use simple on/off actions."
            ], "CONVERSION STATUS")
            return ConversionConfig({})

        terminal.print_box([
            f"Found {len(numeric_mappings)} mappings requiring value conversion:",
            "",
            "ORAC uses standardized 1-100 scale for all voice commands.",
            "System will auto-convert to entity-specific ranges.",
            "",
            "Examples:",
            "• \"Set heating to 22\" → 22°C (direct)",
            "• \"Set lights to 80\" → brightness 204/255",
            "• \"Open blinds 50 percent\" → position 50%"
        ], "VALUE STANDARDIZATION")

        conversions = {}
        for mapping in numeric_mappions:
            conversion = self.setup_entity_conversion(mapping)
            if conversion:
                conversions[mapping.entity_id] = conversion

        return ConversionConfig(conversions)

    def setup_entity_conversion(self, mapping: EntityMapping) -> Optional[ValueConversion]:
        terminal = TerminalGUI()

        # Auto-detect entity value range
        entity_info = self.get_entity_info(mapping.entity_id)
        auto_conversion = self.auto_detect_conversion(entity_info)

        terminal.print_box([
            f"Entity: {mapping.entity_id}",
            f"Type: {entity_info.domain}",
            f"Current range: {auto_conversion.current_range}",
            f"Suggested 1-100 mapping: {auto_conversion.suggested_mapping}",
            "",
            "[A] Accept automatic  [C] Customize  [S] Skip"
        ], f"CONVERSION: {entity_info.friendly_name}")

        choice = await terminal.get_input("Choice: ")

        if choice.lower() == 'a':
            return auto_conversion
        elif choice.lower() == 'c':
            return await self.customize_conversion(entity_info, auto_conversion)
        else:
            return None
```

### Phase 5: Testing & Validation

#### 5.1 Terminal Testing Interface
**File**: `/orac/terminal_gui/grammar_tester.py`

```python
class TerminalGrammarTester:
    """Interactive grammar testing with HA integration"""

    async def run_testing_suite(self, grammar_config: GrammarConfig) -> TestResults:
        terminal = TerminalGUI()

        terminal.print_header("GRAMMAR TESTING SUITE")

        # Test phases
        tests = [
            ("Grammar Validation", self.test_grammar_syntax),
            ("Mapping Validation", self.test_entity_mappings),
            ("HA Integration", self.test_ha_connectivity),
            ("Voice Command Simulation", self.test_voice_commands),
            ("Performance Testing", self.test_performance)
        ]

        results = TestResults()
        for i, (name, test_func) in enumerate(tests):
            terminal.progress_bar(int((i / len(tests)) * 100), f"Running {name}")

            test_result = await test_func(grammar_config)
            results.add_test(name, test_result)

            # Display result immediately
            status = "✓ PASSED" if test_result.passed else "✗ FAILED"
            terminal.matrix_type(f">>> {name}: {status}")

            if not test_result.passed:
                terminal.print_box(test_result.errors, "TEST ERRORS")

        return results

    async def test_voice_commands_interactive(self, grammar_config: GrammarConfig):
        terminal = TerminalGUI()

        terminal.print_header("VOICE COMMAND TESTING")

        # Generate test commands
        test_commands = self.generate_test_commands(grammar_config)

        terminal.print_box([
            "Testing voice command processing pipeline:",
            "",
            "Voice Input → LLM (grammar constrained) → JSON → HA Service",
            "",
            f"Generated {len(test_commands)} test cases..."
        ], "TEST PIPELINE")

        for command in test_commands:
            await self.test_single_command(command, grammar_config)

    async def test_single_command(self, command: TestCommand, config: GrammarConfig):
        terminal = TerminalGUI()

        # Display test case
        terminal.print_box([
            f"Voice Input: \"{command.voice_input}\"",
            f"Expected: {command.expected_output}",
            "",
            "Processing..."
        ], "TEST CASE")

        # Simulate LLM processing
        llm_result = await self.simulate_llm_processing(command.voice_input, config.grammar)

        # Test mapping resolution
        if llm_result.success:
            mapping_result = await self.test_mapping_resolution(llm_result.output, config.mappings)

            # Test HA service call (dry run)
            if mapping_result.success:
                ha_result = await self.test_ha_service_call(mapping_result.service_call, dry_run=True)

                # Display complete pipeline result
                self.display_pipeline_result(command, llm_result, mapping_result, ha_result)
```

### Phase 6: Integration with Existing ORAC

#### 6.1 Topic Manager Integration
**File**: `/orac/topic_manager.py` (modifications)

```python
class TopicManager:
    """Enhanced topic manager with terminal GUI integration"""

    async def create_topic_with_wizard(self, topic_id: str) -> Topic:
        """Create new topic using terminal grammar wizard"""
        from .terminal_gui.grammar_wizard import GrammarWizard

        # Validate HA connection first
        ha_client = HomeAssistantClient()
        if not await ha_client.test_connection():
            raise HAConnectionError("Cannot connect to Home Assistant")

        # Run grammar wizard
        wizard = GrammarWizard(topic_id, ha_client)
        grammar_config = await wizard.run_wizard()

        # Generate files
        await self.generate_topic_files(topic_id, grammar_config)

        # Create topic object
        topic = Topic(
            id=topic_id,
            grammar=GrammarConfig(grammar_file=f"{topic_id}.gbnf"),
            dispatcher="homeassistant",
            config=grammar_config.to_dict()
        )

        return topic

    async def edit_topic_grammar(self, topic_id: str) -> bool:
        """Edit existing topic grammar using terminal wizard"""
        topic = self.get_topic(topic_id)
        if not topic:
            raise TopicNotFoundError(f"Topic {topic_id} not found")

        # Load existing configuration
        existing_config = self.load_topic_grammar_config(topic_id)

        # Run wizard with existing config
        wizard = GrammarWizard(topic_id, ha_client, existing_config)
        new_config = await wizard.run_wizard()

        # Backup old files
        await self.backup_topic_files(topic_id)

        # Generate new files
        await self.generate_topic_files(topic_id, new_config)

        return True
```

#### 6.2 API Integration
**File**: `/orac/api.py` (modifications)

```python
# Add new endpoints for terminal GUI

@app.route('/topics/<topic_id>/grammar/wizard', methods=['POST'])
async def start_grammar_wizard(topic_id: str):
    """Start terminal grammar wizard for topic"""
    try:
        topic_manager = TopicManager()

        # Check if topic exists
        existing_topic = topic_manager.get_topic(topic_id)

        if existing_topic:
            # Edit mode
            result = await topic_manager.edit_topic_grammar(topic_id)
        else:
            # Create mode
            topic = await topic_manager.create_topic_with_wizard(topic_id)
            result = {"created": True, "topic": topic.to_dict()}

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ha/validate', methods=['GET'])
async def validate_ha_setup():
    """Validate Home Assistant setup quality"""
    try:
        from .terminal_gui.ha_discovery import HADiscoveryService

        discovery = HADiscoveryService()
        results = await discovery.scan_entities_with_progress()
        score = discovery.calculate_setup_score(results)

        return jsonify({
            "setup_score": score,
            "entities": results.to_dict(),
            "recommendations": discovery.get_setup_recommendations(results)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## Implementation Timeline

### Sprint 1 (Current): Backend Management Foundation
- [ ] Backend management system (`backend_manager.py`)
- [ ] Backend registry and pluggable architecture (`backends/`)
- [ ] Home Assistant backend implementation
- [ ] Backend storage and configuration management
- [ ] Basic API endpoints for backend operations

### Sprint 2: Entity Import Wizard
- [ ] Entity discovery and import system
- [ ] Tile-based entity selection UI
- [ ] Entity configuration modals
- [ ] Search and filtering capabilities
- [ ] Save/load entity configurations

### Sprint 3: Backend Integration & Testing
- [ ] Backend connection testing and validation
- [ ] Entity refresh and synchronization
- [ ] Error handling and user feedback
- [ ] Backend management UI polish
- [ ] Integration testing with existing ORAC core

### Future Sprints: Grammar & Dispatching
- [ ] Grammar generation from backend entities
- [ ] Topic-backend association
- [ ] Enhanced dispatcher integration
- [ ] End-to-end voice command testing
- [ ] Advanced backend features and optimization

## Terminal UI Flow Examples

### 1. Topic Creation Flow
```
    ╔══════════════════════════════════════════════════════════════╗
    ║                    O R A C   C O R E                         ║
    ║                  TOPIC: home_automation                      ║
    ╚══════════════════════════════════════════════════════════════╝

    >>> INITIALIZING GRAMMAR GENERATION WIZARD...
    >>> CONNECTING TO HOME ASSISTANT...

    ┌─ CONNECTION STATUS ─────────────────────────────────────────┐
    │ ✓ HA URL:    http://192.168.8.99:8123                      │
    │ ✓ TOKEN:     ****************************************       │
    │ ✓ VERSION:   2024.9.1                                      │
    │ ✓ ENTITIES:  156 discovered                                │
    └─────────────────────────────────────────────────────────────┘

    >>> SCANNING ENTITY REGISTRY...

    Scanning lights...     ████████████████████████████████████ 100%
    Scanning scenes...     ████████████████████████████████████ 100%
    Scanning groups...     ████████████████████████████████████ 100%
    Scanning climate...    ████████████████████████████████████ 100%
```

### 2. Entity Selection Matrix
```
    ╔══════════════════════════════════════════════════════════════╗
    ║                  ENTITY SELECTION MATRIX                     ║
    ╚══════════════════════════════════════════════════════════════╝

    ┌─ SCENES (RECOMMENDED) ──────────────────────────────────────┐
    │ [✓] scene.lounge_evening      │ CONTROLS: 6 entities       │
    │ [✓] scene.movie_time          │ CONTROLS: 12 entities      │
    │ [✓] scene.bedtime_routine     │ CONTROLS: 8 entities       │
    │ [ ] scene.morning_wake        │ CONTROLS: 5 entities       │
    └─────────────────────────────────────────────────────────────┘

    ┌─ GROUPS (RECOMMENDED) ──────────────────────────────────────┐
    │ [✓] group.bedroom_lights      │ CONTAINS: 3 lights         │
    │ [✓] group.kitchen_appliances  │ CONTAINS: 4 switches       │
    │ [ ] group.outdoor_lighting    │ CONTAINS: 6 lights         │
    └─────────────────────────────────────────────────────────────┘

    ┌─ RAW DEVICES (FALLBACK) ────────────────────────────────────┐
    │ [ ] light.bedroom_ceiling     │ TYPE: Single light         │
    │ [ ] switch.kitchen_kettle     │ TYPE: Single switch        │
    │ [ ] climate.bedroom_ac        │ TYPE: Climate control      │
    └─────────────────────────────────────────────────────────────┘

    SELECTED: 5/156 entities    [A] Select all  [N] Next  [Q] Quit
    > _
```

### 3. Grammar Preview
```
    ╔══════════════════════════════════════════════════════════════╗
    ║                    GENERATED GRAMMAR                         ║
    ╚══════════════════════════════════════════════════════════════╝

    ┌─ GBNF OUTPUT ───────────────────────────────────────────────┐
    │ > root ::= "{" location "," device "," action "," value "}" │
    │ >                                                           │
    │ > location ::= "lounge" | "bedroom" | "kitchen"             │
    │ > device ::= "lights" | "climate" | "entertainment"         │
    │ > action ::= "on" | "off" | "set"                           │
    │ > value ::= [1-9][0-9]? | "null"                            │
    └─────────────────────────────────────────────────────────────┘

    ┌─ VOICE COMMAND EXAMPLES ────────────────────────────────────┐
    │ • "Turn on the lights in the lounge"                       │
    │ • "Set bedroom climate to 22 degrees"                      │
    │ • "Turn off kitchen entertainment"                          │
    │                                                             │
    │ TOTAL COMBINATIONS: 27                                      │
    │ MAPPED ENTITIES: 5/5 (100%)                                │
    └─────────────────────────────────────────────────────────────┘

    [T] Test commands  [S] Save grammar  [E] Edit  [Q] Quit
    > _
```

### 4. Mapping Wizard
```
    ╔══════════════════════════════════════════════════════════════╗
    ║                   SMART ENTITY MAPPING                       ║
    ╚══════════════════════════════════════════════════════════════╝

    ┌─ MAPPING TARGET ────────────────────────────────────────────┐
    │ Grammar: lounge + lights + on                               │
    │ Example: "Turn on the lights in the lounge"                │
    │                                                             │
    │ Analyzing available entities...                             │
    └─────────────────────────────────────────────────────────────┘

    ┌─ SUGGESTIONS ───────────────────────────────────────────────┐
    │ [1] scene.lounge_evening      [██████████] 95%  → 6 ent    │
    │ [2] group.lounge_lights       [████████  ] 85%  → 3 ent    │
    │ [3] light.lounge_main         [████      ] 40%  → 1 ent    │
    │                                                             │
    │ [C] Create new scene in HA                                  │
    │ [S] Skip this combination                                   │
    └─────────────────────────────────────────────────────────────┘

    Select option [1-3], [C]reate, or [S]kip: > _
```

## Technical Architecture

### File Structure
```
/orac/terminal_gui/
├── __init__.py              # Terminal UI framework
├── grammar_wizard.py        # Main wizard orchestration
├── ha_discovery.py          # HA entity scanning
├── entity_classifier.py    # Entity classification
├── grammar_builder.py      # Interactive grammar building
├── mapping_wizard.py       # Entity mapping interface
├── value_converter.py      # Value conversion setup
├── grammar_tester.py       # Testing and validation
├── ascii_art.py            # ASCII art and animations
└── themes.py               # Color schemes and styling
```

### Integration Points
1. **Topic Manager** - `create_topic_with_wizard()`, `edit_topic_grammar()`
2. **API Endpoints** - `/topics/<id>/grammar/wizard`, `/ha/validate`
3. **Dispatcher System** - Enhanced mapping file generation
4. **Grammar Parser** - Validation and testing integration

### Data Flow
```
Terminal Wizard → HA Discovery → Entity Classification →
Grammar Building → Smart Mapping → Testing → File Generation →
Topic Creation/Update
```

This implementation plan creates a comprehensive terminal-based grammar generation system that maintains ORAC's cyberpunk aesthetic while dramatically simplifying the user experience for creating voice-controlled smart home configurations.