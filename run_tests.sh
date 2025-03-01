#!/usr/bin/env bash

# Add project root, libs/events and libs/core directories to the Python path
export PYTHONPATH=$PYTHONPATH:$(realpath $(dirname $0)):$(realpath $(dirname $0)/libs/events):$(realpath $(dirname $0)/libs/core)

# Run behave tests
cd tests && behave "$@" 