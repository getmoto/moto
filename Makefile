SHELL := /bin/bash

ifeq ($(TEST_SERVER_MODE), true)
	# exclude test_iot and test_iotdata for now
	# because authentication of iot is very complicated
	TEST_EXCLUDE :=  --exclude='test_iot.*'
else
	TEST_EXCLUDE :=
endif

init:
	@python setup.py develop
	@pip install -r requirements.txt

lint:
	flake8 moto

test: lint
	rm -f .coverage
	rm -rf cover
	@nosetests -sv --with-coverage --cover-html ./tests/ $(TEST_EXCLUDE)
test_server:
	@TEST_SERVER_MODE=true nosetests -sv --with-coverage --cover-html ./tests/

aws_managed_policies:
	scripts/update_managed_policies.py

upload_pypi_artifact:
	python setup.py sdist bdist_wheel upload

push_dockerhub_image:
	docker build -t motoserver/moto .
	docker push motoserver/moto

tag_github_release:
	git tag `python setup.py --version`
	git push origin `python setup.py --version`

publish: upload_pypi_artifact \
	tag_github_release \
	push_dockerhub_image

implementation_coverage:
	./scripts/implementation_coverage.py
	git commit IMPLEMENTATION_COVERAGE.md -m "Updating implementation coverage" || true

scaffold:
	@pip install -r requirements-dev.txt > /dev/null
	exec python scripts/scaffold.py

VERSION := $(shell python ./setup.py --version 2>&1)
RELEASE_TAG := v$(VERSION)
PREV_VERSION := $(shell git describe --match='v*' 2>&1 | sed -e s'/\(v[0-9.]*\).*/\1/')

#: release - Tag and push to PyPI.
.PHONY: release
release:
	@echo ""

	@echo "Performing pre-release checks for version $(VERSION)"

	@echo -n "Looking for an existing tag $(RELEASE_TAG)... "
	@if git tag -l $(RELEASE_TAG) | grep $(RELEASE_TAG); then \
	    echo ""; \
	    echo "Error: A release tag $(RELEASE_TAG) already exists."; \
	    echo "  To make a new release, please increment the version"; \
	    echo "  number in setup.py, (use semantic versioning).";\
	    echo ""; \
	    false; \
	fi
	@echo "None found. Good"

	@echo -n "Looking for release notes for $(VERSION)... "
	@if ! grep -q '^$(VERSION) ' CHANGES; then \
	    echo "None found. Bad"; \
	    echo ""; \
	    echo "Error: No release notes found for version $(VERSION)"; \
	    echo ""; \
	    echo "  Please look through completed Trello cards and recent"; \
	    echo "  commits, then summarize changes in the file"; \
	    echo "  CHANGES"; \
	    echo ""; \
	    echo "  The following output may prove useful:"; \
	    echo ""; \
	    echo "  $$ git log $(PREV_VERSION).."; \
	    echo ""; \
	    git --no-pager log $(PREV_VERSION)..; \
	    false; \
	fi
	@echo "Found them. Good"

	@echo -n "Checking for locally-modified files... "
	@mods=$$(git ls-files -m); if [ "$${mods}" != "" ]; then \
	    echo "Found some. Bad"; \
	    echo ""; \
	    echo "Error: The following files have modifications."; \
	    echo "  Please commit the desired changes to git before"; \
	    echo "  attempting a release."; \
	    echo ""; \
	    echo "$$mods"; \
	    echo ""; \
	    false; \
	fi
	@echo "None found. Good"

	@echo ""
	@echo "Preparing to package and release version $(VERSION)"
	@echo "to the Nimbis private repository. You have 10 seconds to abort."
	@echo ""
	@for cnt in $$(seq 10 -1 1); do echo -n "$$cnt... "; sleep 1; done
	@echo "0"

	@echo "python setup.py sdist upload -r nimbis"
	@if ! python setup.py sdist upload -r nimbis; then \
	    echo ""; \
	    echo "Error: Failed to upload new release."; \
	    echo "  Please resolve any error messages above, and then"; \
	    echo "  try again."; \
	    false; \
	fi

	@echo ""
	@echo "Successfully released a package with version $(VERSION)"

	@if ! git tag -s -m "Release $(VERSION)" $(RELEASE_TAG); then \
	    echo ""; \
	    echo "Error: Packaged release has been uploaded, but failed to"; \
	    echo "  create a tag. Please create and push a $(RELEASE_TAG)"; \
	    echo "  tag manually now"; \
	    false; \
        fi

	@if ! git push origin $(RELEASE_TAG); then \
	    echo ""; \
	    echo "Error: Packaged release has been uploaded and tagged."; \
	    echo "  But an error occurred while pushing the tag. Please"; \
	    echo "  manually push the $(RELEASE_TAG) tag now"; \
	    false; \
	fi
