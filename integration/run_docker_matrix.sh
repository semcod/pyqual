#!/usr/bin/env bash
set -euo pipefail

docker build -t pyqual-integration-matrix -f integration/Dockerfile .
docker run --rm pyqual-integration-matrix
