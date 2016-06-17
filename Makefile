check:
	pep8 headphones
	pyflakes headphones
	nosetests

install_dev_dependencies:
	pip install -r requirements-dev.txt

venv:
	virtualenv $@