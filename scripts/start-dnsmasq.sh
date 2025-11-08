#!/bin/bash
# Script to start dnsmasq for FujiDrop DNS hijacking
# This makes api.frame.io resolve to your Mac's IP address so the camera connects to your server

CONFIG_FILE="/tmp/dnsmasq-fujidrop.conf"
DNSMASQ_BIN="/opt/homebrew/sbin/dnsmasq"

# Check if dnsmasq is already running
if pgrep -f "dnsmasq.*fujidrop" > /dev/null; then
    echo "dnsmasq is already running. Stopping it first..."
    sudo pkill -f "dnsmasq.*fujidrop"
    sleep 1
fi

# Check if port 53 is in use and stop system DNS resolver if needed
if lsof -i :53 > /dev/null 2>&1 || sudo lsof -i :53 > /dev/null 2>&1; then
    echo "Port 53 is in use. Checking if it's the system DNS resolver..."
    
    # Check if mDNSResponder is running
    if pgrep -x mDNSResponder > /dev/null; then
        echo "Stopping system DNS resolver (mDNSResponder) temporarily..."
        echo "Note: This will disable system DNS until you restart it."
        sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.mDNSResponder.plist 2>/dev/null || \
        sudo killall mDNSResponder 2>/dev/null || true
        sleep 2
    fi
fi

# Get Mac's IP address on the network (before creating config)
# Try en0 (usually WiFi) first, then en1 (usually Ethernet), then search all interfaces
MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || \
         ipconfig getifaddr en1 2>/dev/null || \
         ifconfig | grep -A1 "inet 192.168" | grep "inet " | awk '{print $2}' | head -1)

# Validate that we got an IP address
if [ -z "$MAC_IP" ]; then
    echo "Error: Could not determine Mac's IP address"
    echo "Please check your network connection and try again"
    exit 1
fi

# Always recreate config file with current IP
echo "Creating/updating config file with IP: $MAC_IP..."
cat > "$CONFIG_FILE" << EOF
# dnsmasq config for FujiDrop - hijack api.frame.io
# Don't read /etc/resolv.conf
no-resolv

# Use upstream DNS servers
server=8.8.8.8
server=8.8.4.4

# Hijack api.frame.io to point to your server
address=/api.frame.io/$MAC_IP

# Listen on all interfaces so camera can reach it
listen-address=0.0.0.0

# Enable logging to see DNS queries from camera
log-queries
log-facility=/tmp/dnsmasq-fujidrop.log
EOF

echo "Starting dnsmasq with config: $CONFIG_FILE"
echo "Your Mac's IP address: $MAC_IP"
echo ""
echo "Configure your camera's DNS to: $MAC_IP"
echo ""
echo "Press Ctrl+C to stop dnsmasq and restore system DNS"
echo ""

# Trap Ctrl+C to restore system DNS
trap 'echo ""; echo "Restoring system DNS resolver..."; sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.mDNSResponder.plist 2>/dev/null || true; exit' INT TERM

# Start dnsmasq (requires sudo for port 53)
sudo $DNSMASQ_BIN --conf-file="$CONFIG_FILE" --no-daemon

# Restore system DNS when dnsmasq exits
echo ""
echo "Restoring system DNS resolver..."
sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.mDNSResponder.plist 2>/dev/null || true

