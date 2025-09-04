#!/bin/bash

echo "🔍 Checking Home Assistant Entities"
echo "===================================="
echo ""
echo "⚠️  This script requires your HA token to be set"
echo ""

# Check if token is provided as argument or environment variable
if [ -n "$1" ]; then
    HA_TOKEN="$1"
elif [ -n "$HA_TOKEN" ]; then
    HA_TOKEN="$HA_TOKEN"
else
    echo "Usage: $0 <HA_TOKEN>"
    echo "   or: export HA_TOKEN=your_token_here"
    echo ""
    echo "Get your token from Home Assistant:"
    echo "1. Go to http://192.168.8.99:8123"
    echo "2. Click your profile (bottom left)"
    echo "3. Create a Long-Lived Access Token"
    exit 1
fi

HA_URL="http://192.168.8.99:8123"

echo "Fetching entities from Home Assistant..."
echo ""

# Get all entities
response=$(curl -s -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    "$HA_URL/api/states")

if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to Home Assistant"
    exit 1
fi

# Check if response is valid
if echo "$response" | grep -q "401"; then
    echo "❌ Invalid token - please check your HA token"
    exit 1
fi

echo "📡 Light Entities:"
echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
lights = [e for e in data if e['entity_id'].startswith('light.')]
for light in lights:
    print(f\"  • {light['entity_id']}: {light['attributes'].get('friendly_name', 'Unknown')} - State: {light['state']}\")
" || echo "  Failed to parse lights"

echo ""
echo "🔌 Switch Entities (including plugs):"
echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
switches = [e for e in data if e['entity_id'].startswith('switch.')]
for switch in switches:
    name = switch['attributes'].get('friendly_name', 'Unknown')
    if 'lamp' in name.lower() or 'plug' in name.lower() or 'lounge' in name.lower():
        print(f\"  • {switch['entity_id']}: {name} - State: {switch['state']} ⭐\")
    else:
        print(f\"  • {switch['entity_id']}: {name} - State: {switch['state']}\")
" || echo "  Failed to parse switches"

echo ""
echo "💡 Looking for Lounge Lamp specifically..."
echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for entity in data:
    name = entity['attributes'].get('friendly_name', '').lower()
    if 'lounge' in name and ('lamp' in name or 'plug' in name):
        print(f\"  ✅ Found: {entity['entity_id']}\")
        print(f\"     Name: {entity['attributes'].get('friendly_name')}\")
        print(f\"     State: {entity['state']}\")
        print(f\"     Type: {entity['entity_id'].split('.')[0]}\")
" || echo "  Failed to find lounge lamp"