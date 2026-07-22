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

# Finder launches apps with a bare-bones PATH (/usr/bin:/bin:...), where
# python3 is Apple's system Python — no pyyaml, so the build fails inside the
# app while working fine in a terminal. Resolve the developer's python3 NOW,
# at build time in a real shell, and bake the absolute path in.
PYTHON="$(command -v python3)"

# --- the launch script: start the server if needed, then open the app window --
cat > "$APP/Contents/MacOS/launch" <<LAUNCH
#!/bin/bash
REPO="$REPO"
PORT="$PORT"
PYTHON="$PYTHON"
URL="http://localhost:\$PORT/primer/start.html"

cd "\$REPO" || exit 1

# The app OWNS the server. A server on this port that the app did not start
# (a leftover from a Claude session, a forgotten terminal) may be running in
# a context that cannot reach the keychain — its Push would fail — so it is
# replaced, not reused. Reopening the app while its own server runs just
# focuses the window. Ownership is a pidfile written at boot.
PIDFILE="/tmp/primer-live.pid"
up() { curl -sf "http://localhost:\$PORT/__ping" >/dev/null 2>&1; }
mine() { [ -f "\$PIDFILE" ] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null \
  && lsof -nP -iTCP:\$PORT -sTCP:LISTEN -t 2>/dev/null | grep -qx "\$(cat "\$PIDFILE")"; }
if up && ! mine; then
  lsof -nP -iTCP:\$PORT -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null
  sleep 1
fi
if ! up; then
  PRIMER_OPEN=0 nohup "\$PYTHON" -u report2027/tools/serve.py >/tmp/primer-live.log 2>&1 &
  echo \$! > "\$PIDFILE"
  for _ in \$(seq 1 40); do
    up && break
    sleep 0.25
  done
fi

# A standalone window (--app) so it reads as an app, not a browser tab — via
# \`open\`, which hands off to the running Chrome and survives this script
# exiting. Invoking the Chrome binary directly and backgrounding it did NOT:
# the handoff stub died with the script and no window ever appeared. Falls
# back to the default browser if Chrome isn't installed.
if [ -d "/Applications/Google Chrome.app" ]; then
  open -na "Google Chrome" --args --app="\$URL"
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
