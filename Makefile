init:
	pip install -r requirements.txt

lint:
	flake8 . --count --statistics --exit-zero
	python -m pylint ./opencell

test:
	pytest -v
