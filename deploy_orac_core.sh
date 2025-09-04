#!/bin/bash

echo "🚀 Deploying ORAC Core to 192.168.8.191:8000"
echo "========================================"

# Check if .env file exists and has token
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with HA_URL and HA_TOKEN"
    exit 1
fi

if grep -q "YOUR_HA_TOKEN_HERE" .env; then
    echo "⚠️  Warning: HA_TOKEN is not set in .env file!"
    echo "Please update the .env file with your Home Assistant token"
    echo ""
    echo "Instructions:"
    echo "1. Go to http://192.168.8.99:8123"
    echo "2. Click on your user profile (bottom left)"
    echo "3. Scroll to 'Long-Lived Access Tokens'"
    echo "4. Click 'Create Token' and name it 'ORAC Core'"
    echo "5. Copy the token and update .env file"
    echo ""
    read -p "Do you want to continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Copy files to Orin
echo ""
echo "📦 Copying files to Orin (192.168.8.191)..."
rsync -av --exclude='models/gguf/*' --exclude='__pycache__' --exclude='.git' \
    --exclude='logs/*' --exclude='cache/*' \
    ./ orin3:~/orac-core/

# Copy .env file separately to ensure it's transferred
echo "📄 Copying .env configuration..."
scp .env orin3:~/orac-core/.env

# SSH to Orin and deploy
echo ""
echo "🔧 Deploying on Orin..."
ssh orin3 << 'ENDSSH'
cd ~/orac-core

echo "🐳 Building Docker image..."
docker-compose build

echo "🛑 Stopping existing container..."
docker-compose down

echo "🚀 Starting ORAC Core..."
docker-compose up -d

echo ""
echo "⏳ Waiting for service to start..."
sleep 5

echo "🔍 Checking service status..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ ORAC Core is running!"
    echo ""
    echo "📊 Service Information:"
    curl -s http://localhost:8000/health | python3 -m json.tool
    echo ""
    echo "🎯 Testing topic system..."
    curl -s http://localhost:8000/api/v1/topics | python3 -m json.tool
else
    echo "❌ Service failed to start. Checking logs..."
    docker-compose logs --tail=50
    exit 1
fi
ENDSSH

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 ORAC Core is now available at:"
echo "   Internal: http://192.168.8.191:8000"
echo "   Health: http://192.168.8.191:8000/health"
echo "   Topics: http://192.168.8.191:8000/api/v1/topics"
echo "   Web UI: http://192.168.8.191:8000"
echo ""
echo "🧪 Test voice command flow:"
echo "   Say: 'Computer, turn on the lounge lamp'"
echo "   Say: 'Computer, turn off the lounge lamp'"
echo ""
echo "📊 Monitor logs with:"
echo "   ssh orin3 'docker logs -f orac-core'"