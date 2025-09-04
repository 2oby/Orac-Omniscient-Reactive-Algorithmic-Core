# ORAC System Integration Testing Guide

This document provides concrete step-by-step instructions for integrating and testing the **Hey_Orac** wake-word detection module with the **ORAC STT** (Speech-to-Text) service during development and testing.

## Architecture Overview

```
┌─────────────────┐    Wake detected    ┌─────────────────┐    Transcribed text    ┌─────────────────┐
│   Hey_Orac      │ ──────────────────► │   ORAC STT      │ ─────────────────────► │ Command API /   │
│ (Raspberry Pi)  │    Audio stream     │ (192.168.8.191  │     (HTTP POST)       │ ORAC Core       │
│ Wake Detection  │                     │    :7272)       │                       │ (192.168.8.191) │
└─────────────────┘                     └─────────────────┘                       └─────────────────┘
```

## Testing Environment

### Current Hardware Setup
- **Raspberry Pi** for Hey_Orac wake detection
- **NVIDIA Orin Nano** (192.168.8.191) for ORAC STT service
- **USB microphone** connected to Raspberry Pi
- **Local network** with devices on 192.168.8.x subnet

### Development Setup
- SSH access configured: `ssh orin3` for Orin Nano
- Docker installed and running on both devices
- Git repositories cloned and accessible

## Step 1: Deploy ORAC STT Service (Orin Nano)

### 1.1 Clone and Setup
```bash
# SSH to Orin Nano and setup
ssh orin3
cd ~/
git clone https://github.com/2oby/ORAC-STT.git orac-stt
cd orac-stt
cp config.toml.example config.toml
```

### 1.2 Configure ORAC STT
Edit `config.toml` with your environment settings:

```toml
[app]
log_level = "INFO"
environment = "production"

[model]
whisper_model = "base"  # Options: tiny, base, small, medium
device = "cuda"         # Use GPU acceleration
cache_dir = "/app/models"

[api]
host = "0.0.0.0"
port = 7272
max_audio_duration = 15
request_timeout = 30

[command_api]
enabled = true
url = "http://localhost:8080/command"  # Adjust for your Command API
timeout = 10
retry_attempts = 3
```

### 1.3 Deploy ORAC STT
```bash
# Build and deploy
cd scripts
./deploy_and_test.sh

# Verify deployment
curl http://192.168.8.191:7272/health
curl http://192.168.8.191:7272/stt/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "whisper-base",
  "backend": "whisper.cpp",
  "device": "cuda"
}
```

## Step 2: Deploy Hey_Orac Wake Detection (Raspberry Pi)

### 2.1 Clone and Setup
```bash
# SSH to Raspberry Pi and setup
ssh pi  # or direct access to Pi
cd ~/
git clone https://github.com/2oby/hey-orac.git
cd hey-orac
cp config/settings.json.template config/settings.json
```

### 2.2 Configure Hey_Orac
Edit `config/settings.json`:

```json
{
  "models": {
    "hey_jarvis": {
      "enabled": true,
      "threshold": 0.5,
      "type": "onnx"
    }
  },
  "audio": {
    "device_index": -1,
    "sample_rate": 16000,
    "chunk_size": 1280
  },
  "transport": {
    "endpoint": "http://192.168.8.191:7272/stt/v1/stream"
  }
}
```

**Key Configuration Points:**
- `transport.endpoint`: Must point to your ORAC STT service URL
- `audio.device_index`: Set to -1 for default microphone or specific index
- `models.threshold`: Adjust sensitivity (0.1-0.9, lower = more sensitive)

### 2.3 Deploy Hey_Orac
```bash
# Build and deploy
./scripts/build_image.sh
./scripts/deploy_and_test.sh

# Verify deployment
curl http://PI_IP_ADDRESS:7171/api/v1/health
```

## Step 3: Network Configuration

### 3.1 Update Device IP Addresses
Ensure consistent IP addressing across your network:

**In Hey_Orac `config/settings.json`:**
```json
{
  "transport": {
    "endpoint": "http://192.168.8.191:7272/stt/v1/stream"
  }
}
```

**In ORAC STT `config.toml`:**
```toml
[command_api]
url = "http://192.168.8.191:8080/command"  # Adjust for your setup
```

### 3.2 Verify Network Connectivity
```bash
# From Raspberry Pi, test ORAC STT connectivity
curl -v http://192.168.8.191:7272/health

# From Orin Nano, test if Command API is reachable
curl -v http://192.168.8.191:8080/health  # Or your command service
```

## Step 4: Integration Testing

### 4.1 End-to-End Test
1. **Start both services** and verify health endpoints
2. **Speak the wake phrase** near the microphone
3. **Monitor logs** for the complete flow:

