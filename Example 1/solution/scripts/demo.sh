#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"

printf 'GET %s/health\n' "${BASE_URL}"
curl --silent --show-error --fail-with-body -- "${BASE_URL}/health"
printf '\n'
printf 'Repeated GET %s/hello requests\n' "${BASE_URL}"
for request_number in {1..6}; do
    printf 'Request %s: ' "${request_number}"
    curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' -- "${BASE_URL}/hello"
done
