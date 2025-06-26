# Smart Home JSON Grammar Implementation

## 🎯 Overview

This implementation converts natural language commands into strict JSON format using `llama.cpp` with GBNF grammar. It's designed to work seamlessly with the existing ORAC (Omniscient Reactive Algorithmic Core) codebase.

**Input:** `"Turn on the bathroom lights"`  
**Output:** `{"action": "turn on", "device": "bathroom lights"}`

## 📁 Files

- `data/smart_home.gbnf` - GBNF grammar file for smart home commands
- `smart_home_parser.py` - Python wrapper class for the parser
- `test_smart_home_parser.py` - Test script with automated tests and interactive mode
- `SMART_HOME_GRAMMAR_README.md` - This documentation

## 🧠 Grammar File (`data/smart_home.gbnf`)

```bnf
root ::= ws action_value "," ws "\"device\"" ws ":" ws device_value ws "}"

action_value ::= "\"" action "\""
device_value ::= "\"" device "\""

action ::= "turn on" | "turn off" | "toggle"

device ::= "bedroom lights" | "bathroom lights" | "kitchen lights" | "living room lights"

ws ::= [ \t\n]*
```

## 🔧 System Prompt

```
You are a JSON-only formatter. For each user input, respond with a single-line JSON object containing exactly these keys: "action" and "device". Do not include any explanations, comments, or additional text. Only output the JSON object.
```

## 🐍 Python Implementation

### Basic Usage

```python
from smart_home_parser import SmartHomeParser

# Initialize parser
parser = SmartHomeParser(
    model_path="./models/model.gguf",
    grammar_path="./data/smart_home.gbnf"
)

# Parse a command
result = parser.parse_command("Turn on the bathroom lights")
print(result)  # {"action": "turn on", "device": "bathroom lights"}
```

### Batch Processing

```python
commands = [
    "Turn on the bathroom lights",
    "toggle kitchen lights", 
    "Turn off bedroom lights"
]

results = parser.parse_commands_batch(commands)
for cmd, result in zip(commands, results):
    print(f"{cmd} -> {result}")
```

## 🧪 Testing

### Automated Tests

```bash
# Set your model path
export SMART_HOME_MODEL_PATH=./models/qwen2.5-0.5b.gguf

# Run automated tests
python test_smart_home_parser.py test
```

### Interactive Mode

```bash
# Run interactive testing
python test_smart_home_parser.py interactive
```

### Manual CLI Testing

```bash
# Direct llama.cpp command
llama-cli \
  -m ./models/model.gguf \
  -p 'You are a JSON-only formatter. For each user input, respond with a single-line JSON object containing exactly these keys: "action" and "device". Do not include any explanations, comments, or additional text. Only output the JSON object.\n\nUser: Turn on the bathroom lights\nAssistant: {"action": ' \
  --grammar-file ./data/smart_home.gbnf \
  -n 50 \
  --temp 0.0 \
  --no-display-prompt
```

## 📊 Test Cases

| Input | Expected Output |
|-------|----------------|
| "Turn on the bathroom lights" | `{"action": "turn on", "device": "bathroom lights"}` |
| "Turn off the kitchen lights" | `{"action": "turn off", "device": "kitchen lights"}` |
| "Toggle bedroom lights" | `{"action": "toggle", "device": "bedroom lights"}` |
| "turn on living room lights" | `{"action": "turn on", "device": "living room lights"}` |

## 🔗 Integration with ORAC

This implementation integrates seamlessly with the existing ORAC codebase:

### Using with LlamaCppClient

```python
from orac.llama_cpp_client import LlamaCppClient

# Initialize the ORAC client
client = LlamaCppClient(model_path="./models/model.gguf")

# Use custom grammar
with open("data/smart_home.gbnf", "r") as f:
    grammar = f.read()

response = await client.generate_with_custom_grammar(
    prompt="Turn on the bathroom lights",
    model="model.gguf",
    custom_grammar=grammar,
    temperature=0.0,
    system_prompt="You are a JSON-only formatter..."
)
```

