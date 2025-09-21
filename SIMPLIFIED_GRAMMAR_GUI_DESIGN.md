# ORAC: Simplified Grammar Generation GUI Design

## Problem Statement

The current ORAC system requires users to manually create GBNF grammar files and configure complex entity mappings. This involves:

1. **Writing GBNF grammar syntax** - Technical barrier for non-developers
2. **Manual entity mapping** - Complex YAML configuration files
3. **Understanding LLM constraints** - Knowledge of how grammar constrains output
4. **Entity ID management** - Matching grammar terms to HA entity IDs
5. **HA Setup Prerequisites** - No guidance on creating proper abstractions first

This complexity prevents Home Assistant power users from leveraging ORAC's voice control capabilities, even when they have well-organized HA configurations.

## Current System Analysis

### Technical Complexity Issues

**Grammar File Creation**:
```gbnf
root ::= "{" ws "action" ws ":" ws action_value "," ws "device" ws ":" ws device_value "}"
action ::= "turn on" | "turn off" | "toggle" | "set"
device ::= "bedroom lights" | "bathroom lights" | "kitchen lights"
```

**Mapping Configuration**:
```yaml
mappings:
  "bedroom|lights": "light.bedroom_lights"
  "kitchen|lights": ""                    # TODO: Map this
  "bathroom|lights": "IGNORE"
```

### User Pain Points

1. **Syntax Knowledge Required** - Users must learn GBNF grammar syntax
2. **Entity Discovery** - Manual process to find available HA entities
3. **Mapping Maintenance** - Updates required when HA entities change
4. **Error-Prone Process** - Typos in grammar or mappings break functionality
5. **No Visual Feedback** - Text-only configuration with no preview

## Prerequisites: Home Assistant Setup Expectations

### Target User Profile

**ORAC targets Home Assistant power users** who have already invested effort in organizing their smart home with proper abstractions. Users should have:

- **Well-organized HA installation** with scenes, groups, and areas configured
- **Meaningful entity naming** following consistent conventions
- **Abstraction layers** that represent real-world actions, not raw device controls
- **Experience with HA concepts** like scripts, automations, and helper entities

### Required HA Organization

Before using ORAC's grammar builder, users should create appropriate abstractions:

**Scenes for Complex Behaviors**:
```yaml
# scene.lounge_evening - Multiple entities working together
scene:
  name: "Lounge Evening"
  entities:
    light.lounge_main: {brightness: 128, color_temp: 454}
    light.lounge_accent: {brightness: 64}
    cover.lounge_blinds: closed
    climate.lounge: {temperature: 21}
    media_player.lounge_tv: "off"
```

**Groups for Logical Collections**:
```yaml
# group.lounge_lights - All lighting as single unit
group:
  lounge_lights:
    name: "Lounge Lights"
    entities:
      - light.lounge_main
      - light.lounge_accent
      - light.lounge_floor_lamp
```

**Helper Entities for Value Control**:
```yaml
# input_number.lounge_brightness - Standardized 0-100 control
input_number:
  lounge_brightness:
    name: "Lounge Brightness"
    min: 0
    max: 100
    step: 5
    unit_of_measurement: "%"
```

### Documentation and Setup Guide

ORAC will include comprehensive setup documentation:

1. **HA Organization Best Practices** - How to structure entities for voice control
2. **Naming Conventions** - Consistent patterns for locations and devices
3. **Scene Creation Examples** - Templates for common room configurations
4. **Testing Your Setup** - Validation checklist before grammar generation

## Proposed Solution: Tile-Based Grammar Builder

### Core Concept

Replace manual grammar writing with a visual tile-based interface that assumes a well-organized HA setup:

1. **Entity Tiles** represent HA abstractions (scenes, groups, helpers)
2. **Grammar Tiles** represent simplified voice command structure (location + device + action)
3. **Smart Mapping** connects simple grammar to complex HA entities
4. **Auto-Generation** creates GBNF and mapping files

### Design Principles

