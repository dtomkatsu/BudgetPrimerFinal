CHROME := /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
PROFILE := $(shell mktemp -d /tmp/primer-pdf.XXXXXX)

all: data html pdf embed

validate:
	python3 tools/build_data.py --validate
	python3 tools/pull_doc.py --check

# Prose lives in the Google Doc; content.md is the committed snapshot the build
# reads. `pull-doc` refreshes it (refuses to write if the doc is malformed), so
# every prose change lands as a reviewable git diff before it ships.
pull-doc:
	python3 tools/pull_doc.py

doc-diff:
	python3 tools/pull_doc.py --diff

data:
	python3 tools/build_data.py

html: data
	python3 tools/render_report.py

pdf: html
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

.PHONY: all validate data html pdf embed preview pull-doc doc-diff
