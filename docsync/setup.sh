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

cat <<EOF

Done. The key is in the GitHub secret and the local copy is shredded.

Two steps remain that only you can do:

  1. Share each doc in docsync.yml with this address, as Editor:

         $EMAIL

     (Share -> paste -> Editor -> uncheck "Notify people".)

  2. Initialise each binding — this REPLACES the doc with the repo's content,
     so copy anything you want to keep first:

         export GOOGLE_SERVICE_ACCOUNT_KEY="\$(gcloud iam service-accounts keys create /dev/stdout --iam-account=$EMAIL)"
         python3 -m docsync.sync push --id budget-primer
         git add docsync/.state && git commit -m "docsync: initialise" && git push

After that the workflow runs every 15 minutes on its own.
EOF
