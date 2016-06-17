PACKAGE = headphones

.PHONY: check install_deps install_dev_deps

check:
	pep8 $(PACKAGE)
	pyflakes $(PACKAGE)
	nosetests

install_deps: requirements.txt
	pip install -r $^

install_dev_deps: requirements-dev.txt
	pip install -r $^

venv:
	virtualenv $@