- **Clean HA Assumption** - Target users with proper abstractions already in place
- **Simple Grammar, Complex Mapping** - Grammar stays predictable, mapping handles complexity
- **Standardized Values** - Use 1-100 scale, let dispatcher convert to entity-specific ranges
- **Abstraction Priority** - Scenes and groups are first-class, raw entities are escape hatches
- **Progressive Enhancement** - System learns and suggests improvements over time

## Proposed User Flow

### Phase 1: Entity Discovery & Selection

**1.1 Auto-Discovery with HA Setup Validation**
```
┌─────────────────────────────────────────────────────────────┐
│ Discovering Home Assistant Entities                         │
│ ●●●●●●●●●● 100% Complete                                    │
│                                                             │
│ Found: 156 entities                                         │
│ ✅ 12 scenes (Well organized!)                             │
│ ✅ 8 groups (Good abstractions)                            │
│ ✅ 5 areas configured                                       │
│ ⚠️  23 raw lights (Consider grouping)                      │
│ ⚠️  15 individual switches (Create scenes?)                │
│                                                             │
│ [View Setup Recommendations] [Continue Anyway]             │
└─────────────────────────────────────────────────────────────┘
```

**1.2 Smart Classification & Auto-Enable**
- **Scenes/Groups/Helpers**: Auto-enabled (proper abstractions)
- **Raw Devices**: Disabled by default (fallback option)
- **Complex Entities**: Disabled by default (automations, sensors)

**1.3 Abstraction-First Selection Interface**
```
Entity Categories                              [Setup Guide] [HA Config]

🎭 Scenes (Recommended - Complex Behaviors)    ✅ 12 enabled
  ✅ scene.lounge_evening               "Lounge Evening" → 6 entities
  ✅ scene.movie_time                   "Movie Time" → 12 entities
  ✅ scene.bedtime_routine              "Bedtime Routine" → 8 entities

👥 Groups (Recommended - Logical Collections)  ✅ 8 enabled
  ✅ group.lounge_lights                "Lounge Lights" → 3 lights
  ✅ group.bedroom_climate              "Bedroom Climate" → 2 devices
  ✅ group.kitchen_appliances           "Kitchen Appliances" → 4 switches

🎛️  Helpers (Recommended - Value Controls)      ✅ 5 enabled
  ✅ input_number.lounge_brightness     "Lounge Brightness" (0-100)
  ✅ input_number.bedroom_temp          "Bedroom Temperature" (15-25°C)

💡 Raw Lights (Fallback)                       ❌ 23 available
  ❌ light.bedroom_ceiling              "Bedroom Ceiling" (No group?)
  ❌ light.kitchen_under_cabinet        "Kitchen Under Cabinet"

🔌 Raw Switches (Fallback)                     ❌ 15 available
🌡️  Sensors (Advanced)                          ❌ 45 available
```

### Phase 2: Grammar Structure Definition

**2.1 Standardized Command Pattern**
```
ORAC uses a single, consistent command pattern:

✅ Location + Device + Action + [Value]
   "Turn on the lights in the lounge"        → {location: lounge, device: lights, action: on}
   "Set heating to 22 degrees in bedroom"    → {location: bedroom, device: heating, action: set, value: 22}
   "Open the blinds 50 percent in kitchen"   → {location: kitchen, device: blinds, action: set, value: 50}

🎯 Grammar Advantage: Simple structure, complex mapping
   User says: "living room" → LLM constrained to: "lounge"
   Grammar device: "lights" → Maps to: scene.lounge_evening (dozens of entities)
   Value: 22 → Dispatcher converts: 22°C for climate, 22% for brightness, etc.
```

**2.2 Area-Based Location Builder**

