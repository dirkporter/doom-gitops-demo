# Build-once alternative to the inline pip-at-startup container.
# OpenShift-friendly: runs fine as an arbitrary non-root UID (restricted-v2).
#
#   podman build -t quay.io/<you>/doom-api:latest build/
#   podman push quay.io/<you>/doom-api:latest
#
# Then in manifests/api-deployment.yaml, replace the python:3.9-slim container
# (image + command + args + the app-code volume/volumeMount) with simply:
#   image: quay.io/<you>/doom-api:latest
# keeping the same env, ports, and probes.
FROM python:3.9-slim

WORKDIR /opt/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

# Group-write so an arbitrary UID (member of GID 0) can run cleanly on OpenShift
RUN chgrp -R 0 /opt/app && chmod -R g=u /opt/app

EXPOSE 8080
CMD ["python", "/opt/app/app.py"]
