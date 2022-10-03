#!/bin/bash

set -euo pipefail

docker run --rm -it --gpus all -p 8080:8080 simswap:latest $@