### Integration with Home Assistant

The parsed JSON can be easily mapped to Home Assistant entities:

```python
# Example mapping
device_mapping = {
    "bathroom lights": ["light.bathroom_main", "light.bathroom_mirror"],
    "kitchen lights": ["light.kitchen_ceiling"],
    "bedroom lights": ["light.bedroom_lamp"],
    "living room lights": ["light.living_room_main"]
}

action_mapping = {
    "turn on": "light.turn_on",
    "turn off": "light.turn_off", 
    "toggle": "light.toggle"
}

# Convert parsed result to Home Assistant service call
def to_hass_service(parsed_result):
    device_ids = device_mapping.get(parsed_result["device"], [])
    service = action_mapping.get(parsed_result["action"])
    
    return {
        "service": service,
        "target": {"entity_id": device_ids}
    }
```

## ⚙️ Configuration

### Environment Variables

- `SMART_HOME_MODEL_PATH` - Path to your GGUF model file
- `ORAC_MODELS_PATH` - ORAC models directory (used by LlamaCppClient)

### Model Requirements

- GGUF format model file
- Compatible with llama.cpp
- Recommended: Small, fast models like Qwen2.5-0.5B for real-time processing

## 🚀 Performance Optimization

### Temperature Setting
- Set to `0.0` for maximum consistency
- Ensures deterministic output for the same input

### Token Limit
- 50 tokens is sufficient for this simple format
- Can be reduced for faster processing

### Grammar Constraints
- Grammar enforces valid combinations only
- Prevents invalid JSON output
- Reduces processing time by limiting search space

## 🔍 Error Handling

The parser includes robust error handling:

```python
# Returns fallback JSON on errors
{"action": "error", "device": "unknown"}
```

Common error scenarios:
- Model file not found
- Grammar file not found
- Invalid JSON output
- Subprocess execution errors

## 📈 Extending the Grammar

### Adding New Actions

Edit `data/smart_home.gbnf`:

```bnf
action ::= "turn on" | "turn off" | "toggle" | "dim" | "brighten"
```

### Adding New Devices

```bnf
device ::= "bedroom lights" | "bathroom lights" | "kitchen lights" | 
          "living room lights" | "thermostat" | "garage door"
```

### Complex Commands

For more complex commands, extend the grammar:

```bnf
root ::= ws action_value "," ws "\"device\"" ws ":" ws device_value "," ws "\"level\"" ws ":" ws level_value ws "}"

level_value ::= "\"" level "\""
level ::= "low" | "medium" | "high" | "50%" | "75%"
```

## 🛠️ Troubleshooting

### Common Issues

1. **Model not found**
   ```
   Error: Model file not found at ./models/model.gguf
   ```
   Solution: Set `SMART_HOME_MODEL_PATH` to correct path

2. **Grammar file not found**
   ```
   Error: Grammar file not found
   ```
   Solution: Ensure `data/smart_home.gbnf` exists

3. **Invalid JSON output**
   ```
   JSONDecodeError: Expecting value
   ```
   Solution: Check grammar syntax and model compatibility

4. **llama-cli not found**
   ```
   FileNotFoundError: [Errno 2] No such file or directory: 'llama-cli'
   ```
   Solution: Ensure llama.cpp is installed and in PATH

### Debug Mode

Enable verbose output:

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use ORAC's logger
from orac.logger import get_logger
logger = get_logger(__name__)
```

## 📚 References

- [llama.cpp Documentation](https://github.com/ggerganov/llama.cpp)
- [GBNF Grammar Specification](https://github.com/ggerganov/llama.cpp/blob/master/grammars/README.md)
- [ORAC Documentation](./README.md)
- [Home Assistant API](https://developers.home-assistant.io/docs/api/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This implementation is part of the ORAC project and follows the same licensing terms. 