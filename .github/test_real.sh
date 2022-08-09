#!/bin/bash
set -e

cd tests
testflo -v -n 1 --coverage --coverpkg baseclasses
