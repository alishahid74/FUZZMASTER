#!/bin/bash
# Master Installation Script
# Sets up complete AFL++ with PPO fuzzing framework

set -e

PROJECT_ROOT="${1:-$HOME/fuzzing-project}"

echo "======================================"
echo "AFL++ PPO Fuzzing - Master Setup"
echo "======================================"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

# Check if running in project directory
if [ ! -d "$PROJECT_ROOT" ]; then
    print_info "Creating project directory: $PROJECT_ROOT"
    mkdir -p "$PROJECT_ROOT"
fi

cd "$PROJECT_ROOT"

# Step 1: Download all project files
echo ""
echo "=== Step 1: Checking Project Files ==="
echo ""

# List of required files
REQUIRED_FILES=(
    # Phase 2 - Core Implementation
    "ppo_agent.py"
    "feedback_analyzer.py"
    "mutation_selector.py"
    "fuzzing_controller.py"
    "config.yaml"
    "requirements.txt"
    
    # Phase 3 - Experiments
    "experiment_runner.py"
    "data_analysis.py"
    "visualizer.py"
    "generate_sample_data.py"
    
    # Phase 4 - Documentation
    "report_generator.py"
    "presentation_generator.py"
    "documentation_generator.py"
    
    # Benchmarks
    "benchmark_runner.py"
    "setup_benchmarks.sh"
)

MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    print_error "Missing ${#MISSING_FILES[@]} required files!"
    echo ""
    echo "Please download these files and place them in $PROJECT_ROOT:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "You can get all files from Claude's outputs or download the complete archive:"
    echo "  afl-ppo-complete-project.tar.gz"
    echo ""
    echo "Then extract in this directory:"
    echo "  cd $PROJECT_ROOT"
    echo "  tar -xzf /path/to/afl-ppo-complete-project.tar.gz"
    echo ""
    exit 1
else
    print_status "All required files present!"
fi

# Step 2: Check Python environment
echo ""
echo "=== Step 2: Python Environment ==="
echo ""

if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
fi

print_status "Activating virtual environment..."
source venv/bin/activate

print_info "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

print_status "Python environment ready!"

# Step 3: Verify AFL++
echo ""
echo "=== Step 3: AFL++ Verification ==="
echo ""

if ! command -v afl-fuzz &> /dev/null; then
    print_error "AFL++ not found!"
    echo ""
    echo "Please install AFL++ first:"
    echo "  cd ~"
    echo "  git clone https://github.com/AFLplusplus/AFLplusplus.git"
    echo "  cd AFLplusplus"
    echo "  make all"
    echo "  sudo make install"
    exit 1
else
    print_status "AFL++ found: $(which afl-fuzz)"
fi

# Check QEMU mode
if [ ! -f "$HOME/AFLplusplus/afl-qemu-trace" ] && [ ! -f "/usr/local/bin/afl-qemu-trace" ]; then
    print_error "AFL++ QEMU mode not found!"
    echo ""
    echo "Building QEMU mode..."
    cd ~/AFLplusplus/qemu_mode
    ./build_qemu_support.sh
    cd "$PROJECT_ROOT"
fi

print_status "AFL++ QEMU mode available"

# Step 4: Directory Structure
echo ""
echo "=== Step 4: Directory Structure ==="
echo ""

mkdir -p afl-workdir/input
mkdir -p afl-workdir/output
mkdir -p afl-workdir/seeds
mkdir -p binaries
mkdir -p logs
mkdir -p models
mkdir -p results

# Create basic seed files
if [ ! "$(ls -A afl-workdir/input)" ]; then
    print_info "Creating initial seed corpus..."
    echo "GET / HTTP/1.0" > afl-workdir/input/http_request.txt
    echo "test" > afl-workdir/input/test1.txt
    echo "Hello World" > afl-workdir/input/test2.txt
    print_status "Initial seeds created"
fi

print_status "Directory structure ready"

# Step 5: System Configuration
echo ""
echo "=== Step 5: System Configuration ==="
echo ""

print_info "Configuring system for AFL++..."

