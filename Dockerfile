FROM ubuntu:bionic AS base

RUN apt-get update && \
    apt-get install -y \
        python3.7 \
	python3-pip \
    && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT []
CMD []


FROM base AS dist

WORKDIR /src
COPY . ./
RUN python3.7 -m pip wheel . && ls -lahR /src

ENTRYPOINT []
CMD []


FROM base AS test

WORKDIR /app
COPY --from=dist /src/swarmrunner-0.1.0-py3-none-any.whl /tmp/
RUN python3.7 -m pip install /tmp/swarmrunner-0.1.0-py3-none-any.whl

ENTRYPOINT []
CMD []
