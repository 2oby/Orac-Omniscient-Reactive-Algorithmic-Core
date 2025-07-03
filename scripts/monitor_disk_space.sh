#!/usr/bin/env bash
set -euo pipefail

# Disk Space Monitoring Script for ORAC
# Monitors disk usage and triggers cleanup when thresholds are exceeded

# Configuration
DISK_THRESHOLD_PERCENT=80
DOCKER_THRESHOLD_GB=50
LOG_THRESHOLD_GB=1
MODEL_THRESHOLD_GB=10
ALERT_EMAIL=""  # Optional: email for alerts

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

# Get disk usage percentage
get_disk_usage() {
    df / | awk 'NR==2 {print $5}' | sed 's/%//'
}

# Get directory size in GB
get_directory_size_gb() {
    local dir="$1"
    if [ -d "$dir" ]; then
        du -s "$dir" 2>/dev/null | awk '{print $1/1024/1024}' || echo "0"
    else
        echo "0"
    fi
}

# Get Docker disk usage
get_docker_usage() {
    docker system df 2>/dev/null | grep "Build Cache" | awk '{print $4}' | sed 's/GB//' || echo "0"
}

# Check if cleanup is needed
check_cleanup_needed() {
    local disk_usage=$(get_disk_usage)
    local docker_usage=$(get_docker_usage)
    local log_size=$(get_directory_size_gb "/app/logs")
    local model_size=$(get_directory_size_gb "/app/models/gguf")
    
    local needs_cleanup=false
    local reasons=()
    
    if [ "$disk_usage" -gt "$DISK_THRESHOLD_PERCENT" ]; then
        needs_cleanup=true
        reasons+=("Disk usage: ${disk_usage}% (threshold: ${DISK_THRESHOLD_PERCENT}%)")
    fi
    
    if (( $(echo "$docker_usage > $DOCKER_THRESHOLD_GB" | bc -l) )); then
        needs_cleanup=true
        reasons+=("Docker build cache: ${docker_usage}GB (threshold: ${DOCKER_THRESHOLD_GB}GB)")
    fi
    
    if (( $(echo "$log_size > $LOG_THRESHOLD_GB" | bc -l) )); then
        needs_cleanup=true
        reasons+=("Log directory: ${log_size}GB (threshold: ${LOG_THRESHOLD_GB}GB)")
    fi
    
    if (( $(echo "$model_size > $MODEL_THRESHOLD_GB" | bc -l) )); then
        needs_cleanup=true
        reasons+=("Model directory: ${model_size}GB (threshold: ${MODEL_THRESHOLD_GB}GB)")
    fi
    
    echo "$needs_cleanup"
    if [ ${#reasons[@]} -gt 0 ]; then
        printf '%s\n' "${reasons[@]}"
    fi
}

# Send alert (placeholder for future implementation)
send_alert() {
    local message="$1"
    warn "ALERT: $message"
    
    # TODO: Implement email alerts if ALERT_EMAIL is set
    if [ -n "$ALERT_EMAIL" ]; then
        echo "Alert: $message" | mail -s "ORAC Disk Space Alert" "$ALERT_EMAIL" 2>/dev/null || true
    fi
}

# Main monitoring function
monitor_disk_space() {
    log "Starting disk space monitoring..."
    
    # Get current usage
    local disk_usage=$(get_disk_usage)
    local docker_usage=$(get_docker_usage)
    
    log "Current disk usage: ${disk_usage}%"
    log "Current Docker build cache: ${docker_usage}GB"
    
    # Check if cleanup is needed
    local cleanup_result=$(check_cleanup_needed)
    local needs_cleanup=$(echo "$cleanup_result" | head -n 1)
    local reasons=$(echo "$cleanup_result" | tail -n +2)
    
    if [ "$needs_cleanup" = "true" ]; then
        warn "Cleanup needed!"
        echo "$reasons" | while read -r reason; do
            warn "  - $reason"
        done
        
        send_alert "Disk space cleanup needed: $(echo "$reasons" | tr '\n' '; ')"
        
        # Trigger cleanup
        log "Triggering automatic cleanup..."
        if [ -f "/app/scripts/docker_cleanup.sh" ]; then
            bash /app/scripts/docker_cleanup.sh
        else
            warn "Cleanup script not found, running basic cleanup..."
            docker system prune -f 2>/dev/null || true
            docker image prune -a -f 2>/dev/null || true
            docker volume prune -f 2>/dev/null || true
        fi
        
        # Check again after cleanup
        local new_disk_usage=$(get_disk_usage)
        local new_docker_usage=$(get_docker_usage)
        
        log "After cleanup - Disk usage: ${new_disk_usage}%, Docker cache: ${new_docker_usage}GB"
        
        if [ "$new_disk_usage" -lt "$DISK_THRESHOLD_PERCENT" ]; then
            success "Cleanup successful - disk usage below threshold"
        else
            error "Cleanup insufficient - disk usage still high"
        fi
    else
        success "Disk space usage is within acceptable limits"
    fi
}

# Continuous monitoring mode
monitor_continuously() {
    local interval_minutes=${1:-60}
    log "Starting continuous monitoring (checking every ${interval_minutes} minutes)"
    
    while true; do
        monitor_disk_space
        log "Sleeping for ${interval_minutes} minutes..."
        sleep $((interval_minutes * 60))
    done
}

# Main script logic
main() {
    case "${1:-check}" in
        "check")
            monitor_disk_space
            ;;
        "monitor")
            local interval=${2:-60}
            monitor_continuously "$interval"
            ;;
        "config")
            echo "Disk Space Monitoring Configuration:"
            echo "  Disk threshold: ${DISK_THRESHOLD_PERCENT}%"
            echo "  Docker threshold: ${DOCKER_THRESHOLD_GB}GB"
            echo "  Log threshold: ${LOG_THRESHOLD_GB}GB"
            echo "  Model threshold: ${MODEL_THRESHOLD_GB}GB"
            echo "  Alert email: ${ALERT_EMAIL:-'Not configured'}"
            ;;
        *)
            echo "Usage: $0 [check|monitor|config] [interval_minutes]"
            echo "  check: Run one-time disk space check"
            echo "  monitor: Run continuous monitoring (default: 60 minutes)"
            echo "  config: Show current configuration"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 