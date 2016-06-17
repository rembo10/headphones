check:
	pep8 headphones
	pyflakes headphones
	nosetests

install_dependencies:
	pip install -r requirements.txt

install_dev_dependencies:
	pip install -r requirements-dev.txt

venv:
	virtualenv $@