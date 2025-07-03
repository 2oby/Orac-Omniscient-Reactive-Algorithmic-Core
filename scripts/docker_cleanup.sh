#!/usr/bin/env bash
set -euo pipefail

# Docker Cleanup Script for ORAC
# Safely removes unused Docker resources while preserving essential data

# Configuration
PRESERVE_IMAGES=("orac-orac:latest")  # Images to preserve
PRESERVE_VOLUMES=("orac_cache" "orac_data" "orac_logs")  # Volumes to preserve
MAX_BUILD_CACHE_GB=20  # Maximum build cache size to keep
DRY_RUN=false

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

# Get Docker disk usage
get_docker_usage() {
    docker system df 2>/dev/null || echo "Docker not available"
}

# Get build cache size in GB
get_build_cache_size() {
    docker system df 2>/dev/null | grep "Build Cache" | awk '{print $4}' | sed 's/GB//' || echo "0"
}

# Check if image should be preserved
should_preserve_image() {
    local image="$1"
    for preserve in "${PRESERVE_IMAGES[@]}"; do
        if [[ "$image" == *"$preserve"* ]]; then
            return 0  # true
        fi
    done
    return 1  # false
}

# Check if volume should be preserved
should_preserve_volume() {
    local volume="$1"
    for preserve in "${PRESERVE_VOLUMES[@]}"; do
        if [[ "$volume" == *"$preserve"* ]]; then
            return 0  # true
        fi
    done
    return 1  # false
}

# Stop containers safely
stop_containers() {
    log "Stopping running containers..."
    
    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN: Would stop containers"
        return
    fi
    
    # Stop all running containers except essential ones
    local running_containers=$(docker ps --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$running_containers" ]; then
        echo "$running_containers" | while read -r container; do
            # Skip essential containers (add more as needed)
            if [[ "$container" != "orac" ]]; then
                log "Stopping container: $container"
                docker stop "$container" 2>/dev/null || warn "Failed to stop $container"
            else
                log "Preserving essential container: $container"
            fi
        done
    fi
}

# Remove stopped containers
remove_stopped_containers() {
    log "Removing stopped containers..."
    
    if [ "$DRY_RUN" = true ]; then
        local stopped_count=$(docker ps -a --filter "status=exited" --format "{{.Names}}" | wc -l)
        log "DRY RUN: Would remove $stopped_count stopped containers"
        return
    fi
    
    docker container prune -f 2>/dev/null || warn "Failed to remove stopped containers"
}

# Remove unused images (preserving essential ones)
remove_unused_images() {
    log "Removing unused images..."
    
    if [ "$DRY_RUN" = true ]; then
        local unused_images=$(docker images --filter "dangling=true" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null || true)
        local count=$(echo "$unused_images" | grep -v "^$" | wc -l)
        log "DRY RUN: Would remove $count dangling images"
        return
    fi
    
    # Remove dangling images first
    docker image prune -f 2>/dev/null || warn "Failed to remove dangling images"
    
    # Remove unused images, but preserve essential ones
    local all_images=$(docker images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null || true)
    if [ -n "$all_images" ]; then
        echo "$all_images" | while read -r image; do
            if [ -n "$image" ] && [ "$image" != "<none>:<none>" ]; then
                if ! should_preserve_image "$image"; then
                    # Check if image is used by any container
                    local used_by=$(docker ps -a --filter "ancestor=$image" --format "{{.Names}}" 2>/dev/null || true)
                    if [ -z "$used_by" ]; then
                        log "Removing unused image: $image"
                        docker rmi "$image" 2>/dev/null || warn "Failed to remove $image"
                    fi
                else
                    log "Preserving essential image: $image"
                fi
            fi
        done
    fi
}

# Remove unused volumes (preserving essential ones)
remove_unused_volumes() {
    log "Removing unused volumes..."
    
    if [ "$DRY_RUN" = true ]; then
        local unused_volumes=$(docker volume ls --filter "dangling=true" --format "{{.Name}}" 2>/dev/null || true)
        local count=$(echo "$unused_volumes" | grep -v "^$" | wc -l)
        log "DRY RUN: Would remove $count unused volumes"
        return
    fi
    
    # Get all volumes
    local all_volumes=$(docker volume ls --format "{{.Name}}" 2>/dev/null || true)
    if [ -n "$all_volumes" ]; then
        echo "$all_volumes" | while read -r volume; do
            if [ -n "$volume" ]; then
                if ! should_preserve_volume "$volume"; then
                    # Check if volume is used by any container
                    local used_by=$(docker ps -a --filter "volume=$volume" --format "{{.Names}}" 2>/dev/null || true)
                    if [ -z "$used_by" ]; then
                        log "Removing unused volume: $volume"
                        docker volume rm "$volume" 2>/dev/null || warn "Failed to remove $volume"
                    fi
                else
                    log "Preserving essential volume: $volume"
                fi
            fi
        done
    fi
}

# Remove unused networks
remove_unused_networks() {
    log "Removing unused networks..."
    
    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN: Would remove unused networks"
        return
    fi
    
    docker network prune -f 2>/dev/null || warn "Failed to remove unused networks"
}

# Clean build cache
clean_build_cache() {
    log "Cleaning build cache..."
    
    local current_size=$(get_build_cache_size)
    log "Current build cache size: ${current_size}GB"
    
    if (( $(echo "$current_size > $MAX_BUILD_CACHE_GB" | bc -l) )); then
        log "Build cache exceeds threshold (${MAX_BUILD_CACHE_GB}GB), cleaning..."
        
        if [ "$DRY_RUN" = true ]; then
            log "DRY RUN: Would clean build cache"
            return
        fi
        
        docker builder prune -a -f 2>/dev/null || warn "Failed to clean build cache"
        
        local new_size=$(get_build_cache_size)
        log "Build cache size after cleanup: ${new_size}GB"
    else
        log "Build cache size is within limits"
    fi
}

# Full system cleanup
full_system_cleanup() {
    log "Performing full system cleanup..."
    
    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN: Would perform full system cleanup"
        return
    fi
    
    # This is more aggressive - use with caution
    docker system prune -a -f --volumes 2>/dev/null || warn "Failed to perform full system cleanup"
}

# Show cleanup summary
show_summary() {
    log "Docker cleanup completed"
    log "Current Docker disk usage:"
    get_docker_usage
}

# Main cleanup function
main_cleanup() {
    local level="${1:-normal}"
    
    log "Starting Docker cleanup (level: $level)"
    log "Preserving images: ${PRESERVE_IMAGES[*]}"
    log "Preserving volumes: ${PRESERVE_VOLUMES[*]}"
    
    # Show initial state
    log "Initial Docker disk usage:"
    get_docker_usage
    
    case "$level" in
        "light")
            log "Light cleanup mode"
            remove_stopped_containers
            remove_unused_networks
            clean_build_cache
            ;;
        "normal")
            log "Normal cleanup mode"
            stop_containers
            remove_stopped_containers
            remove_unused_images
            remove_unused_volumes
            remove_unused_networks
            clean_build_cache
            ;;
        "aggressive")
            log "Aggressive cleanup mode"
            stop_containers
            remove_stopped_containers
            remove_unused_images
            remove_unused_volumes
            remove_unused_networks
            clean_build_cache
            full_system_cleanup
            ;;
        *)
            error "Invalid cleanup level: $level"
            echo "Usage: $0 [light|normal|aggressive] [--dry-run]"
            exit 1
            ;;
    esac
    
    show_summary
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

# Run main cleanup with remaining arguments
main_cleanup "${1:-normal}" 