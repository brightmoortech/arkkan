#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [ ! -f ".python-version" ]; then
    echo "[ERROR] .python-version not found"
    exit 1
fi

REQUIRED_VERSION="$(tr -d '[:space:]' < .python-version)"

if [ -z "${REQUIRED_VERSION}" ]; then
    echo "[ERROR] .python-version is empty"
    exit 1
fi

MAJOR_MINOR="${REQUIRED_VERSION%.*}"

PYTHON_CANDIDATES=(
    "python${MAJOR_MINOR}"
    "python3"
    "/Library/Frameworks/Python.framework/Versions/${MAJOR_MINOR}/bin/python3"
)

PYTHON_EXECUTABLE=""

for candidate in "${PYTHON_CANDIDATES[@]}"; do
    if command -v "${candidate}" >/dev/null 2>&1; then
        candidate_path="$(command -v "${candidate}")"
    elif [ -x "${candidate}" ]; then
        candidate_path="${candidate}"
    else
        continue
    fi

    candidate_version="$(
        "${candidate_path}" -c         'import platform; print(platform.python_version())'
    )"

    if [ "${candidate_version}" = "${REQUIRED_VERSION}" ]; then
        PYTHON_EXECUTABLE="${candidate_path}"
        break
    fi
done

if [ -z "${PYTHON_EXECUTABLE}" ]; then
    echo "[ERROR] Python ${REQUIRED_VERSION} not found"
    exit 1
fi

echo "[OK] Using Python ${REQUIRED_VERSION}: ${PYTHON_EXECUTABLE}"

if [ ! -d ".venv" ]; then
    "${PYTHON_EXECUTABLE}" -m venv .venv
    echo "[CREATE] Virtual environment: .venv"
else
    echo "[SKIP] Virtual environment already exists: .venv"
fi

source .venv/bin/activate

VENV_VERSION="$(
    python -c 'import platform; print(platform.python_version())'
)"

if [ "${VENV_VERSION}" != "${REQUIRED_VERSION}" ]; then
    echo "[ERROR] .venv uses Python ${VENV_VERSION}; expected ${REQUIRED_VERSION}"
    exit 1
fi

python -m pip install -r requirements-bootstrap.txt
python -m pip install -r requirements.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check

python -m pytest

echo "[OK] Bootstrap complete"
