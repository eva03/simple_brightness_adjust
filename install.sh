#!/bin/bash
#
# Installation script for brightness-control utility
# Sets up monitor brightness control for Pop!_OS 22.04 / GNOME
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Install paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
LIB_DIR="$HOME/.local/lib/brightness-control"

echo -e "${BLUE}=== Brightness Control Installation ===${NC}\n"

# Don't run as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script with sudo${NC}"
    echo "The script will prompt for sudo only when needed."
    exit 1
fi

# --- Prerequisites ---
echo "Checking prerequisites..."

if ! command -v ddcutil &> /dev/null; then
    echo -e "${RED}Error: ddcutil not found${NC}"
    echo "Install it with: sudo apt install ddcutil"
    exit 1
fi
echo -e "${GREEN}✓${NC} ddcutil found"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)'; then
    PY_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo -e "${RED}Error: Python 3.7+ required (found $PY_VER)${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $(python3 --version | cut -d' ' -f2) found"

if [ -z "$XDG_CURRENT_DESKTOP" ] || ! echo "$XDG_CURRENT_DESKTOP" | grep -qi gnome; then
    echo -e "${YELLOW}Warning: GNOME desktop not detected${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r; echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
else
    echo -e "${GREEN}✓${NC} GNOME desktop detected"
fi

echo ""

# --- Number of monitors ---
read -p "How many monitors do you want to set up shortcuts for? [2] " MONITOR_COUNT_NUM
MONITOR_COUNT_NUM=${MONITOR_COUNT_NUM:-2}

if ! [[ "$MONITOR_COUNT_NUM" =~ ^[1-4]$ ]]; then
    echo -e "${RED}Error: Enter a number between 1 and 4${NC}"
    exit 1
fi
echo ""

# --- Confirm ---
echo "Keyboard shortcuts that will be created:"
for i in $(seq 1 "$MONITOR_COUNT_NUM"); do
    echo "  Monitor $i: Super+Shift+F$((i * 2 - 1)) (down), Super+Shift+F$((i * 2)) (up)"
done
echo ""
read -p "Continue with installation? (Y/n) " -n 1 -r; echo
[[ $REPLY =~ ^[Nn]$ ]] && { echo "Installation cancelled."; exit 0; }

# --- Install files ---
echo ""
echo "Installing files..."

mkdir -p "$BIN_DIR" "$LIB_DIR"

cp "$SCRIPT_DIR/bin/brightness-control" "$BIN_DIR/"
chmod +x "$BIN_DIR/brightness-control"
echo -e "${GREEN}✓${NC} Installed brightness-control → $BIN_DIR"

cp "$SCRIPT_DIR/lib/"*.py "$LIB_DIR/"
echo -e "${GREEN}✓${NC} Installed library → $LIB_DIR"

# --- i2c group ---
if ! groups | grep -qw i2c; then
    echo ""
    echo -e "${YELLOW}Adding $USER to i2c group (requires sudo)...${NC}"
    sudo usermod -aG i2c "$USER"
    echo -e "${GREEN}✓${NC} Added $USER to i2c group"
    NEED_LOGOUT=1
else
    echo -e "${GREEN}✓${NC} User already in i2c group"
    NEED_LOGOUT=0
fi

# --- GNOME keyboard shortcuts ---
echo ""
echo "Setting up GNOME keyboard shortcuts..."

# Read current list (strip @as prefix and whitespace)
RAW=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
EXISTING=$(echo "$RAW" | sed "s/@as //g; s/\[//g; s/\]//g; s/'//g" | tr ',' '\n' | sed 's/[[:space:]]//g' | grep -v '^$')

# Build new list, removing any existing brightness-control entries first
NEW_LIST=""
while IFS= read -r path; do
    [[ "$path" == *brightness-mon* ]] && continue
    [[ -n "$NEW_LIST" ]] && NEW_LIST+=",'$path'" || NEW_LIST="'$path'"
done <<< "$EXISTING"

add_keybinding() {
    local id="$1" name="$2" command="$3" binding="$4"
    local path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/$id/"
    [[ -n "$NEW_LIST" ]] && NEW_LIST+=",'$path'" || NEW_LIST="'$path'"
    gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$path" name    "$name"
    gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$path" command "$command"
    gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$path" binding "$binding"
}

for i in $(seq 1 "$MONITOR_COUNT_NUM"); do
    add_keybinding "brightness-mon${i}-up"   "Brightness: Monitor $i Up"   "$BIN_DIR/brightness-control -m $i -a up"   "<Super><Shift>F$((i * 2))"
    add_keybinding "brightness-mon${i}-down" "Brightness: Monitor $i Down" "$BIN_DIR/brightness-control -m $i -a down" "<Super><Shift>F$((i * 2 - 1))"
    echo -e "${GREEN}✓${NC} Monitor $i: Super+Shift+F$((i * 2 - 1)) / F$((i * 2))"
done

gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "[$NEW_LIST]"

# --- Done ---
echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Scripts : $BIN_DIR/brightness-control"
echo "Library : $LIB_DIR"
echo ""

if [ "$NEED_LOGOUT" -eq 1 ]; then
    echo -e "${YELLOW}IMPORTANT: Log out and back in for i2c group permissions to take effect.${NC}"
    echo ""
fi

echo "Test with:"
echo "  brightness-control -m 1 -a up"
echo "  brightness-control --detect    # show current slot assignments"
echo ""
