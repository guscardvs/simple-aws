.PHONY: format test

format:
	@poetry run black simple_aws tests
	@poetry run isort -ir simple_aws tests
	@poetry run autoflake --remove-all-unused-imports --remove-unused-variables --remove-duplicate-keys --expand-star-imports -ir simple_aws tests

test:
	@poetry run pytest
