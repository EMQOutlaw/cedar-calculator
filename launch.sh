#!/bin/sh
# Resolve relative to this file, not the working directory or a user's home.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$(readlink -f -- "$0")")" && pwd)
# Detach and close launch-provider response pipes, including startup logs.
exec qs -d -p "$root/shell.qml" "$@" >/dev/null 2>&1
