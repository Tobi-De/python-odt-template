@install:
    hatch run python --version

@shell:
    cd example && hatch run python manage.py shell

@fmt:
    hatch fmt --formatter
    pre-commit run --all-files pyproject-fmt
    pre-commit run --all-files reorder-python-imports
