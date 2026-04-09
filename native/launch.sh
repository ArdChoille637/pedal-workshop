#!/bin/bash
# Build (incremental) and launch Pedal Workshop
set -e
cd "$(dirname "$0")"

echo "Building..."
xcodebuild \
  -project PedalWorkshop.xcodeproj \
  -scheme PedalWorkshop-macOS \
  -configuration Debug \
  -destination 'platform=macOS' \
  build \
  ONLY_ACTIVE_ARCH=YES \
  | grep -E "error:|warning:|BUILD SUCCEEDED|BUILD FAILED" \
  | grep -v appintentsmetadataprocessor

APP=$(xcodebuild \
  -project PedalWorkshop.xcodeproj \
  -scheme PedalWorkshop-macOS \
  -configuration Debug \
  -showBuildSettings 2>/dev/null \
  | grep BUILT_PRODUCTS_DIR \
  | head -1 \
  | awk '{print $3}')

echo "Launching $APP/Pedal Workshop.app"
pkill -f "Pedal Workshop" 2>/dev/null || true
sleep 0.5
open "$APP/Pedal Workshop.app"
