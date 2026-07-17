#!/usr/bin/env bash
# One-time credential setup for docsync. See SETUP.md for what this does and
# why. Idempotent: safe to re-run.
#
#   ./docsync/setup.sh [project-id]
#
# Leaves two things for you to do by hand afterwards, because neither can be
# scripted: sharing each bound doc with the service account, and running the
# first `push` to initialise.
set -euo pipefail

PROJECT="${1:-docsync-$(whoami | tr -cd 'a-z0-9')}"
SA="docsync"
KEY="$(mktemp -t docsync-key-XXXXXX.json)"
trap 'rm -f "$KEY"' EXIT

for cmd in gcloud gh; do
  command -v "$cmd" >/dev/null || { echo "need $cmd on PATH"; exit 1; }
done
gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q . \
  || { echo "run: gcloud auth login"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "run: gh auth login"; exit 1; }

echo "==> project: $PROJECT"
gcloud projects describe "$PROJECT" >/dev/null 2>&1 \
  || gcloud projects create "$PROJECT"
gcloud config set project "$PROJECT" >/dev/null

echo "==> enabling Docs + Drive APIs"
gcloud services enable docs.googleapis.com drive.googleapis.com

echo "==> service account: $SA"
EMAIL="$SA@$PROJECT.iam.gserviceaccount.com"
gcloud iam service-accounts describe "$EMAIL" >/dev/null 2>&1 \
  || gcloud iam service-accounts create "$SA" --display-name="docsync"

# No IAM roles: the account reaches a doc only when a human shares it, which is
# the whole point — its blast radius is exactly the docs you name.
echo "==> minting a key and storing it as a GitHub secret"
gcloud iam service-accounts keys create "$KEY" --iam-account="$EMAIL"
gh secret set GOOGLE_SERVICE_ACCOUNT_KEY < "$KEY"

echo "==> creating a Drive folder and sharing it with you"
# One folder shared with the service account once is what removes per-doc
# sharing forever: every doc created inside it is reachable already.
TOKEN="$(gcloud auth print-access-token --impersonate-service-account="$EMAIL" 2>/dev/null || true)"
FOLDER=""
if [ -n "$TOKEN" ]; then
  FOLDER=$(curl -sS -X POST "https://www.googleapis.com/drive/v3/files?fields=id" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"name":"docsync","mimeType":"application/vnd.google-apps.folder"}' \
    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))')
fi
ME="$(git config user.email || true)"
if [ -n "$FOLDER" ] && [ -n "$ME" ]; then
  curl -sS -X POST \
    "https://www.googleapis.com/drive/v3/files/$FOLDER/permissions?sendNotificationEmail=false" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"type\":\"user\",\"role\":\"writer\",\"emailAddress\":\"$ME\"}" >/dev/null
  echo "    folder $FOLDER shared with $ME"
fi

cat <<EOF

Done. The key is in the GitHub secret; the local copy is shredded.

  service account:  $EMAIL
EOF

if [ -n "$FOLDER" ]; then
  cat <<EOF
  docs folder:      https://drive.google.com/drive/folders/$FOLDER

Add this to docsync.yml, then every new doc is one command:

  folder: "$FOLDER"

  python3 -m docsync.bind <id> --title "..." --mode fragment --target <page.html>

Check anything with:  python3 -m docsync.doctor
EOF
else
  cat <<EOF

Could not create the docs folder automatically (impersonation unavailable).
Do it once by hand instead:

  1. Make a folder in your Drive named "docsync".
  2. Share it with $EMAIL as Editor.
  3. Put its id (from the URL) in docsync.yml as: folder: "<id>"

Then check with:  python3 -m docsync.doctor
EOF
fi

cat <<EOF

For a doc that already exists, share it with $EMAIL as Editor, then:

  python3 -m docsync.bind <id> --doc <url>

EOF
