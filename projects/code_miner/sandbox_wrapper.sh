#!/usr/bin/env bash
ulimit -t 2
ulimit -v 131072
exec "$@"