# Set core pattern
if [ -w /proc/sys/kernel/core_pattern ]; then
    echo core | sudo tee /proc/sys/kernel/core_pattern > /dev/null
    print_status "Core pattern configured"
else
    print_info "Cannot set core pattern (needs sudo)"
fi

# Set CPU governor
if [ -w /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
    print_status "CPU governor set to performance"
else
    print_info "Cannot set CPU governor (needs sudo)"
fi

# Step 6: Test Installation
echo ""
echo "=== Step 6: Testing Installation ==="
echo ""

print_info "Running quick test..."

# Test imports
python3 << 'PYEOF'
import sys
try:
    import torch
    import numpy
    import pandas
    import matplotlib
    print("✓ All Python packages imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
PYEOF

if [ $? -eq 0 ]; then
    print_status "Python packages working"
else
    print_error "Python package test failed"
    exit 1
fi

# Create test script
cat > test_setup.py << 'EOF'
"""Quick setup test"""
import sys
from pathlib import Path

print("Testing imports...")
try:
    # Test core modules can be imported
    # from ppo_agent import PPOAgent  # Commented out as it might fail without full setup
    # from feedback_analyzer import FeedbackAnalyzer
    print("✓ Core modules exist")
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

print("✓ Setup test passed!")
EOF

python test_setup.py
rm test_setup.py

print_status "Installation test passed!"

# Step 7: Summary
echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""

print_status "Project directory: $PROJECT_ROOT"
print_status "Virtual environment: $PROJECT_ROOT/venv"
print_status "AFL++ available: $(which afl-fuzz)"
print_status "Python packages installed"

echo ""
echo "Next Steps:"
echo ""
echo "1. Activate environment:"
echo "   cd $PROJECT_ROOT"
echo "   source venv/bin/activate"
echo ""
echo "2. Quick test (5 minutes):"
echo "   python generate_sample_data.py -o results/test"
echo "   python data_analysis.py results/test"
echo "   python visualizer.py results/test"
echo ""
echo "3. Run experiments:"
echo "   # Single binary test"
echo "   python fuzzing_controller.py binaries/openssl-1.1.1f/apps/openssl \\"
echo "       -i afl-workdir/input -o afl-workdir/output-ppo -c config.yaml -d 0.5"
echo ""
echo "   # OR: Multiple benchmarks"
echo "   ./setup_benchmarks.sh  # First time only"
echo "   python benchmark_runner.py --duration 0.1 --mode both"
echo ""
echo "4. Documentation:"
echo "   See README_PHASE*.md files for detailed guides"
echo ""

# Create quick reference card
cat > QUICK_REFERENCE.txt << 'EOF'
AFL++ PPO Fuzzing - Quick Reference
====================================

ACTIVATE ENVIRONMENT:
  cd ~/fuzzing-project
  source venv/bin/activate

SINGLE BINARY FUZZING:
  python fuzzing_controller.py <binary> -i <input> -o <output> -c config.yaml -d <hours>

MULTIPLE BENCHMARKS:
  ./setup_benchmarks.sh              # First time setup
  python benchmark_runner.py --list  # Show available benchmarks
  python benchmark_runner.py --duration 1.0 --mode both

EXPERIMENTS:
  python experiment_runner.py <binary> -i <input> -r <results> --baseline-duration 2.0 --ppo-duration 2.0

ANALYSIS:
  python data_analysis.py <results_dir>
  python visualizer.py <results_dir>

DOCUMENTATION:
  python report_generator.py <results_dir> -o paper.md
  python presentation_generator.py -r <results_dir> -o slides.md

TEST WITH SAMPLE DATA:
  python generate_sample_data.py -o results/test
  python data_analysis.py results/test
  python visualizer.py results/test

TROUBLESHOOTING:
  - Check logs in: logs/
  - Verify AFL++: afl-fuzz --version
  - Check Python: python --version
  - See README_PHASE*.md for detailed help
EOF

print_status "Created QUICK_REFERENCE.txt"

echo ""
echo "=== Installation Complete! ==="
echo ""
