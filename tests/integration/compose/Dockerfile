FROM python:3.12-alpine
RUN --mount=type=secret,id=synthetic,required=true python -c "from pathlib import Path; value=Path('/run/secrets/synthetic').read_text(); assert value.startswith('SYNTHETIC_'); Path('/build-result').write_text('authenticated synthetic step completed')"
USER 65534:65534
