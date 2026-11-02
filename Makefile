.PHONY: install migrate run test coa brackets

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

migrate:
	python manage.py makemigrations && python manage.py migrate

run:
	python manage.py runserver

test:
	python manage.py test

coa:
	python manage.py init_coa --company-id 1

brackets:
	python manage.py seed_tax_brackets --year 1403