**Hey_Orac logs** (should show):
```
2025-01-23 10:30:00 - Wake word detected: hey_jarvis (confidence: 0.85)
2025-01-23 10:30:01 - Audio captured: 3.2s, sending to STT
2025-01-23 10:30:01 - STT request successful: 'turn on the lights'
```

**ORAC STT logs** (should show):
```
2025-01-23 10:30:01 - Received audio: 3.2s, 16kHz mono
2025-01-23 10:30:01 - Transcription: 'turn on the lights' (confidence: 0.95)
2025-01-23 10:30:01 - Forwarded to command API: success
```

### 4.2 Performance Validation
Monitor these metrics during testing:

**Target Performance:**
- Wake detection latency: ≤500ms
- STT processing time: ≤500ms for 15s audio
- CPU usage: <25% on Pi, variable on Orin
- Memory usage: <250MB on Pi, 1-2GB on Orin

## Step 5: Monitoring and Maintenance

### 5.1 Health Monitoring
Quick health check commands for testing:

```bash
# Check ORAC STT health
curl -s http://192.168.8.191:7272/health | jq .
curl -s http://192.168.8.191:7272/stt/v1/health | jq .

# Check Hey_Orac health (replace with actual Pi IP)
curl -s http://PI_IP_ADDRESS:8000/api/v1/health | jq .

# Get system metrics
curl -s http://192.168.8.191:7272/metrics | grep "orac_stt"
curl -s http://PI_IP_ADDRESS:7171/metrics | grep "hey_orac"
```

### 5.2 Log Management
Monitor logs during testing:

```bash
# ORAC STT logs
ssh orin3 "docker logs --tail=50 orac-stt"

# Hey_Orac logs (adjust container name as needed)
ssh pi "docker logs --tail=50 hey-orac"
```

### 5.3 Restart Services
When updating configurations during testing:

```bash
# Restart ORAC STT service
ssh orin3 "cd ~/orac-stt && docker-compose restart"

# Restart Hey_Orac service
ssh pi "cd ~/hey-orac && docker-compose restart"
```

## Troubleshooting

### Common Issues

**1. Wake word not detected:**
- Check microphone permissions: `ls -la /dev/snd/`
- Verify audio device index in settings
- Lower threshold value (e.g., 0.3)
- Test with `docker logs -f hey-orac`

**2. STT connection fails:**
- Verify network connectivity: `ping 192.168.8.191`
- Check firewall settings on Orin Nano
- Confirm ORAC STT is running: `curl http://192.168.8.191:7272/health`

**3. High latency:**
- Check CPU/GPU usage on both devices
- Verify whisper model size (use 'tiny' for fastest response)
- Monitor network latency between devices

**4. Audio format errors:**
- Ensure 16kHz, 16-bit, mono audio format
- Check Hey_Orac audio configuration
- Verify microphone compatibility

### Debug Commands for Testing

```bash
# Test audio capture on Pi
ssh pi "arecord -d 5 -f cd test.wav && aplay test.wav"

# Test STT API directly with sample audio
curl -X POST http://192.168.8.191:7272/stt/v1/stream \
  -F "file=@test.wav" \
  -F "language=en"

# Monitor real-time logs during testing
ssh orin3 "docker logs -f orac-stt" &
ssh pi "docker logs -f hey-orac" &

# Test specific endpoints
curl -v http://192.168.8.191:7272/health
curl -v http://192.168.8.191:7272/stt/v1/health
```

## API Reference

### Hey_Orac API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Service health status |
| `/api/v1/settings` | GET | Current configuration |
| `/api/v1/settings` | PUT | Update configuration |
| `/metrics` | GET | Prometheus metrics |

### ORAC STT API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health status |
| `/stt/v1/health` | GET | STT-specific health |
| `/stt/v1/stream` | POST | Audio transcription |
| `/stt/v1/preload` | POST | Preload model |
| `/metrics` | GET | Prometheus metrics |

## Security Considerations

1. **Network Security**: Consider using TLS for production deployments
2. **Access Control**: Implement authentication if exposing APIs externally
3. **Audio Privacy**: Ensure audio data is not logged or stored permanently
4. **Device Security**: Keep Docker images and system packages updated

## Next Steps

After successful integration, consider:

1. **Adding more wake words**: Configure additional models in Hey_Orac
2. **Improving accuracy**: Fine-tune thresholds and test different environments
3. **Performance optimization**: Monitor metrics and adjust model sizes
4. **High availability**: Implement redundancy and failover mechanisms
5. **Integration with ORAC Core**: Connect STT output to your command processing system

For detailed API documentation, refer to:
- `Hey_Orac/STT_API_REFERENCE.md`
- `ORAC STT/API_REFERENCE.md`