#!/bin/bash

# Network Diagnostic Script for Jetson Orin DNS Issues
# This script helps diagnose and potentially fix DNS resolution problems

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Network Diagnostic Script for Jetson Orin${NC}"
echo -e "${BLUE}=============================================${NC}"
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

# 1. Basic Network Information
print_section "Network Interface Information"
echo "Active network interfaces:"
ip addr show | grep -E "^[0-9]+:|inet " | grep -v "127.0.0.1" || true

echo ""
echo "Routing table:"
ip route show || true

# 2. DNS Configuration Check
print_section "DNS Configuration Analysis"

echo "Current resolv.conf:"
cat /etc/resolv.conf 2>/dev/null || echo "resolv.conf not found"

echo ""
echo "systemd-resolved status:"
systemctl is-active systemd-resolved 2>/dev/null || echo "systemd-resolved not running"

echo ""
echo "systemd-resolved configuration:"
systemd-resolve --status 2>/dev/null || echo "systemd-resolve command failed"

# 3. NetworkManager DNS Settings
print_section "NetworkManager DNS Configuration"

echo "NetworkManager connection details:"
for conn in $(nmcli -t -f NAME,TYPE connection show --active | grep -v "bridge\|loopback" | cut -d: -f1); do
    echo "Connection: $conn"
    nmcli connection show "$conn" | grep -E "(ipv4\.dns|ipv4\.ignore-auto-dns)" || echo "  No DNS settings found"
    echo ""
done

# 4. DNS Resolution Tests
print_section "DNS Resolution Tests"

# Test with different DNS servers
echo "Testing DNS resolution with different servers:"

# Test with Google DNS
echo "Testing with Google DNS (8.8.8.8):"
if nslookup google.com 8.8.8.8 2>/dev/null | grep -q "Address:"; then
    print_status 0 "Google DNS (8.8.8.8) works"
else
    print_status 1 "Google DNS (8.8.8.8) failed"
fi

# Test with Cloudflare DNS
echo "Testing with Cloudflare DNS (1.1.1.1):"
if nslookup google.com 1.1.1.1 2>/dev/null | grep -q "Address:"; then
    print_status 0 "Cloudflare DNS (1.1.1.1) works"
else
    print_status 1 "Cloudflare DNS (1.1.1.1) failed"
fi

# Test with router DNS
echo "Testing with router DNS (192.168.8.1):"
if nslookup google.com 192.168.8.1 2>/dev/null | grep -q "Address:"; then
    print_status 0 "Router DNS (192.168.8.1) works"
else
    print_status 1 "Router DNS (192.168.8.1) failed"
fi

# 5. Check for DNS Cache Issues
print_section "DNS Cache Analysis"

echo "systemd-resolved cache:"
systemd-resolve --statistics 2>/dev/null || echo "Could not get systemd-resolved statistics"

echo ""
echo "Checking for DNS cache files:"
find /var/cache -name "*dns*" -o -name "*resolv*" 2>/dev/null || echo "No DNS cache files found"

# 6. Check for DNS Hijacking Software
print_section "DNS Hijacking Detection"

echo "Checking for common DNS hijacking software:"
echo "dnsmasq processes:"
pgrep -f dnsmasq 2>/dev/null || echo "No dnsmasq processes found"

echo ""
echo "systemd-resolved processes:"
pgrep -f systemd-resolved 2>/dev/null || echo "No systemd-resolved processes found"

echo ""
echo "Checking for DNS-related services:"
systemctl list-units --type=service | grep -i dns || echo "No DNS services found"

# 7. Network Connectivity Tests
print_section "Network Connectivity Tests"

echo "Testing basic connectivity:"
echo "Ping to router (192.168.8.1):"
if ping -c 1 192.168.8.1 >/dev/null 2>&1; then
    print_status 0 "Router connectivity OK"
else
    print_status 1 "Router connectivity failed"
fi

echo "Ping to Google DNS (8.8.8.8):"
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    print_status 0 "Internet connectivity OK"
else
    print_status 1 "Internet connectivity failed"
fi

echo "Ping to Google.com (should fail with DNS issue):"
if ping -c 1 google.com >/dev/null 2>&1; then
    print_status 0 "Domain resolution works (unexpected)"
else
    print_status 1 "Domain resolution failed (expected with DNS issue)"
fi

# 8. Potential Solutions
print_section "Potential Solutions"

echo "Based on the analysis, here are potential solutions to try:"

echo ""
echo "1. Force DNS configuration:"
echo "   sudo nmcli connection modify 'YOUR_CONNECTION_NAME' ipv4.dns '8.8.8.8,1.1.1.1'"
echo "   sudo nmcli connection modify 'YOUR_CONNECTION_NAME' ipv4.ignore-auto-dns yes"
echo "   sudo nmcli connection down 'YOUR_CONNECTION_NAME' && sudo nmcli connection up 'YOUR_CONNECTION_NAME'"

echo ""
echo "2. Clear DNS cache:"
echo "   sudo systemd-resolve --flush-caches"
echo "   sudo systemctl restart systemd-resolved"

echo ""
echo "3. Check for DNS hijacking in router settings:"
echo "   - Access router admin panel (192.168.8.1)"
echo "   - Check DNS settings and disable any DNS hijacking features"
echo "   - Look for 'DNS rebinding protection' or similar settings"

echo ""
echo "4. Test with static DNS in resolv.conf:"
echo "   sudo cp /etc/resolv.conf /etc/resolv.conf.backup"
echo "   echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf"
echo "   echo 'nameserver 1.1.1.1' | sudo tee -a /etc/resolv.conf"

echo ""
echo "5. Check for Docker DNS interference:"
echo "   docker network ls"
echo "   docker network inspect bridge"

# 9. Generate Summary Report
print_section "Summary Report"

echo "Network Diagnostic Summary:"
echo "=========================="

# Determine the likely cause
if systemctl is-active systemd-resolved >/dev/null 2>&1; then
    echo "✓ systemd-resolved is running"
else
    echo "✗ systemd-resolved is not running"
fi

if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo "✓ Internet connectivity works"
else
    echo "✗ Internet connectivity failed"
fi

if nslookup google.com 8.8.8.8 >/dev/null 2>&1; then
    echo "✓ External DNS servers work"
else
    echo "✗ External DNS servers failed"
fi

echo ""
echo "Most likely causes:"
echo "1. Router DNS hijacking (most common)"
echo "2. systemd-resolved configuration issue"
echo "3. NetworkManager DNS override"
echo "4. Docker DNS interference"
echo "5. Firewall/proxy DNS interception"

echo ""
echo -e "${BLUE}🔧 Next Steps:${NC}"
echo "1. Try the DNS configuration commands above"
echo "2. Check router settings for DNS hijacking"
echo "3. Test with a different network if possible"
echo "4. Consider using a VPN to bypass local DNS"

echo ""
echo -e "${GREEN}✅ Diagnostic complete!${NC}" 