.PHONY: alldoc apidoc bdist clean develop pyflakes pylint sdist test

OS := $(shell uname)

pip-requirements:
	pip install -r requirements.txt

alldoc: pip-requirements
	sphinx-apidoc --separate -F wreport -o alldoc
ifeq "$(OS)" "Darwin"
	sed -ie "s/html_theme = 'alabaster'/html_theme = 'default'/" alldoc/conf.py
	sed -ie "s/\#sys\.path\.insert(0, os\.path\.abspath('\.'))/sys.path.insert(0, os.path.abspath('..'))/" alldoc/conf.py
else
	sed -i "s/html_theme = 'alabaster'/html_theme = 'default'/" alldoc/conf.py
	sed -i "s/\#sys\.path\.insert(0, os\.path\.abspath('\.'))/sys.path.insert(0, os.path.abspath('..'))/" alldoc/conf.py
endif
	echo 'import sphinx_rtd_theme' >> alldoc/conf.py
	echo 'html_theme = "sphinx_rtd_theme"' >> alldoc/conf.py
	echo 'html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]' >> alldoc/conf.py
	$(MAKE) -C alldoc html

apidoc: pip-requirements
	sphinx-apidoc --separate --private -F wreport -o apidoc
ifeq "$(OS)" "Darwin"
	sed -ie "s/html_theme = 'alabaster'/html_theme = 'default'/" apidoc/conf.py
	sed -ie "s/\#sys\.path\.insert(0, os\.path\.abspath('\.'))/sys.path.insert(0, os.path.abspath('..'))/" apidoc/conf.py
else
	sed -i "s/html_theme = 'alabaster'/html_theme = 'default'/" apidoc/conf.py
	sed -i "s/\#sys\.path\.insert(0, os\.path\.abspath('\.'))/sys.path.insert(0, os.path.abspath('..'))/" apidoc/conf.py
endif
	echo 'import sphinx_rtd_theme' >> apidoc/conf.py
	echo 'html_theme = "sphinx_rtd_theme"' >> apidoc/conf.py
	echo 'html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]' >> apidoc/conf.py
	$(MAKE) -C apidoc html

bdist: pip-requirements
	python2 setup.py bdist

clean:
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	rm -rf alldoc
	rm -rf apidoc
	rm -rf htmlcov
	rm -rf wreport/__pycache__

develop: pip-requirements
	sudo python2 setup.py develop
	#sudo python3.4 setup.py develop

pyflakes: pip-requirements
	pyflakes wreport

pylint: pip-requirements
	pylint --rcfile=.pylintrc wreport

sdist: pip-requirements
	python2 setup.py sdist

test: pip-requirements
	coverage2 run --source wreport setup.py test
	coverage html
	coverage report -m
