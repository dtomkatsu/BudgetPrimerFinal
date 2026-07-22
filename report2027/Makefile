CHROME := /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
PROFILE := $(shell mktemp -d /tmp/primer-pdf.XXXXXX)

all: data html pdf embed

validate:
	python3 tools/build_data.py --validate
	cd .. && python3 docsync/test_docsync.py
	python3 tools/test_render.py

# The draft editor runs this report's own renderer in the browser. docsync
# stages it — and everything it reads — next to the published page, driven by
# the editor: block in docsync.yml. Nothing about the editor is primer-specific,
# so there is nothing to configure here.
editor: render
	cd .. && python3 -m docsync.stage --id budget-primer --repo dtomkatsu/BudgetPrimerFinal

# Publish the built report + editor into docs/, which GitHub Pages serves. This
# is the ONE build command — the local live server, the save endpoint, and CI
# all run it, so the deployed page is always exactly what a build here produces.
pub: editor
	cp web/index.html ../docs/primer/
	cp web/primer.css ../docs/primer/
	mkdir -p ../docs/primer/assets && cp -R web/assets/. ../docs/primer/assets/

data:
	python3 tools/build_data.py

# Rendering and rebuilding the data are different jobs. build_data.py parses
# source PDFs and needs PyMuPDF; the numbers it produces are committed and do
# not change because someone edited a sentence. Keeping `render` free of it lets
# CI regenerate the report from an edit without installing a PDF toolchain to
# recompute figures that did not move.
render:
	python3 tools/render_report.py

html: data render

pdf: html
	@mkdir -p dist
	"$(CHROME)" --headless=new --disable-gpu --no-sandbox --no-first-run \
	  --user-data-dir=$(PROFILE) --virtual-time-budget=12000 \
	  --no-pdf-header-footer \
	  --print-to-pdf="$(CURDIR)/dist/Budget-Primer-FY2026-27.pdf" \
	  "file://$(CURDIR)/web/index.html"
	rm -rf $(PROFILE)

embed: html
	python3 tools/bundle_embed.py $(ASSET_BASE)

preview: html
	open web/index.html

# The local live-editing loop: serve docs/, rebuild on every change to the
# source (yours or Claude's), reload the browser in about a second, and push to
# the cloud when you press Save. See tools/serve.py.
live:
	python3 tools/serve.py

.PHONY: render editor pub live all validate data html pdf embed preview
