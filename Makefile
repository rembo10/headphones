PACKAGE = headphones

check:
	pep8 $PACKAGE
	pyflakes $PACKAGE
	nosetests

install_dependencies:
	pip install -r requirements.txt

install_dev_dependencies:
	pip install -r requirements-dev.txt

venv:
	virtualenv $@