```
Locations (from HA Areas + Custom)              [Import from HA] [+ Add Custom]
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 🏠 Lounge       │ │ 🛏️ Bedroom      │ │ 🍳 Kitchen      │
│ Primary: lounge │ │ Primary: bedroom│ │ Primary: kitchen│
│ Alt: living_room│ │ Alt: master     │ │ Alt: dining     │
│ Alt: front_room │ │ Alt: main_bed   │ │ Alt: cooking    │
│ HA Area: Living │ │ HA Area: Master │ │ HA Area: Kitchen│
└─────────────────┘ └─────────────────┘ └─────────────────┘

Device Types (from enabled entities)           [+ Add Device Type]
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 💡 Lights       │ │ 🌡️ Climate      │ │ 🎵 Entertainment│
│ lights, lighting│ │ heating, temp   │ │ tv, music, sound│
│ lamps, bulbs    │ │ cooling, aircon │ │ stereo, speakers│
│ → 8 entities    │ │ → 3 entities    │ │ → 2 entities    │
└─────────────────┘ └─────────────────┘ └─────────────────┘

Actions (Standardized)                         [+ Add Action]
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ ⚡ Toggle        │ │ 📊 Set (1-100)   │ │ ❓ Query (Future)│
│ on, off, toggle │ │ set, adjust     │ │ status, check   │
│ → Binary states │ │ → Numeric values│ │ → Read-only     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Phase 3: Smart Entity Mapping Interface

**3.1 Abstraction-Aware Mapping Board**
```
Grammar → Entity Mapping (Simple Commands → Complex Behaviors)

GRAMMAR COMBINATIONS                  HOME ASSISTANT ENTITIES
┌─────────────────────────┐          ┌─────────────────────────┐
│ 🏠 Lounge               │   ────── │ 🎬 scene.lounge_evening │
│ 💡 Lights               │          │   → 3 lights + blinds  │
│ ⚡ Toggle               │          │   → 6 total entities    │
│ ℹ️  "turn on lights"     │          │ 🔧 Service: scene.turn_on│
└─────────────────────────┘          └─────────────────────────┘

┌─────────────────────────┐          ┌─────────────────────────┐
│ 🛏️ Bedroom              │   ────── │ 🎛️ input_number.bed_temp │
│ 🌡️ Climate              │          │   → 15-25°C range      │
│ 📊 Set Value (1-100)    │          │ 🔧 Auto-convert scale   │
│ ℹ️  "set heating to 22"  │          │ 💡 Triggers automation │
└─────────────────────────┘          └─────────────────────────┘

┌─────────────────────────┐          ┌─────────────────────────┐
│ 🍳 Kitchen              │   ────── │ 👥 group.kitchen_lights │
│ 💡 Lights               │          │   → 2 ceiling + 1 under│
│ 📊 Set Value (1-100)    │          │ 🔧 Service: light.turn_on│
│ ℹ️  "set lights to 80"   │          │ 💡 Brightness: 0-255    │
└─────────────────────────┘          └─────────────────────────┘

┌─────────────────────────┐          ┌─────────────────────────┐
│ 🛏️ Bedroom              │   ❌     │ ❌ Unmapped Combination │
│ 🎵 Entertainment        │          │ 💡 Suggestion: Create   │
│ ⚡ Toggle               │          │    bedroom_music scene? │
│ ℹ️  "turn on music"      │          │ [Create Scene] [Skip]   │
└─────────────────────────┘          └─────────────────────────┘

Mapped: 12/15 combinations          Suggestions: 2          [Export Config]
```

**3.2 Context-Aware Mapping Suggestions**
```
Smart Mapping Suggestions (HA-Structure Aware):

┌─────────────────────────────────────────────────────────────┐
│ 🤖 "bedroom + entertainment + toggle" needs mapping:       │
│                                                             │
│ 🏆 RECOMMENDED (Create abstraction in HA):                 │
│    scene.bedroom_music → TV on, speakers on, lights dim    │
│    [Open HA Scene Editor] [Create for me]                  │
│                                                             │
│ 🔄 FALLBACK OPTIONS (Use existing entities):               │
│ ✅ media_player.bedroom_tv     [Confidence: 85%]           │
│ ❓ switch.bedroom_speakers     [Confidence: 60%]           │
│ ❓ automation.bedroom_media    [Confidence: 40%]           │
│                                                             │
│ [Use Recommendation] [Pick Fallback] [Skip for now]        │
└─────────────────────────────────────────────────────────────┘
```

### Phase 4: Grammar Preview & Real-World Testing

**4.1 Generated Grammar with Abstraction Context**
```
Generated GBNF Grammar                    [Edit] [Regenerate] [Export]

