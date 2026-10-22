FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash obc \
    && mkdir -p /var/lib/obc /opt/scripts /run/sshd \
    && echo "obc:password123" | chpasswd

RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY obc/scripts /opt/scripts
RUN chmod +x /opt/scripts/*.py \
    && ln -sf /opt/scripts/releasePanel.py /usr/local/bin/releasePanel.py \
    && ln -sf /opt/scripts/getReleaseStatus.py /usr/local/bin/getReleaseStatus.py

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
