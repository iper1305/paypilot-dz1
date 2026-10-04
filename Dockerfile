# Only the dependencies live in the image; the script, cases.json and
# reports/ are mounted from the working copy, so edits apply without a rebuild.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEEPEVAL_TELEMETRY_OPT_OUT=1

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /work
ENTRYPOINT ["python", "l02_eval.py"]
