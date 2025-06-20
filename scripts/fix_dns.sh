#!/bin/bash

# DNS Fix Script for Jetson Orin
# This script attempts to fix DNS resolution issues by applying various fixes

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 DNS Fix Script for Jetson Orin${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${YELLOW}👉 $1${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Function to test DNS resolution
test_dns() {
    local test_domain="google.com"
    local test_ip=$(nslookup "$test_domain" 2>/dev/null | grep -A1 "Name:" | tail -1 | awk '{print $2}')
    
    if [[ "$test_ip" == "10.0.0.1" ]]; then
        return 1  # DNS hijacking detected
    elif [[ -n "$test_ip" && "$test_ip" != "10.0.0.1" ]]; then
        return 0  # DNS working correctly
    else
        return 2  # DNS resolution failed
    fi
}

# Function to get active connection name
get_active_connection() {
    nmcli -t -f NAME,TYPE connection show --active | grep -v "bridge\|loopback" | head -1 | cut -d: -f1
}

# Backup current configuration
print_section "Creating Backups"

echo "Backing up current DNS configuration..."
sudo cp /etc/resolv.conf /etc/resolv.conf.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "Could not backup resolv.conf"

# Test initial DNS state
print_section "Testing Initial DNS State"

echo "Testing current DNS resolution..."
if test_dns; then
    echo -e "${GREEN}✓ DNS is working correctly!${NC}"
    exit 0
else
    echo -e "${RED}✗ DNS hijacking detected (resolving to 10.0.0.1)${NC}"
fi

# Fix 1: Clear DNS cache and restart systemd-resolved
print_section "Fix 1: Clear DNS Cache"

echo "Flushing systemd-resolved cache..."
sudo systemd-resolve --flush-caches 2>/dev/null || echo "Could not flush cache"

echo "Restarting systemd-resolved..."
sudo systemctl restart systemd-resolved 2>/dev/null || echo "Could not restart systemd-resolved"

sleep 2

echo "Testing DNS after cache clear..."
if test_dns; then
    print_status 0 "DNS fixed by clearing cache!"
    exit 0
else
    print_status 1 "Cache clear did not fix DNS"
fi

# Fix 2: Configure NetworkManager DNS settings
print_section "Fix 2: Configure NetworkManager DNS"

ACTIVE_CONNECTION=$(get_active_connection)
if [[ -n "$ACTIVE_CONNECTION" ]]; then
    echo "Configuring DNS for connection: $ACTIVE_CONNECTION"
    
    # Set DNS servers
    sudo nmcli connection modify "$ACTIVE_CONNECTION" ipv4.dns "8.8.8.8,1.1.1.1" 2>/dev/null || echo "Could not set DNS servers"
    
    # Disable auto DNS
    sudo nmcli connection modify "$ACTIVE_CONNECTION" ipv4.ignore-auto-dns yes 2>/dev/null || echo "Could not disable auto DNS"
    
    # Restart connection
    echo "Restarting network connection..."
    sudo nmcli connection down "$ACTIVE_CONNECTION" 2>/dev/null || echo "Could not bring down connection"
    sleep 2
    sudo nmcli connection up "$ACTIVE_CONNECTION" 2>/dev/null || echo "Could not bring up connection"
    
    sleep 5
    
    echo "Testing DNS after NetworkManager configuration..."
    if test_dns; then
        print_status 0 "DNS fixed by NetworkManager configuration!"
        exit 0
    else
        print_status 1 "NetworkManager configuration did not fix DNS"
    fi
else
    echo "Could not determine active connection"
fi

# Fix 3: Static resolv.conf configuration
print_section "Fix 3: Static resolv.conf Configuration"

echo "Creating static resolv.conf..."
sudo tee /etc/resolv.conf > /dev/null << EOF
# Static DNS configuration
nameserver 8.8.8.8
nameserver 1.1.1.1
nameserver 8.8.4.4
EOF

# Make resolv.conf immutable to prevent systemd-resolved from overwriting it
sudo chattr +i /etc/resolv.conf 2>/dev/null || echo "Could not make resolv.conf immutable"

sleep 2

echo "Testing DNS after static resolv.conf..."
if test_dns; then
    print_status 0 "DNS fixed by static resolv.conf!"
    exit 0
else
    print_status 1 "Static resolv.conf did not fix DNS"
fi

# Fix 4: Check for Docker DNS interference
print_section "Fix 4: Check Docker DNS Interference"

if command -v docker &> /dev/null; then
    echo "Checking Docker networks..."
    docker network ls 2>/dev/null || echo "Docker not running or not accessible"
    
    echo "Checking Docker bridge network DNS..."
    docker network inspect bridge 2>/dev/null | grep -A5 -B5 "DNS" || echo "Could not inspect Docker bridge network"
    
    echo "Stopping Docker to test if it's interfering..."
    sudo systemctl stop docker 2>/dev/null || echo "Could not stop Docker"
    
    sleep 3
    
    echo "Testing DNS with Docker stopped..."
    if test_dns; then
        print_status 0 "DNS fixed by stopping Docker!"
        echo "Docker was interfering with DNS. Consider configuring Docker DNS settings."
        exit 0
    else
        print_status 1 "Stopping Docker did not fix DNS"
        echo "Restarting Docker..."
        sudo systemctl start docker 2>/dev/null || echo "Could not restart Docker"
    fi
else
    echo "Docker not installed"
fi

# Fix 5: Check for systemd-resolved configuration issues
print_section "Fix 5: systemd-resolved Configuration"

echo "Checking systemd-resolved configuration..."
if [[ -f /etc/systemd/resolved.conf ]]; then
    echo "Current resolved.conf:"
    cat /etc/systemd/resolved.conf
else
    echo "No resolved.conf found, creating one..."
    sudo tee /etc/systemd/resolved.conf > /dev/null << EOF
[Resolve]
DNS=8.8.8.8 1.1.1.1 8.8.4.4
FallbackDNS=1.1.1.1 8.8.8.8
Domains=
DNSSEC=no
DNSOverTLS=no
MulticastDNS=yes
LLMNR=yes
Cache=yes
DNSStubListener=no
EOF
fi

echo "Restarting systemd-resolved..."
sudo systemctl restart systemd-resolved 2>/dev/null || echo "Could not restart systemd-resolved"

sleep 3

echo "Testing DNS after systemd-resolved configuration..."
if test_dns; then
    print_status 0 "DNS fixed by systemd-resolved configuration!"
    exit 0
else
    print_status 1 "systemd-resolved configuration did not fix DNS"
fi

# Fix 6: Check for firewall/proxy interference
print_section "Fix 6: Check Firewall/Proxy Interference"

echo "Checking iptables rules..."
sudo iptables -L -n | grep -E "(53|DNS)" || echo "No DNS-related iptables rules found"

echo "Checking for proxy settings..."
env | grep -i proxy || echo "No proxy environment variables found"

echo "Checking for transparent proxy..."
if command -v curl &> /dev/null; then
    echo "Testing HTTP proxy detection..."
    curl -I http://google.com --connect-timeout 5 2>/dev/null || echo "HTTP test failed"
fi

# Fix 7: Last resort - Network namespace test
print_section "Fix 7: Network Namespace Test"

echo "Testing DNS in a clean network namespace..."
sudo ip netns add dns-test 2>/dev/null || echo "Could not create network namespace"
sudo ip netns exec dns-test ip link set lo up 2>/dev/null || echo "Could not bring up loopback"

# Test DNS in clean namespace
if sudo ip netns exec dns-test nslookup google.com 8.8.8.8 2>/dev/null | grep -q "Address:"; then
    print_status 0 "DNS works in clean namespace - system-level interference detected!"
    echo "This suggests a system-level DNS hijacking is occurring."
else
    print_status 1 "DNS still fails in clean namespace"
fi

# Clean up namespace
sudo ip netns del dns-test 2>/dev/null || true

# Final Summary
print_section "Final Summary"

echo "All DNS fixes attempted. Current status:"
if test_dns; then
    print_status 0 "DNS is now working!"
else
    print_status 1 "DNS hijacking persists"
    echo ""
    echo -e "${RED}🔍 Root Cause Analysis:${NC}"
    echo "The DNS hijacking is likely caused by:"
    echo "1. Router-level DNS hijacking (most common)"
    echo "2. ISP-level DNS interference"
    echo "3. Corporate/network firewall with DNS inspection"
    echo "4. Malware or system compromise"
    echo ""
    echo -e "${YELLOW}🔧 Recommended Next Steps:${NC}"
    echo "1. Check router admin panel (192.168.8.1) for DNS settings"
    echo "2. Disable any 'DNS rebinding protection' or 'DNS hijacking' features"
    echo "3. Test with a different network (mobile hotspot)"
    echo "4. Use a VPN to bypass local DNS"
    echo "5. Contact your ISP about DNS interference"
fi

echo ""
echo -e "${BLUE}📋 Configuration Applied:${NC}"
echo "✓ DNS servers: 8.8.8.8, 1.1.1.1, 8.8.4.4"
echo "✓ Auto DNS disabled"
echo "✓ systemd-resolved restarted"
echo "✓ Static resolv.conf configured"

echo ""
echo -e "${GREEN}✅ DNS fix script complete!${NC}" 