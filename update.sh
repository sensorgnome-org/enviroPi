#!/usr/bin/env bash
set -e

APP_DIR="/opt/enviroPi"

if [ -d "$APP_DIR/.git" ]; then
  echo "enviroPi: pulling latest changes..."
  git -C "$APP_DIR" pull --ff-only || echo "enviroPi: git pull failed, continuing with existing code."
else
  echo "enviroPi: no git repo found at $APP_DIR"
fi