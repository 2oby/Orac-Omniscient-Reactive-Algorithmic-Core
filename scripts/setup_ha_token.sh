#!/bin/bash

# Script to set up Home Assistant token on deployment machine
# This should be run on the Orin after deployment

echo "🔐 Home Assistant Token Setup"
echo "============================="
echo ""

# Check if we're on the Orin
if [[ ! $(hostname) =~ "orin" ]] && [[ ! $(hostname) =~ "jetson" ]]; then
    echo "⚠️  Warning: This script should be run on the Orin/Jetson device"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Navigate to ORAC Core directory
if [ -d "$HOME/orac-core" ]; then
    cd "$HOME/orac-core"
elif [ -d "/app" ]; then
    cd "/app"
else
    echo "❌ Cannot find ORAC Core directory"
    echo "Please run this from the ORAC Core directory"
    exit 1
fi

# Check if .env exists
if [ -f ".env" ]; then
    echo "📄 Found existing .env file"
    
    # Check if token is already set
    if grep -q "HA_TOKEN=YOUR_HA_TOKEN_HERE" .env || grep -q "HA_TOKEN=PLACE_HOLDER_ADD_YOUR_API_HERE" .env || ! grep -q "HA_TOKEN=" .env; then
        echo "⚠️  HA Token needs to be configured"
    else
        echo "✅ HA Token appears to be configured"
        echo ""
        echo "Current configuration:"
        grep "HA_URL=" .env || echo "HA_URL not set"
        echo "HA_TOKEN=****** (hidden)"
        echo ""
        read -p "Do you want to update the token? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
else
    echo "📝 Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        echo "❌ .env.example not found!"
        exit 1
    fi
fi

# Get HA token from user
echo ""
echo "📋 To get your Home Assistant token:"
echo "  1. Go to http://192.168.8.99:8123"
echo "  2. Click on your profile (bottom left)"
echo "  3. Scroll to 'Long-Lived Access Tokens'"
echo "  4. Click 'Create Token' and name it 'ORAC Core'"
echo "  5. Copy the generated token"
echo ""
echo "Paste your Home Assistant token (it will be hidden):"
read -s HA_TOKEN
echo ""

if [ -z "$HA_TOKEN" ]; then
    echo "❌ No token provided"
    exit 1
fi

# Update the .env file
echo "📝 Updating .env file..."

# Update HA_URL to correct address
sed -i 's|HA_URL=.*|HA_URL=http://192.168.8.99:8123|' .env

# Update HA_TOKEN
if grep -q "HA_TOKEN=" .env; then
    # Use a delimiter that won't appear in the token
    sed -i "s|HA_TOKEN=.*|HA_TOKEN=$HA_TOKEN|" .env
else
    echo "HA_TOKEN=$HA_TOKEN" >> .env
fi

echo "✅ Token configured successfully!"
echo ""
echo "🔍 Verifying configuration..."
if grep -q "HA_URL=http://192.168.8.99:8123" .env && grep -q "HA_TOKEN=$HA_TOKEN" .env; then
    echo "✅ Configuration verified"
    
    # Test the token if possible
    echo ""
    echo "🧪 Testing Home Assistant connection..."
    
    # Try to test the connection
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $HA_TOKEN" \
        http://192.168.8.99:8123/api/)
    
    if [ "$response" = "200" ]; then
        echo "✅ Successfully connected to Home Assistant!"
    elif [ "$response" = "401" ]; then
        echo "❌ Authentication failed - please check your token"
        exit 1
    else
        echo "⚠️  Could not connect to Home Assistant (HTTP $response)"
        echo "   This might be a network issue"
    fi
else
    echo "❌ Configuration failed"
    exit 1
fi

echo ""
echo "🚀 Next steps:"
echo "  1. Restart ORAC Core:"
echo "     docker-compose restart"
echo "  2. Test the integration:"
echo "     curl -X POST http://localhost:8000/v1/generate \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"prompt\": \"turn on the lounge lamp\", \"topic\": \"home_assistant\"}'"