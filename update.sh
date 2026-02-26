#!/usr/bin/env bash
set -e

APP_DIR="/opt/enpi"

if [ -d "$APP_DIR/.git" ]; then
  echo "[enpi-update] pulling latest changes..."
  git -C "$APP_DIR" pull --ff-only || echo "[enpi-update] git pull failed, continuing with existing code."
else
  echo "[enpi-update] no git repo found at $APP_DIR"
fi