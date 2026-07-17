CHROME := /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
PROFILE := $(shell mktemp -d /tmp/primer-pdf.XXXXXX)

all: data html pdf embed

validate:
	python3 tools/build_data.py --validate
	cd .. && python3 docsync/test_docsync.py
	cd .. && python3 -m docsync.sync check --id budget-primer

# Prose lives in the Google Doc; content.md is the committed snapshot the build
# reads. `pull-doc` refreshes it (refuses to write if the doc is malformed), so
# every prose change lands as a reviewable git diff before it ships.
pull-doc:
	cd .. && python3 -m docsync.sync pull --id budget-primer

doc-diff:
	cd .. && python3 -m docsync.sync check --id budget-primer --diff

doc-status:
	cd .. && python3 -m docsync.sync status --id budget-primer

# The draft editor runs this report's own renderer in the browser. docsync
# stages it — and everything it reads — next to the published page, driven by
# the editor: block in docsync.yml. Nothing about the editor is primer-specific,
# so there is nothing to configure here.
editor: html
	cd .. && python3 -m docsync.stage --id budget-primer --repo dtomkatsu/BudgetPrimerFinal

data:
	python3 tools/build_data.py

html: data
	python3 tools/render_report.py

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

.PHONY: editor doc-status all validate data html pdf embed preview pull-doc doc-diff
