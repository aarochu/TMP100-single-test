# Runs the test suite on Debian 12, the same base as Raspberry Pi OS.
# Also proves the documented install path (venv + pip install -r) actually works.
#
#   docker build -t tmp100-test .
#   docker run --rm tmp100-test
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . /app
CMD ["sh", "-c", "python -c 'import smbus2; print(\"smbus2\", smbus2.__version__, \"installed OK\")' && python -B -m unittest discover -s tests -v"]
