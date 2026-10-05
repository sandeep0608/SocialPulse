# Social Pulse — common tasks
.PHONY: help sample build demo clean

help:
	@echo "make sample   # generate synthetic sample CSVs into data/"
	@echo "make build    # build output/dashboard.html from the sample data"
	@echo "make demo     # sample + build + refresh the browsable docs/dashboard.html"
	@echo "make clean    # remove generated output"

sample:
	python make_sample_data.py

build:
	python generate_dashboard.py --posts data/sample_posts.csv --email "data/sample_broadcasts.csv:Nimbus Weekly"

demo: sample build
	cp output/dashboard.html docs/dashboard.html
	@echo "docs/dashboard.html refreshed"

clean:
	rm -f output/*.html output/*.json
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
