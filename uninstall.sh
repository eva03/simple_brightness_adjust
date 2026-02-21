#!/bin/bash
#
# Uninstallation script for brightness-control utility
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BIN_DIR="$HOME/.local/bin"
LIB_DIR="$HOME/.local/lib/brightness-control"

echo -e "${BLUE}=== Brightness Control Uninstallation ===${NC}\n"

# --- Remove GNOME keyboard shortcuts ---
echo "Removing GNOME keyboard shortcuts..."

RAW=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
EXISTING=$(echo "$RAW" | sed "s/@as //g; s/\[//g; s/\]//g; s/'//g" | tr ',' '\n' | sed 's/[[:space:]]//g' | grep -v '^$')

KEEP_LIST=""
while IFS= read -r path; do
    if [[ "$path" == *brightness-mon* ]]; then
        gsettings reset "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$path/" name    2>/dev/null || true
        gsettings reset "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$path/" command 2>/dev/null || true
        gsettings reset "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$path/" binding 2>/dev/null || true
        id=$(echo "$path" | sed 's|.*/||; s|/$||')
        echo -e "${GREEN}✓${NC} Removed shortcut: $id"
    else
        [[ -n "$KEEP_LIST" ]] && KEEP_LIST+=",'$path'" || KEEP_LIST="'$path'"
    fi
done <<< "$EXISTING"

gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "[$KEEP_LIST]"

# --- Remove installed files ---
if [ -f "$BIN_DIR/brightness-control" ]; then
    rm "$BIN_DIR/brightness-control"
    echo -e "${GREEN}✓${NC} Removed $BIN_DIR/brightness-control"
fi

if [ -d "$LIB_DIR" ]; then
    rm -rf "$LIB_DIR"
    echo -e "${GREEN}✓${NC} Removed $LIB_DIR"
fi

# --- Remove cache ---
CACHE_FILE="/tmp/brightness-control-$USER-bus-cache.json"
if [ -f "$CACHE_FILE" ]; then
    rm "$CACHE_FILE"
    echo -e "${GREEN}✓${NC} Removed cache file"
fi

echo ""
echo -e "${GREEN}=== Uninstallation Complete ===${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} i2c group membership was not changed."
echo "To remove: sudo deluser $USER i2c"
echo ""