┌─────────────────────────────────────────────────────────────┐
│ root ::= "{" location "," device "," action "," value "}"   │
│                                                             │
│ location ::= "lounge" | "bedroom" | "kitchen"               │
│ device ::= "lights" | "climate" | "entertainment"           │
│ action ::= "on" | "off" | "set"                             │
│ value ::= [1-9][0-9]? | "null"  # 1-100 scale               │
└─────────────────────────────────────────────────────────────┘

Generated Mapping File (Entity → HA Service Calls):
┌─────────────────────────────────────────────────────────────┐
│ mappings:                                                   │
│   "lounge|lights|on":                                       │
│     entity_id: "scene.lounge_evening"                       │
│     service: "scene.turn_on"                                │
│     complexity: "6 entities controlled"                     │
│                                                             │
│   "bedroom|climate|set":                                    │
│     entity_id: "input_number.bedroom_temp"                  │
│     service: "input_number.set_value"                       │
│     value_conversion: "1-100 → 15-25°C"                     │
│                                                             │
│   "kitchen|lights|set":                                     │
│     entity_id: "group.kitchen_lights"                       │
│     service: "light.turn_on"                                │
│     value_conversion: "1-100 → 0-255 brightness"            │
└─────────────────────────────────────────────────────────────┘

Coverage: 12/15 combinations mapped (80%)    [View Unmapped] [Setup Help]
```

**4.2 Real Voice Command Testing with HA Integration**
```
Test Your Voice Commands                    [🎤 Live Test] [HA Test Mode]

Actual Usage Examples:                  Expected → Actual Result:
┌─────────────────────┐   ┌─────────────────────────────────────┐
│ "Turn on the lights │   │ Grammar: {location: lounge,         │
│  in the living room"│ → │          device: lights,            │
│                     │   │          action: on}                │
│                     │   │ HA Call: scene.turn_on              │
│                     │   │ Result: ✅ 6 entities activated     │
└─────────────────────┘   └─────────────────────────────────────┘

┌─────────────────────┐   ┌─────────────────────────────────────┐
│ "Set bedroom heating│   │ Grammar: {location: bedroom,        │
│  to 22 degrees"     │ → │          device: climate,           │
│                     │   │          action: set, value: 22}    │
│                     │   │ Conversion: 22 → 22°C               │
│                     │   │ Result: ✅ Temperature updated      │
└─────────────────────┘   └─────────────────────────────────────┘

┌─────────────────────┐   ┌─────────────────────────────────────┐
│ "Turn kitchen lights│   │ Grammar: {location: kitchen,        │
│  to half brightness"│ → │          device: lights,            │
│                     │   │          action: set, value: 50}    │
│                     │   │ Conversion: 50 → brightness 128     │
│                     │   │ Result: ✅ 3 lights dimmed to 50%   │
└─────────────────────┘   └─────────────────────────────────────┘

✅ All tests passed with HA     [Save Configuration] [Deploy to ORAC]
```

## Technical Implementation

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web GUI       │    │  Grammar Gen    │    │  File Output    │
│                 │ → │                 │ → │                 │
│ - Entity Tiles  │    │ - GBNF Builder  │    │ - .gbnf files   │
│ - Drag & Drop   │    │ - Mapping Gen   │    │ - .yaml files   │
│ - Visual Map    │    │ - Validation    │    │ - Topic config  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

**1. Entity Discovery Service**
```python
class EntityDiscoveryService:
    def discover_ha_entities(self) -> Dict[str, List[Entity]]:
        """Auto-discover and categorize HA entities"""

    def validate_ha_setup(self) -> SetupValidation:
        """Check if HA has good abstractions for voice control"""
        # Check for scenes, groups, areas, helper entities
        # Score setup quality and suggest improvements

    def suggest_abstractions(self) -> List[AbstractionSuggestion]:
        """Find missing abstractions that should be created"""
        # "You have 5 bedroom lights but no bedroom_lights group"
        # "Consider creating scene.movie_time for entertainment"

    def classify_by_abstraction_level(self) -> Dict[str, List[Entity]]:
        """Prioritize scenes/groups over raw entities"""
        # Return: {"scenes": [...], "groups": [...], "helpers": [...], "raw": [...]}
