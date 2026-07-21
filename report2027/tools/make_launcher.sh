#!/bin/bash
# Build a double-clickable macOS launcher for the live draft editor.
#
# The result is a real .app bundle: launching it starts the local live server
# (report2027/tools/serve.py) if it is not already up, then opens the editor in
# a standalone Chrome "app" window — no tabs, no address bar, its own Dock icon.
# It is the one-icon version of `make -C report2027 live`.
#
#   ./report2027/tools/make_launcher.sh            # -> ~/Applications
#   ./report2027/tools/make_launcher.sh /some/dir  # -> /some/dir
#
# The bundle is a build artifact, not committed. Re-run this after moving the
# repo (the repo path is baked in at build time so the icon works from anywhere).
set -euo pipefail

# The repo is two levels above this script, resolved absolutely so the baked
# path is correct no matter where the build runs from.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT_DIR="${1:-$HOME/Applications}"
APP="$OUT_DIR/Budget Primer Editor.app"
PORT="${PRIMER_PORT:-8010}"

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# --- the launch script: start the server if needed, then open the app window --
cat > "$APP/Contents/MacOS/launch" <<LAUNCH
#!/bin/bash
REPO="$REPO"
PORT="$PORT"
URL="http://localhost:\$PORT/primer/start.html"
CHROME="\${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

cd "\$REPO" || exit 1

# Boot the live server only if nothing is already answering on the port —
# reopening the app while it is already running just focuses the window.
if ! curl -sf "http://localhost:\$PORT/__ping" >/dev/null 2>&1; then
  PRIMER_OPEN=0 nohup python3 report2027/tools/serve.py >/tmp/primer-live.log 2>&1 &
  for _ in \$(seq 1 40); do
    curl -sf "http://localhost:\$PORT/__ping" >/dev/null 2>&1 && break
    sleep 0.25
  done
fi

# A standalone window (--app) so it reads as an app, not a browser tab. Falls
# back to the default browser if Chrome is not where we expect.
if [ -x "\$CHROME" ]; then
  "\$CHROME" --app="\$URL" >/dev/null 2>&1 &
else
  open "\$URL"
fi
LAUNCH
chmod +x "$APP/Contents/MacOS/launch"

# --- Info.plist ---------------------------------------------------------------
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Budget Primer Editor</string>
  <key>CFBundleDisplayName</key><string>Budget Primer Editor</string>
  <key>CFBundleIdentifier</key><string>org.hiappleseed.primereditor</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>LSMinimumSystemVersion</key><string>10.13</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

# --- icon: reuse the editor's own, converted to .icns -------------------------
SRC_PNG="$REPO/docs/primer/icons/icon-512.png"
if [ -f "$SRC_PNG" ]; then
  ICONSET="$(mktemp -d)/icon.iconset"
  mkdir -p "$ICONSET"
  for spec in "16:16x16" "32:16x16@2x" "32:32x32" "64:32x32@2x" \
              "128:128x128" "256:128x128@2x" "256:256x256" "512:256x256@2x" \
              "512:512x512"; do
    px="${spec%%:*}"; name="${spec##*:}"
    sips -z "$px" "$px" "$SRC_PNG" --out "$ICONSET/icon_$name.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns"
  rm -rf "$(dirname "$ICONSET")"
fi

# Make Finder/LaunchServices pick up the new bundle immediately.
touch "$APP"

echo "Built: $APP"
echo "Repo baked in: $REPO  (port $PORT)"
echo "Launch it from Finder, Spotlight, or drag it to the Dock."
