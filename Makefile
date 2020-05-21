TEST_DB_CONTAINER_NAME = opencelldb-test

init:
	pip install -r requirements.txt

lint:
	flake8 . --count --statistics --exit-zero
	python -m pylint ./opencell

create-test-db:
	docker create --name $(TEST_DB_CONTAINER_NAME) \
	-e POSTGRES_PASSWORD=password \
	-e POSTGRES_DB=opencelldb-test \
	-p 5433:5432 \
	postgres;

start-test-db:
	docker start $(TEST_DB_CONTAINER_NAME) && sleep 2;

drop-test-db:
	docker rm --force $(TEST_DB_CONTAINER_NAME);

test:
	pytest -v
