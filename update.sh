#!/usr/bin/env bash
set -e

HOME_DIR="/home/gnome"
ENPI_DIR="/opt/sensorgnome/enpi"
SERVICE_USER="gnome"
REPO_BRANCH="sensorgnome"

SG_REPO_DIR="$HOME_DIR/sensorgnome-control-enpi"
SG_CONTROL_DIR="/opt/sensorgnome/control"

echo "=== enviroPi Update Script ==="

updates_applied=false

update_repo() {
    local repo_dir="$1"
    local branch="$2"

    echo
    echo "Checking repo: $repo_dir"

    cd "$repo_dir"

    git fetch origin

    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" = "$REMOTE" ]; then
        echo "No updates available."
        return 0
    fi

    echo "Updates found. Pulling changes..."
    git pull --ff-only origin "$branch"
    updates_applied=true
}

# 1 Update enviroPi repo
if [ -d "$HOME_DIR/enviroPi/.git" ]; then
    update_repo "$HOME_DIR/enviroPi" "$REPO_BRANCH"

    if [ "$updates_applied" = true ]; then
        echo "Syncing enviroPi files..."
        sudo rsync -av --delete "$HOME_DIR/enviroPi/" "$ENPI_DIR/"
        sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$ENPI_DIR"
    fi
else
    echo "enviroPi repo not found, skipping."
fi

# 2 Update sg-control repo
if [ -d "$SG_REPO_DIR/.git" ]; then
    update_repo "$SG_REPO_DIR" "enpi"

    if [ "$updates_applied" = true ]; then
        echo "Updating sg-control files..."
        sudo cp "$SG_REPO_DIR/src/dashboard.js" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/enpi.js" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/fd-config.json" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/main.js" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/motus_up.js" "$SG_CONTROL_DIR/"

        echo "Restarting sg-control service..."
        sudo systemctl restart sg-control
    fi
else
    echo "sg-control repo not found, skipping."
fi

# 3 Restart pigpio only if updates happened
if [ "$updates_applied" = true ]; then
    echo
    echo "Restarting pigpio..."
    sudo systemctl restart pigpiod
else
    echo
    echo "No updates applied. No services restarted."
fi

echo
echo "=== Update complete ==="