# Home Assistant Integration Plan

## Current Status
**Date**: September 4, 2025 - 14:30
**Status**: ORAC Core Ready for Deployment - HA Integration Configured

### ✅ Completed:
- Hey ORAC: Topic propagation working (master branch)
- ORAC STT: Topic forwarding implemented (master branch)  
- ORAC Core: HAExecutor class implemented with entity mappings
- Lounge Lamp: Added `switch.lounge_lamp_plug` as "lounge lamp"
- Environment: .env file created with HA_URL=http://192.168.8.99:8123
- Documentation: Updated with deployment instructions

### 🔧 Ready for Deployment:
- ORAC Core configured for Home Assistant integration
- Entity mappings include lounge lamp plug
- HAExecutor supports both light and switch entities

### ⏳ Awaiting:
- Home Assistant API token generation and .env update
- Deployment to 192.168.8.191:8000

## Phase 1: ORAC Core Deployment

### Requirements:
- Deploy ORAC Core to target hardware (192.168.8.191:8000 or dedicated server)
- Ensure grammar files are in place (`default.gbnf`)
- Configure Home Assistant connection details

### Deployment Steps:

1. **Add HA Token to .env**:
```bash
# Edit the .env file
nano /Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core/.env
# Replace YOUR_HA_TOKEN_HERE with actual token from Home Assistant
```

2. **Deploy ORAC Core**:
```bash
cd /Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core
./scripts/deploy_and_test.sh "Deploy HA integration" master
```

3. **Verify deployment**:
```bash
# Health check
curl http://192.168.8.191:8000/health

# Check topics
curl http://192.168.8.191:8000/api/v1/topics

# Test lounge lamp command
curl -X POST http://192.168.8.191:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "turn on the lounge lamp", "topic": "home_assistant"}'
```

## Phase 2: Configuration

### Hey ORAC Configuration:
```json
{
  "models": [{
    "name": "computer_v2",
    "webhook_url": "http://192.168.8.191:7272/stt/v1/stream",
    "topic": "home_assistant",
    "stt_enabled": true
  }]
}
```

### ORAC STT Configuration:
- Core endpoint: `http://192.168.8.191:8000`
- Auto-forwarding enabled
- Topic propagation active

### ORAC Core Configuration:
- Home Assistant URL: `http://192.168.8.99:8123` (configured in .env)
- HA API Token: Set in environment variable (needs to be added to .env)
- Topic grammars configured
- Entity mappings include lounge lamp (`switch.lounge_lamp_plug`)

## Phase 3: Testing Protocol

### 1. Component Health Checks
```bash
# Hey ORAC
curl http://192.168.8.99:7171/api/v1/health

# ORAC STT  
curl http://192.168.8.191:7272/stt/v1/health

# ORAC Core
curl http://192.168.8.191:8000/health
```

### 2. End-to-End Voice Test

**Test Commands:**
1. "Computer, turn on the lounge lamp"  ← Primary test target
2. "Computer, turn off the lounge lamp" ← Primary test target
3. "Computer, turn on the bedroom lights"
4. "Computer, turn off the kitchen lights"
5. "Computer, set living room lights to 50 percent"

**Expected Flow:**
1. Wake word detected by Hey ORAC
2. Audio streamed to ORAC STT with topic
3. Text transcribed and forwarded to Core
4. Core generates HA command using grammar
5. Command executed in Home Assistant
6. Device state changes

### 3. Monitoring During Tests

Open multiple terminals:
```bash
# Terminal 1: Hey ORAC logs
ssh pi "docker logs -f hey-orac | grep -E 'WAKE|topic|heartbeat'"

# Terminal 2: ORAC STT logs
ssh orin3 "docker logs -f orac-stt | grep -E 'Transcription|Core|topic'"

# Terminal 3: ORAC Core logs (adjust host as needed)
docker logs -f orac-core | grep -E 'generate|topic|home_assistant'"
```

## Phase 4: Performance Validation

### Metrics to Track:
- **End-to-end latency**: Target < 3 seconds
- **Wake word → STT**: < 500ms
- **STT transcription**: < 1s
- **Core generation**: < 500ms
- **HA execution**: < 500ms

### Success Criteria:
- [ ] All components connected and healthy
- [ ] Voice commands reliably trigger HA actions
- [ ] Latency within acceptable limits
- [ ] Error handling works gracefully
- [ ] Logs show complete flow

## Phase 5: Production Readiness

### Before Production:
1. **Security Review**
   - Verify TLS/mTLS configuration
   - Secure API tokens
   - Network isolation

2. **Reliability Testing**
   - 24-hour continuous operation
   - Network interruption recovery
   - Component restart handling

3. **Performance Optimization**
   - Profile bottlenecks
   - Optimize model loading
   - Cache frequently used data

## Troubleshooting Guide

### Common Issues:

**1. Hey ORAC not sending audio:**
- Check webhook URL configuration
- Verify network connectivity to ORAC STT
- Check topic configuration

**2. ORAC STT not forwarding to Core:**
- Verify Core endpoint configuration
- Check Core health status
- Review topic registry

**3. Core not executing HA commands:**
- Verify HA token is valid
- Check network access to HA
- Review grammar file syntax

**4. High latency:**
- Check GPU utilization on Orin
- Review network latency
- Optimize model sizes

## Questions for User

Before proceeding with integration testing, please confirm:

1. **ORAC Core Location**: Where should ORAC Core be deployed?
   - Same Orin as STT (192.168.8.191)?
   - Separate server?
   - Container or bare metal?

2. **Home Assistant Details**:
   - HA instance URL/IP?
   - API token available?
   - Which devices to test with?

3. **Test Environment**:
   - Is this production HA or test instance?
   - Are test devices available?
   - Backup/rollback plan?

## Next Actions

Once the above questions are answered:
1. Deploy ORAC Core to designated host
2. Configure all three components
3. Run end-to-end test suite
4. Document results and optimize
5. Prepare for production deployment