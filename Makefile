all: build

build:
	pyproject-build

wheel:
	pyproject-build --wheel

sdist:
	pyproject-build --sdist

clean:
	rm -rf dist/ build/ juffi.egg-info/
