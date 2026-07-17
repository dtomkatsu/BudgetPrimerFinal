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

# The draft editor runs the real renderer in the browser. Serving its code
# from raw.githubusercontent meant the CDN could hand out a stale renderer for
# minutes after a push — a silently wrong page that looked fine. Copy what it
# needs next to the page instead: same origin, deployed atomically with it.
E := ../docs/primer/engine
editor: html
	@mkdir -p $(E)/docsync $(E)/report2027/tools $(E)/report2027/data $(E)/report2027/manual
	cp ../docsync/content.py ../docsync/normalise.py $(E)/docsync/
	cp tools/render_report.py $(E)/report2027/tools/
	cp content.md layout.json $(E)/report2027/
	cp data/report_data.json $(E)/report2027/data/
	cp manual/obligated_costs.json $(E)/report2027/manual/

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

.PHONY: editor doc-status all validate data html pdf embed preview pull-doc doc-diff
