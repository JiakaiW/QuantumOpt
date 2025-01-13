#!/bin/bash

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate CQS

# Install frontend dependencies
cd src/quantum_opt/web/frontend
npm install

# Start the application
cd ../../../..
echo "Starting QuantumOpt web application..."
python examples/web_example.py 