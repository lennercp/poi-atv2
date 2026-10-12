#!/bin/bash
cd "$(dirname "$0")/.."
set -a
source config/app.env
set +a
java $JAVA_OPTS -jar target/cpu-bound.jar
