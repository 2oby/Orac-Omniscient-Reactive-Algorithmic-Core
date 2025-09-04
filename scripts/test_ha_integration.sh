#!/bin/bash

echo "🧪 Testing ORAC Voice Pipeline with Home Assistant"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test component health
echo "1️⃣  Checking Component Health..."
echo "--------------------------------"

# Hey ORAC
echo -n "   Hey ORAC (Pi - 192.168.8.99:7171): "
if curl -s http://192.168.8.99:7171/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Online${NC}"
else
    echo -e "${RED}✗ Offline${NC}"
fi

# ORAC STT
echo -n "   ORAC STT (Orin - 192.168.8.192:7272): "
if curl -s http://192.168.8.192:7272/stt/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Online${NC}"
else
    echo -e "${RED}✗ Offline${NC}"
fi

# ORAC Core
echo -n "   ORAC Core (Orin - 192.168.8.192:8000): "
if curl -s http://192.168.8.192:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Online${NC}"
else
    echo -e "${RED}✗ Offline${NC}"
fi

echo ""
echo "2️⃣  Testing Topic Propagation..."
echo "--------------------------------"

# Check Hey ORAC settings for topic
echo "   Hey ORAC Model Configuration:"
curl -s http://192.168.8.99:7171/api/v1/settings 2>/dev/null | \
    python3 -c "import sys, json; data=json.load(sys.stdin); models=data.get('models', []); 
    for m in models: 
        if m.get('name') == 'computer_v2': 
            print(f\"      Model: {m.get('name')}\")
            print(f\"      Topic: {m.get('topic', 'Not set')}\")
            print(f\"      Webhook: {m.get('webhook_url', 'Not set')}\")"

echo ""
# Check ORAC Core topics
echo "   ORAC Core Available Topics:"
curl -s http://192.168.8.192:8000/api/v1/topics 2>/dev/null | \
    python3 -c "import sys, json; data=json.load(sys.stdin); 
    topics=data.get('topics', {});
    for topic in topics: print(f'      - {topic}')" || echo "      Failed to fetch topics"

echo ""
echo "3️⃣  Testing Grammar Generation..."
echo "--------------------------------"

# Test command generation
echo "   Testing: 'turn on the lounge lamp'"
response=$(curl -s -X POST http://192.168.8.192:8000/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt": "turn on the lounge lamp", "topic": "home_assistant"}' 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "   Generated JSON:"
    echo "$response" | python3 -c "import sys, json; 
    data=json.load(sys.stdin); 
    text=data.get('text', '');
    print(f'      {text}')" || echo "      Failed to parse response"
else
    echo -e "   ${RED}✗ Generation failed${NC}"
fi

echo ""
echo "   Testing: 'turn off the lounge lamp'"
response=$(curl -s -X POST http://192.168.8.192:8000/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt": "turn off the lounge lamp", "topic": "home_assistant"}' 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "   Generated JSON:"
    echo "$response" | python3 -c "import sys, json; 
    data=json.load(sys.stdin); 
    text=data.get('text', '');
    print(f'      {text}')" || echo "      Failed to parse response"
else
    echo -e "   ${RED}✗ Generation failed${NC}"
fi

echo ""
echo "4️⃣  Monitoring Instructions..."
echo "--------------------------------"
echo "   Open 3 terminals to monitor the flow:"
echo ""
echo "   Terminal 1 - Hey ORAC logs:"
echo "   ${YELLOW}ssh pi 'docker logs -f hey-orac | grep -E \"WAKE|topic|webhook\"'${NC}"
echo ""
echo "   Terminal 2 - ORAC STT logs:"
echo "   ${YELLOW}ssh orin3 'docker logs -f orac-stt | grep -E \"Transcription|Core|topic\"'${NC}"
echo ""
echo "   Terminal 3 - ORAC Core logs:"
echo "   ${YELLOW}ssh orin3 'docker logs -f orac-core | grep -E \"generate|home_assistant|HA\"'${NC}"
echo ""

echo "5️⃣  Voice Test Commands..."
echo "--------------------------------"
echo "   Say these commands to test:"
echo "   • \"Computer, turn on the lounge lamp\""
echo "   • \"Computer, turn off the lounge lamp\""
echo "   • \"Computer, turn on the bedroom lights\""
echo "   • \"Computer, set living room lights to 50 percent\""
echo ""
echo "   Expected flow:"
echo "   1. Wake word detected → 2. Audio sent to STT → 3. Text to Core"
echo "   4. JSON generated → 5. HA command executed → 6. Device responds"
echo ""
echo "✅ Test setup complete! Say the test commands and watch the logs."