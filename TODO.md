## Urgent (once working again)
- [ ] Update to Pydantic v2: Move BaseSettings to pydantic-settings package and adapt code (currently pinned to v1 due to FastAPI dependency) 

## UI Improvements

### Entity Mapping Popup System
- [ ] **Add NULL value popup to WebUI**: When users log into the WebUI (e.g., to change model prompts), show a popup if there are entities with NULL friendly names
- [ ] **Progressive entity mapping**: Show one entity at a time to avoid overwhelming users
- [ ] **Smart suggestions**: Provide intelligent friendly name suggestions based on entity_id parsing
- [ ] **Skip option**: Allow users to skip entities they don't want to control
- [ ] **Validation**: Ensure friendly names are unique and appropriate
- [ ] **API endpoints**: Add `/api/mapping/check-null` and `/api/mapping/save` endpoints
- [ ] **Integration**: Connect popup with existing auto-discovery system

### WebUI Enhancements
- [ ] **Model selection improvements**: Better model management and favorites
- [ ] **Settings persistence**: Save user preferences across sessions
- [ ] **Response formatting**: Better display of LLM responses
- [ ] **Error handling**: Improved error messages and recovery

## Grammar and Mapping System

### Grammar Manager
- [x] **Replace stub implementation**: Full grammar manager with auto-discovery integration ✅
- [x] **NULL fallback handling**: Use entity_id as friendly name when NULL encountered ✅
- [ ] **Grammar persistence**: Save generated grammar to file or database
- [ ] **Dynamic updates**: Update grammar when new entities are discovered
- [ ] **Grammar validation**: Validate grammar structure and constraints

### Entity Mapping
- [x] **Auto-discovery system**: Discover entities and generate initial mappings ✅
- [x] **YAML configuration**: Load and save mappings to entity_mappings.yaml ✅
- [x] **Bidirectional lookup**: entity_id ↔ friendly_name mapping ✅
- [ ] **Manual override support**: Allow manual editing of mappings
- [ ] **Mapping validation**: Validate mapping consistency and uniqueness

## CLI and API Integration

### CLI Commands
- [ ] **Discovery commands**: Add `discover`, `generate-mapping`, `update-grammar` commands
- [ ] **Mapping commands**: Add `list-mappings`, `add-mapping`, `remove-mapping` commands
- [ ] **Validation commands**: Add `validate-mapping`, `check-grammar` commands

### API Endpoints
- [ ] **Discovery endpoints**: `/api/discovery/run`, `/api/discovery/status`
- [ ] **Mapping endpoints**: `/api/mapping/check-null`, `/api/mapping/save`
- [ ] **Grammar endpoints**: `/api/grammar/generate`, `/api/grammar/update`

## Testing and Validation

### Test Suite
- [ ] **Comprehensive discovery tests**: Test auto-discovery with various Home Assistant setups
- [ ] **Mapping validation tests**: Test entity mapping functionality
- [ ] **Grammar generation tests**: Test grammar generation and constraints
- [ ] **UI integration tests**: Test popup system and user interactions
- [ ] **Fix existing test**: Update `test_homeassistant_data` to account for cache filtering

### Integration Testing
- [ ] **End-to-end testing**: Test complete workflow from discovery to grammar generation
- [ ] **Real Home Assistant testing**: Test with various Home Assistant configurations
- [ ] **Performance testing**: Test with large numbers of entities and services

## Documentation and Deployment

### Documentation
- [ ] **API documentation**: Document all new endpoints and parameters
- [ ] **User guide**: Guide for setting up and using the auto-discovery system
- [ ] **Developer guide**: Guide for extending and customizing the system
- [ ] **Troubleshooting**: Common issues and solutions

### Deployment
- [ ] **Configuration management**: Better configuration file management
- [ ] **Environment setup**: Automated environment setup scripts
- [ ] **Monitoring**: Add monitoring and logging for production use 