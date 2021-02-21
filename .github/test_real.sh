#!/bin/bash
set -e
if [[ $AGENT_NAME == "Azure Pipelines"* ]]; then
    N_TEST=1
else
    N_TEST=4
fi
testflo -v -n $N_TEST
