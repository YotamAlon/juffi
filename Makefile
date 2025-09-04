all: build

build:
	python -m build

clean:
	rm -rf dist/ build/ juffi.egg-info/