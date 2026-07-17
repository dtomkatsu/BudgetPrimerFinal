"""Read a Google Doc, with or without credentials.

Unauthenticated: the Markdown export endpoint serves any link-shared doc, which
is what `make pull-doc` uses from a laptop — no secrets to hold.

Authenticated: the same endpoint with a service-account bearer token, which is
what CI uses. It also reaches docs that are shared only with the service
account, and is the only way to read modifiedTime for conflict detection.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

SCOPES = ("https://www.googleapis.com/auth/documents",
          "https://www.googleapis.com/auth/drive")


class FetchError(RuntimeError):
    pass


def export_url(doc_id: str) -> str:
    return f"https://docs.google.com/document/d/{doc_id}/export?format=markdown"


def _get(url: str, token: str | None = None, accept_html: bool = False) -> bytes:
    headers = {"User-Agent": "docsync"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            if not accept_html and "text/html" in r.headers.get("Content-Type", ""):
                raise FetchError(
                    "Google returned a sign-in page, not Markdown. Either share "
                    "the doc as 'Anyone with the link -> Viewer', or share it with "
                    "the service account and run with credentials.")
            return r.read()
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} fetching {url}") from e


def fetch_markdown(doc_id: str, token: str | None = None) -> str:
    return _get(export_url(doc_id), token).decode("utf-8")


def fetch_modified_time(doc_id: str, token: str) -> str:
    """Drive's modifiedTime (RFC-3339). Requires credentials — this is the
    signal that tells a push whether the doc changed since the last sync."""
    url = ("https://www.googleapis.com/drive/v3/files/"
           f"{doc_id}?fields=modifiedTime")
    return json.loads(_get(url, token))["modifiedTime"]


def replace_doc(doc_id: str, markdown: str, token: str) -> None:
    """Overwrite the doc body by importing Markdown — Drive converts headings,
    bold, links and lists into native Docs formatting, and its exporter turns
    them back, which is what makes the round-trip work at all."""
    url = ("https://www.googleapis.com/upload/drive/v3/files/"
           f"{doc_id}?uploadType=media")
    req = urllib.request.Request(
        url, data=markdown.encode("utf-8"), method="PATCH",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "text/markdown"})
    try:
        urllib.request.urlopen(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} replacing doc {doc_id}: "
                         f"{e.read().decode('utf-8', 'replace')[:400]}") from e


def access_token(service_account_json: str) -> str:
    """Mint an access token from a service-account key (JWT bearer grant)."""
    try:
        from google.oauth2 import service_account            # noqa: PLC0415
        from google.auth.transport.requests import Request   # noqa: PLC0415
    except ImportError as e:
        raise FetchError(
            "google-auth is required for authenticated access:\n"
            "  pip install google-auth") from e

    info = json.loads(service_account_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=list(SCOPES))
    creds.refresh(Request())
    return creds.token
