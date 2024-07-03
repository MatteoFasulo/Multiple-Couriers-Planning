#!/bin/bash

# Array of Python scripts
scripts=("cp.py" "smt.py" "mip.py")

# Array of models
models=("default" "SB")

# Default values
TIMEOUT=300
SEED=42
VERBOSE=false

# Parse additional optional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --timeout|-t) TIMEOUT="$2"; shift ;;
        --seed) SEED="$2"; shift ;;
        --verbose) VERBOSE=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Loop over scripts, solvers, and models
for script in "${scripts[@]}"; do
    if [ "$script" == "cp.py" ]; then
        solvers=("gecode" "chuffed")
    elif [ "$script" == "smt.py" ]; then
        solvers=("z3")
    elif [ "$script" == "mip.py" ]; then
        solvers=("CBC" "GLPK")
    fi
    for solver in "${solvers[@]}"; do
        for model in "${models[@]}"; do
            CMD="python3 $script --runall --timeout $TIMEOUT --solver $solver --seed $SEED --model $model"
            $VERBOSE && CMD+=" --verbose"
            echo "Running command: $CMD"
            eval $CMD
