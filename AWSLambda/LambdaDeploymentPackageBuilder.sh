#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="catweazle-lambda-$(date +%Y%m%d-%H%M%S).zip"
TEMP_DIR=$(mktemp -d)

cleanup() { rm -rf "${TEMP_DIR}"; }
trap cleanup EXIT

PACKAGE_DIR="${TEMP_DIR}/catweazle-lambda"
mkdir -p "${PACKAGE_DIR}"

[[ -f "${SCRIPT_DIR}/function.py" ]] || { echo "Error: function.py not found"; exit 1; }
cp "${SCRIPT_DIR}/function.py" "${PACKAGE_DIR}/"

[[ -f "${SCRIPT_DIR}/__init__.py" ]] && cp "${SCRIPT_DIR}/__init__.py" "${PACKAGE_DIR}/"
[[ -f "${SCRIPT_DIR}/requirements.txt" ]] && cp "${SCRIPT_DIR}/requirements.txt" "${PACKAGE_DIR}/"

if [[ -f "${PACKAGE_DIR}/requirements.txt" ]]; then
    pip install -r "${PACKAGE_DIR}/requirements.txt" -t "${PACKAGE_DIR}/" --no-cache-dir
    find "${PACKAGE_DIR}" -name "*.pyc" -delete
    find "${PACKAGE_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
fi

find "${PACKAGE_DIR}" -type f -exec chmod 644 {} \;
cd "${PACKAGE_DIR}"
zip -r "${SCRIPT_DIR}/${OUTPUT_FILE}" .

echo "Created: ${OUTPUT_FILE}"
echo "Size: $(du -h "${SCRIPT_DIR}/${OUTPUT_FILE}" | cut -f1)"