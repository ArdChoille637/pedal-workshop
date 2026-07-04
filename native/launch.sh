#!/bin/bash
# Build (incremental) and launch Pedal Workshop
set -euo pipefail
cd "$(dirname "$0")"

SCHEME="PedalWorkshop-macOS"
PROJECT="PedalWorkshop.xcodeproj"
CONFIG="Debug"

# ── Generate the Xcode project from project.yml if missing ───────────────────
# PedalWorkshop.xcodeproj is gitignored; project.yml is the source of truth.
# A fresh clone has no .xcodeproj, so generate it with XcodeGen.
if [[ ! -d "$PROJECT" ]]; then
  if command -v xcodegen >/dev/null 2>&1; then
    echo "Generating $PROJECT from project.yml…"
    xcodegen generate
  else
    echo "error: $PROJECT is missing and 'xcodegen' is not installed." >&2
    echo "       Install it with:  brew install xcodegen" >&2
    echo "       then re-run ./launch.sh" >&2
    exit 1
  fi
fi

# ── Resolve build product directory (fast — no compilation) ──────────────────
# NB: field-based awk, not /^\s+…/ — macOS BSD awk has no \s escape.
BUILD_DIR=$(xcodebuild \
  -project       "$PROJECT" \
  -scheme        "$SCHEME" \
  -configuration "$CONFIG" \
  -showBuildSettings 2>/dev/null \
  | awk '$1 == "BUILT_PRODUCTS_DIR" { print $3; exit }')

if [[ -z "$BUILD_DIR" ]]; then
  echo "error: Could not resolve build directory." >&2
  echo "       Is Xcode installed? Run: xcodebuild -list" >&2
  exit 1
fi

APP="$BUILD_DIR/Pedal Workshop.app"

# ── Incremental build ─────────────────────────────────────────────────────────
echo "Building $SCHEME…"
LOG=$(mktemp /tmp/pedal-workshop-build.XXXXXX)
trap 'rm -f "$LOG"' EXIT

xcodebuild \
  -project       "$PROJECT" \
  -scheme        "$SCHEME" \
  -configuration "$CONFIG" \
  -destination   "platform=macOS" \
  ONLY_ACTIVE_ARCH=YES \
  build >"$LOG" 2>&1 || true

# Print only meaningful lines (errors, warnings, result)
grep -E "(error:|warning:|BUILD SUCCEEDED|BUILD FAILED)" "$LOG" \
  | grep -v appintentsmetadataprocessor \
  || true

if grep -q "BUILD FAILED" "$LOG"; then
  echo "" >&2
  echo "Build failed. For full output run:" >&2
  echo "  xcodebuild -project $PROJECT -scheme $SCHEME build" >&2
  exit 1
fi

echo "Build succeeded."

# ── Install to /Applications + launch ─────────────────────────────────────────
INSTALLED="/Applications/Pedal Workshop.app"
echo "Installing to $INSTALLED…"
pkill -f "Pedal Workshop" 2>/dev/null || true
sleep 0.3
rm -rf "$INSTALLED"
cp -R "$APP" "$INSTALLED"

echo "Launching Pedal Workshop…"
open "$INSTALLED"
