@bootstrap:
    hatch env create

@install:
    hatch run python --version

@shell:
    cd example && hatch run python manage.py shell

@fmt:
    hatch fmt --formatter
    pre-commit run --all-files pyproject-fmt
    pre-commit run --all-files reorder-python-imports

@dj:
    cd example && hatch run python manage.py

@samples-test:
    cd samples && hatch run python test.py

@samples-clean:
    rm -r samples/outputs