```

**2. Grammar Builder Service**
```python
class GrammarBuilderService:
    def build_location_vocabulary(self, ha_areas: List[str], custom_names: List[str]) -> Dict[str, List[str]]:
        """Generate location terms with synonyms from HA areas"""
        # {"lounge": ["lounge", "living_room", "front_room"], ...}

    def build_device_vocabulary(self, enabled_abstractions: List[Entity]) -> Dict[str, List[str]]:
        """Generate device terms based on abstraction types"""
        # Group scenes/groups by function: lighting, climate, entertainment

    def generate_standardized_gbnf(self, components: GrammarComponents) -> str:
        """Create GBNF with location+device+action+value pattern"""
        # Always generates: {location, device, action, value} structure

    def validate_grammar_coverage(self, grammar: str, entities: List[Entity]) -> CoverageReport:
        """Check how many enabled entities can be controlled"""
```

**3. Smart Mapping Generator Service**
```python
class SmartMappingService:
    def generate_grammar_combinations(self, grammar: GrammarComponents) -> List[Combination]:
        """Generate all location+device+action combinations"""

    def suggest_abstraction_mapping(self, combination: Combination) -> List[MappingSuggestion]:
        """Prioritize scenes/groups, suggest creating missing ones"""
        # "bedroom+entertainment" → "Create scene.bedroom_music?"
        # "lounge+lights" → "Use scene.lounge_evening (6 entities)"

    def generate_service_call_mapping(self, mappings: Dict) -> ServiceCallConfig:
        """Generate HA service calls for each grammar combination"""
        # Map to specific service calls: scene.turn_on, light.turn_on, etc.

    def validate_entity_accessibility(self, mappings: Dict) -> ValidationResult:
        """Test actual HA API calls for each mapping"""
```

### Data Models

**Enhanced Data Models**
```python
@dataclass
class Entity:
    entity_id: str
    friendly_name: str
    domain: str
    device_class: Optional[str]
    area: Optional[str]
    abstraction_level: AbstractionLevel  # SCENE, GROUP, HELPER, RAW
    complexity_score: int  # How many underlying entities this controls
    enabled: bool = False

@dataclass
class GrammarComponent:
    name: str
    primary_term: str  # Main term used in grammar
    synonyms: List[str]  # Alternative terms user might say
    component_type: ComponentType  # LOCATION, DEVICE, ACTION
    source: ComponentSource  # HA_AREA, USER_DEFINED, AUTO_GENERATED

@dataclass
class SmartMapping:
    grammar_combination: str  # "lounge|lights|on"
    entity_id: str
    service_call: str  # "scene.turn_on", "light.turn_on", etc.
    value_conversion: Optional[ValueConversion]  # 1-100 → entity scale
    complexity_info: str  # "Controls 6 entities", "Single device"
    mapping_type: MappingType  # ABSTRACTION_PREFERRED, RAW_FALLBACK
    confidence: float

@dataclass
class ValueConversion:
    input_range: Tuple[int, int]  # (1, 100)
    output_range: Tuple[float, float]  # (15.0, 25.0) for temperature
    unit: str  # "°C", "%", "brightness"
    service_parameter: str  # "temperature", "brightness_pct"
