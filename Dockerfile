FROM python:3.13.7-slim

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir /multivol_web /multivol_cli && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        unzip \
        curl \
        # need to install docker for dind needed by MULTIVOL CLI
        ca-certificates \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get -y update \
    && apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
    && rm -rf /var/lib/apt/lists/* && \
    pip install uv
 
COPY . /multivol_web

RUN git clone https://github.com/BoBNewz/MultiVolatility.git -b feature/add-output-parameter /multivol_cli && \
    uv pip install --system -r /multivol_cli/requirements.txt && \
    uv pip install --system -r /multivol_web/requirements.txt

WORKDIR /multivol_web

ENTRYPOINT [ "reflex","run","--env","prod" ]