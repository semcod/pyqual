#!/bin/bash
# Demo script for LLX + Pyqual integration
# Run from examples/llx directory

set -e

echo "=== LLX + Pyqual Integration Demo ==="
echo

# Check if we're in the right directory
if [ ! -f "pyqual-llx.yaml" ]; then
    echo "Error: Run this script from examples/llx directory"
    exit 1
fi

# Ensure tools are installed
echo "1. Checking dependencies..."
check_tool() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "  ✓ $1"
    else
        echo "  ✗ $1 - Install with: $2"
        missing=true
    fi
}

missing=false
check_tool "llx" "pip install llx[prellm]"
check_tool "pyqual" "pip install pyqual"
check_tool "code2llm" "pip install code2llm"
check_tool "vallm" "pip install vallm"

if [ "$missing" = true ]; then
    echo "Install missing dependencies first"
    exit 1
fi

echo
echo "2. Setting up project..."
# Go to project root
cd ../..

# Copy configuration if not exists
if [ ! -f "pyqual.yaml" ]; then
    cp examples/llx/pyqual-llx.yaml pyqual.yaml
    echo "  ✓ Created pyqual.yaml with LLX integration"
else
    echo "  ✓ Using existing pyqual.yaml"
fi

# Initialize llx if not exists
if [ ! -f "llx.toml" ]; then
    llx init . >/dev/null 2>&1
    echo "  ✓ Created llx.toml"
else
    echo "  ✓ Using existing llx.toml"
fi

echo
echo "3. Pipeline configuration:"
echo "  - Analyze code with code2llm"
echo "  - Validate with vallm"
echo "  - Generate fixes with LLX (model auto-selected based on metrics)"
echo "  - Run tests"
echo "  - Loop until quality gates pass"

echo
echo "4. Running quality pipeline..."
echo "   Press Ctrl+C to stop"
echo

# Run the pipeline
pyqual run

echo
echo "=== Demo Complete ==="
echo
echo "Check .pyqual/ directory for results:"
echo "  - errors.json    (validation errors found)"
echo "  - coverage.json  (test coverage results)"
echo
echo "LLX selected the optimal model based on your project metrics."
echo "Review the generated fixes in the output above."