```

### Value Standardization System

**Enhanced Value Standardization**
```python
class ValueStandardizer:
    """Standardizes all numeric values to 1-100 scale for consistent voice commands"""

    def __init__(self, ha_client: HomeAssistantClient):
        self.ha_client = ha_client
        self.conversion_cache = {}  # Cache entity value ranges

    def standardize_input(self, value: int, entity_id: str, action_type: str) -> int:
        """Convert user spoken value to 1-100 scale"""
        # "22 degrees" → 22 (already in user-friendly scale)
        # "half brightness" → 50
        # "full volume" → 100
        return max(1, min(100, value))

    def convert_for_entity(self, standardized_value: int, entity_id: str) -> Dict[str, Any]:
        """Convert 1-100 to entity-specific service call parameters"""
        entity_info = self._get_entity_info(entity_id)

        if entity_info.domain == "climate":
            # 1-100 → 15-25°C (or user's configured range)
            temp_range = self._get_climate_range(entity_id)
            actual_temp = self._scale_value(standardized_value, 1, 100, *temp_range)
            return {"temperature": actual_temp}

        elif entity_info.domain == "light":
            # 1-100 → 0-255 brightness
            brightness = self._scale_value(standardized_value, 1, 100, 0, 255)
            return {"brightness": int(brightness)}

        elif entity_info.domain == "cover":
            # 1-100 → 0-100 position (already correct scale)
            return {"position": standardized_value}

        elif entity_info.domain == "input_number":
            # 1-100 → entity's min-max range
            entity_range = self._get_input_number_range(entity_id)
            actual_value = self._scale_value(standardized_value, 1, 100, *entity_range)
            return {"value": actual_value}

    def _scale_value(self, value: int, in_min: int, in_max: int,
                    out_min: float, out_max: float) -> float:
        """Linear scaling between ranges"""
        return out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min)
```

## Benefits of Proposed Solution

### For Users
- **Leverages Existing HA Knowledge** - Works with scenes/groups users already understand
- **Simple Voice Commands, Complex Results** - "Turn on lounge lights" can control dozens of entities
- **Consistent Value System** - All numeric commands use 1-100 scale regardless of device
- **Smart Setup Guidance** - Suggests HA improvements for better voice control
- **Future-Proof Configuration** - System learns and suggests improvements over time

### For System
- **Clean Architecture Separation** - Simple grammar, complex mapping, smart dispatch
- **Abstraction-First Design** - Prioritizes proper HA organization over raw entities
- **Standardized Value Handling** - Dispatcher handles all unit conversions automatically
- **Progressive Enhancement Ready** - Infrastructure for ML-based optimization
- **HA Best Practices Enforcement** - Guides users toward maintainable smart home setups

## Implementation Phases

### Phase 1: Core Infrastructure (MVP)
- HA setup validation and guidance
- Abstraction-first entity discovery
- Standardized grammar generation (location+device+action+value)
- Basic mapping interface with service call generation

### Phase 2: Smart Mapping Features
- HA setup quality scoring
- Missing abstraction detection and suggestions
- Smart entity mapping with complexity awareness
- Value conversion system for all entity types

### Phase 3: Progressive Enhancement
- Usage pattern analysis and logging
- ML-based mapping optimization ("dreaming" LLM)
- Automatic HA scene/group suggestions
- Performance analytics and bottleneck detection

### Phase 4: Advanced Intelligence
- Multi-user pattern recognition
- Context-aware command optimization
- Predictive mapping improvements
- Integration with HA configuration management

## Alternative Approaches Considered

### 1. Natural Language Grammar Generation
**Approach**: Let users describe commands in plain English, auto-generate grammar
**Pros**: Most intuitive for users
**Cons**: Complex NLP, unpredictable results, harder to debug

### 2. Template-Based System
**Approach**: Pre-built grammar templates users can customize
**Pros**: Faster setup, proven patterns
**Cons**: Less flexible, may not fit all HA setups

### 3. Code Generation Wizard
**Approach**: Wizard that generates Python code instead of grammar files
**Pros**: More powerful, easier to extend
**Cons**: Abandons existing GBNF infrastructure, requires code knowledge

## Progressive Enhancement: The "Dreaming" LLM

### Concept: Automated System Optimization

ORAC will include a unique progressive enhancement system that learns from usage patterns:

**Daily Learning Cycle**:
```python
class ProgressiveEnhancementService:
    def analyze_daily_usage(self, usage_logs: List[CommandLog]) -> OptimizationSuggestions:
        """Nightly analysis of voice command patterns"""
        # Analyze: voice input → LLM output → HA service call → result
        # Identify: patterns, failures, suboptimal mappings

    def dream_optimizations(self, patterns: UsagePatterns) -> List[Suggestion]:
        """Use powerful LLM to suggest improvements during low-usage hours"""
        # "Users often say 'movie time' but you only control lights.
        #  Suggest creating scene.movie_time that also dims blinds and sets TV."

    def suggest_ha_improvements(self, optimization: Suggestion) -> HAConfigSuggestion:
        """Generate actual HA configuration for suggested improvements"""
        # Auto-generate YAML for new scenes, groups, automations
