#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [ ! -f ".python-version" ]; then
    echo "[ERROR] .python-version not found" >&2
    exit 1
fi

REQUIRED_VERSION="$(tr -d '[:space:]' < .python-version)"

if [ -z "${REQUIRED_VERSION}" ]; then
    echo "[ERROR] .python-version is empty" >&2
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

    if ! candidate_version="$(
        "${candidate_path}" -c 'import platform; print(platform.python_version())'
    )"; then
        continue
    fi

    if [ "${candidate_version}" = "${REQUIRED_VERSION}" ]; then
        PYTHON_EXECUTABLE="${candidate_path}"
        break
    fi
done

if [ -z "${PYTHON_EXECUTABLE}" ]; then
    echo "[ERROR] Python ${REQUIRED_VERSION} not found" >&2
    exit 1
fi

echo "[OK] Using Python ${REQUIRED_VERSION}: ${PYTHON_EXECUTABLE}"

if [ ! -d ".venv" ]; then
    "${PYTHON_EXECUTABLE}" -m venv .venv
    echo "[CREATE] Virtual environment: .venv"
else
    echo "[SKIP] Virtual environment already exists: .venv"
fi

VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [ ! -x "${VENV_PYTHON}" ]; then
    echo "[ERROR] .venv has no executable Python; inspect the environment before recreating it" >&2
    exit 1
fi

VENV_VERSION="$(
    "${VENV_PYTHON}" -c 'import platform; print(platform.python_version())'
)"

if [ "${VENV_VERSION}" != "${REQUIRED_VERSION}" ]; then
    echo "[ERROR] .venv uses Python ${VENV_VERSION}; expected ${REQUIRED_VERSION}" >&2
    exit 1
fi

"${VENV_PYTHON}" -m pip install -r requirements-bootstrap.txt
"${VENV_PYTHON}" -m pip install -r requirements-runtime.txt -r requirements.txt
"${VENV_PYTHON}" -m pip install --no-build-isolation --no-deps -e .
"${VENV_PYTHON}" -m pip check

"${VENV_PYTHON}" -m pytest

echo "[OK] Bootstrap complete"
