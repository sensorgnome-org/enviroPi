#!/usr/bin/env bash
set -e

HOME_DIR="/home/gnome"
ENPI_DIR="/opt/sensorgnome/enpi"
SERVICE_USER="gnome"
ENPI_REPO="enpi"
REPO_BRANCH="sensorgnome"

SG_REPO_DIR="$HOME_DIR/sensorgnome-control"
SG_CONTROL_DIR="/opt/sensorgnome/control"

echo "=== enpi Update Script ==="

updates_applied=false
enpi_updated=false
sgcontrol_updated=false

update_repo() {
    local repo_dir="$1"
    local branch="$2"
    updates_applied=false

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

# 1 Update enpi repo
if [ -d "$HOME_DIR/$ENPI_REPO/.git" ]; then
    update_repo "$HOME_DIR/$ENPI_REPO" "$REPO_BRANCH"

    if [ "$updates_applied" = true ]; then
        enpi_updated=true
        echo "Syncing $ENPI_REPO files..."
        OLD_REQ_HASH=$(sha256sum "$ENPI_DIR/requirements.txt" 2>/dev/null | awk '{print $1}')
        sudo rsync -av --delete \
          --exclude-from="$ENPI_DIR/.rsync-exclude" \
          "$HOME_DIR/$ENPI_REPO/" "$ENPI_DIR/"

        sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$ENPI_DIR"
        NEW_REQ_HASH=$(sha256sum "$ENPI_DIR/requirements.txt" 2>/dev/null | awk '{print $1}')

        # Check to see if required packages have changed.
        
        if [ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]; then
          echo "requirements.txt changed — updating Python dependencies"
          sudo -u "$SERVICE_USER" bash <<EOF
            cd "$ENPI_DIR"
            source env/bin/activate
            pip install -r requirements.txt
EOF
        else
          echo "requirements.txt unchanged — skipping pip install"
        fi
    fi
else
    echo "enpi repo not found, skipping."
fi

# 2 Update sg-control repo
if [ -d "$SG_REPO_DIR/.git" ]; then
    update_repo "$SG_REPO_DIR" "enpi"

    if [ "$updates_applied" = true ]; then
        sgcontrol_updated=true
        echo "Updating sg-control files..."
        sudo cp "$SG_REPO_DIR/src/dashboard.js" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/enpi.js" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/fd-config.json" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/main.js" "$SG_CONTROL_DIR/"
        sudo cp "$SG_REPO_DIR/src/motus_up.js" "$SG_CONTROL_DIR/"
    fi
else
    echo "sg-control repo not found, skipping."
fi

# 3 Restart pigpio only if updates happened
if [ "$enpi_updated" = true ]; then
    echo
    echo "Restarting pigpio..."
    sudo systemctl restart pigpiod
fi
if [ "$sgcontrol_updated" = true ]; then
    echo "Restarting sg-control service..."
    sudo systemctl restart sg-control
fi
if [[ "$enpi_updated" = false && "$sgcontrol_updated" = false ]]; then
    echo
    echo "No updates applied. No services restarted."
fi

echo
echo "=== Update complete ==="