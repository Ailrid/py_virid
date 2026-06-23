#!/bin/bash
set -e

NEW_VERSION="0.1.2"


sed -i "s/^version = \"[0-9.]*\"/version = \"${NEW_VERSION}\"/" packages/core/pyproject.toml
sed -i "s/^version = \"[0-9.]*\"/version = \"${NEW_VERSION}\"/" packages/std/pyproject.toml
sed -i "s/^version = \"[0-9.]*\"/version = \"${NEW_VERSION}\"/" pyproject.toml


rm -rf dist/
uv build --package virid-core
uv build --package virid-std



uvx twine upload dist/virid_core*

sleep 5

uvx twine upload dist/virid_std*