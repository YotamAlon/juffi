all: build

build:
	pyproject-build

wheel:
	pyproject-build --wheel

sdist:
	pyproject-build --sdist

test:
	pytest tests/

lint:
	pylint juffi/

coverage:
	coverage run -m pytest tests/
	coverage combine
	coverage report

clean:
	rm -rf dist/ build/ juffi.egg-info/
