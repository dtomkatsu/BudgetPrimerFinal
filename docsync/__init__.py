"""Google Doc <-> HTML report sync.

A binding pairs one Google Doc with one file in this repo (see docsync.yml).
The doc is the writing surface; the committed file is what the build reads, so
builds stay reproducible and every prose change lands as a reviewable diff.

Two modes:
  slots    — the doc supplies text into named [[key]] slots (content.py). For
             art-directed reports where code owns layout.
  fragment — the whole doc becomes one HTML block injected between anchor
             comments in a target page (fragment.py). For simple pages.

Nothing is ever written unless it parses and satisfies the report: a doc that
loses a key, or cites a source that does not exist, fails loudly instead.
"""
from .content import Content, ContentError                       # noqa: F401
from .normalise import normalise                                 # noqa: F401
from .registry import Binding, load_registry, RegistryError      # noqa: F401