```

**Example Learning Scenarios**:

1. **Pattern Recognition**:
   - User frequently says "movie time" → maps to `light.lounge_main: off`
   - System suggests: Create `scene.movie_time` that also closes blinds, dims other lights

2. **Failure Analysis**:
   - Command "set bedroom temperature to 18" often fails
   - System discovers: User's climate entity has 20°C minimum
   - Suggests: Adjust value conversion or recommend different thermostat settings

3. **Usage Optimization**:
   - Multiple commands often used in sequence
   - Suggests: Create composite scenes that handle multiple actions

### Implementation Strategy

**Data Collection** (Privacy-Conscious):
```python
@dataclass
class CommandLog:
    timestamp: datetime
    voice_input: str  # "turn on the lounge lights"
    grammar_output: Dict  # {location: lounge, device: lights, action: on}
    ha_service_call: str  # "scene.turn_on"
    entity_id: str  # "scene.lounge_evening"
    success: bool
    response_time: float
    user_satisfaction: Optional[bool]  # If user immediately adjusted
```

**Nightly Analysis** (Low-Priority Background Process):
```python
def dream_session(command_history: List[CommandLog]) -> List[OptimizationSuggestion]:
    """Run during low-usage hours with powerful LLM"""

    analysis_prompt = f"""
    Analyze these voice command patterns from a smart home system:

    {format_usage_patterns(command_history)}

    The system uses scenes/groups in Home Assistant for complex behaviors.
    Current HA configuration: {get_current_ha_config()}

    Suggest improvements:
    1. Missing scenes that would better serve user patterns
    2. Mapping optimizations for better voice control
    3. Value range adjustments for more natural commands
    4. Entity organization improvements

    Focus on practical suggestions that improve daily usage.
    """

    return powerful_llm.analyze(analysis_prompt)
```

## Recommendation

The **Smart Grammar Builder with Progressive Enhancement** creates a system that:

- **Starts Simple** - Works with existing HA setups, guides users toward better organization
- **Grows Smarter** - Learns from actual usage patterns to suggest concrete improvements
- **Maintains Control** - Users approve all suggestions, system never makes changes automatically
- **Scales Naturally** - Better HA organization → better voice control → more usage → more learning

This transforms ORAC from a static configuration tool into an intelligent assistant that helps users optimize their entire smart home setup over time, making both HA and voice control more effective.

## Next Steps

### Immediate Development (Phase 1)
1. **HA Setup Validator** - Build service to analyze and score HA organization quality
2. **Abstraction-First Discovery** - Prioritize scenes/groups in entity selection UI
3. **Standardized Grammar Generator** - Always generate location+device+action+value pattern
4. **Smart Mapping Interface** - Visual mapping with service call generation and value conversion
5. **HA Integration Testing** - Validate generated configurations with real HA instances

### Documentation Priority
1. **HA Setup Guide** - Best practices for organizing HA before using ORAC
2. **Scene/Group Templates** - Examples for common room and device combinations
3. **Value Standardization Guide** - How 1-100 scale maps to different entity types
4. **Troubleshooting Guide** - Common setup issues and solutions

### Future Development (Phases 2-4)
1. **Usage Analytics Infrastructure** - Logging and pattern analysis foundation
2. **Progressive Enhancement Service** - "Dreaming" LLM for optimization suggestions
3. **HA Configuration Generator** - Auto-create scene/group YAML from suggestions
4. **Community Learning** - Anonymized pattern sharing for better suggestions

### Success Metrics
- **Setup Success Rate** - % of users who complete grammar generation
- **Mapping Coverage** - % of selected entities successfully mapped
- **Usage Satisfaction** - Voice command success rate in daily use
- **HA Improvement Adoption** - % of users who implement suggested HA changes

This approach targets HA power users first, then uses their success patterns to build better guidance for all users, creating a positive feedback loop that improves both ORAC and Home Assistant setup quality.