#!/bin/bash
# Verification Script for AFL++ + PPO Setup
# This script checks if all components are properly installed

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

echo -e "${BLUE}=========================================="
echo "AFL++ + PPO Setup Verification"
echo -e "==========================================${NC}"
echo ""

# Function to check and report
check_command() {
    local cmd=$1
    local name=$2
    
    if command -v "$cmd" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $name is installed"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name is NOT installed"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

check_file() {
    local file=$1
    local name=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $name exists"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name does NOT exist"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

check_directory() {
    local dir=$1
    local name=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $name exists"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name does NOT exist"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

check_python_package() {
    local package=$1
    
    if python3 -c "import $package" &> /dev/null; then
        echo -e "${GREEN}✓${NC} Python package '$package' is installed"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Python package '$package' is NOT installed"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Check system commands
echo -e "${YELLOW}[1] Checking System Commands${NC}"
check_command "git" "Git"
check_command "gcc" "GCC"
check_command "clang" "Clang"
check_command "python3" "Python 3"
check_command "pip3" "Pip3"
echo ""

# Check AFL++
echo -e "${YELLOW}[2] Checking AFL++ Installation${NC}"
check_command "afl-fuzz" "AFL++ (afl-fuzz)"
check_command "afl-gcc" "AFL++ (afl-gcc)"
check_command "afl-qemu-trace" "AFL++ QEMU mode"

if command -v afl-fuzz &> /dev/null; then
    VERSION=$(afl-fuzz -h 2>&1 | head -1 || echo "Unknown")
    echo -e "  ${BLUE}Version:${NC} $VERSION"
fi
echo ""

# Check project structure
echo -e "${YELLOW}[3] Checking Project Structure${NC}"
PROJECT_DIR="$HOME/fuzzing-project"

check_directory "$PROJECT_DIR" "Project directory"
check_directory "$PROJECT_DIR/venv" "Virtual environment"
check_directory "$PROJECT_DIR/afl-workdir" "AFL workdir"
check_directory "$PROJECT_DIR/afl-workdir/input" "Input corpus directory"
check_directory "$PROJECT_DIR/binaries" "Binaries directory"
check_directory "$PROJECT_DIR/results" "Results directory"
echo ""

# Check binaries
echo -e "${YELLOW}[4] Checking Test Binaries${NC}"
check_directory "$PROJECT_DIR/binaries/openssl-1.1.1f" "OpenSSL source"
check_file "$PROJECT_DIR/binaries/openssl-1.1.1f/apps/openssl" "OpenSSL binary"

if [ -f "$PROJECT_DIR/binaries/openssl-1.1.1f/apps/openssl" ]; then
    VERSION=$("$PROJECT_DIR/binaries/openssl-1.1.1f/apps/openssl" version 2>&1 || echo "Error")
    echo -e "  ${BLUE}OpenSSL Version:${NC} $VERSION"
fi
echo ""

# Check input corpus
echo -e "${YELLOW}[5] Checking Input Corpus${NC}"
INPUT_DIR="$PROJECT_DIR/afl-workdir/input"
if [ -d "$INPUT_DIR" ]; then
    FILE_COUNT=$(find "$INPUT_DIR" -type f | wc -l)
    if [ "$FILE_COUNT" -ge 3 ]; then
        echo -e "${GREEN}✓${NC} Input corpus has $FILE_COUNT files (minimum 3 required)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} Input corpus has only $FILE_COUNT files (need at least 3)"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${RED}✗${NC} Input corpus directory not found"
    FAILED=$((FAILED + 1))
fi
echo ""

# Check Python environment
echo -e "${YELLOW}[6] Checking Python Environment${NC}"

if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    
    echo -e "  ${BLUE}Python:${NC} $(python3 --version)"
    echo -e "  ${BLUE}Pip:${NC} $(pip --version | cut -d' ' -f1-2)"
    echo ""
    
    echo -e "${YELLOW}[7] Checking Python Packages${NC}"
    check_python_package "torch"
    check_python_package "numpy"
    check_python_package "matplotlib"
    check_python_package "pandas"
    check_python_package "gym"
    check_python_package "stable_baselines3"
    
    if python3 -c "import torch" &> /dev/null; then
        TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)")
        echo -e "  ${BLUE}PyTorch Version:${NC} $TORCH_VERSION"
    fi
else
    echo -e "${RED}✗${NC} Virtual environment not found"
    FAILED=$((FAILED + 1))
fi
echo ""

# System optimization checks
echo -e "${YELLOW}[8] Checking System Optimization${NC}"

# CPU governor
if [ -f "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
    GOVERNOR=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    if [ "$GOVERNOR" = "performance" ]; then
        echo -e "${GREEN}✓${NC} CPU governor set to 'performance'"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}!${NC} CPU governor is '$GOVERNOR' (recommended: 'performance')"
    fi
else
    echo -e "${YELLOW}!${NC} Cannot check CPU governor (may not be applicable)"
fi

# Core pattern
CORE_PATTERN=$(cat /proc/sys/kernel/core_pattern 2>/dev/null || echo "unknown")
if [ "$CORE_PATTERN" = "core" ]; then
    echo -e "${GREEN}✓${NC} Core pattern configured correctly"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}!${NC} Core pattern is '$CORE_PATTERN' (recommended: 'core')"
fi

# ASLR
ASLR=$(cat /proc/sys/kernel/randomize_va_space 2>/dev/null || echo "unknown")
if [ "$ASLR" = "0" ]; then
    echo -e "${GREEN}✓${NC} ASLR disabled (good for fuzzing)"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}!${NC} ASLR is enabled (value: $ASLR)"
fi

echo ""

# Quick functionality test
echo -e "${YELLOW}[9] Quick Functionality Test${NC}"

if command -v afl-fuzz &> /dev/null && [ -d "$PROJECT_DIR/afl-workdir/input" ]; then
    echo "Running 5-second test fuzzing session..."
    
    TEST_OUTPUT="$PROJECT_DIR/afl-workdir/output-verify-test"
    rm -rf "$TEST_OUTPUT" 2>/dev/null
    
    if timeout 5 afl-fuzz -i "$PROJECT_DIR/afl-workdir/input" \
                          -o "$TEST_OUTPUT" \
                          -Q \
                          -m none \
                          -- "$PROJECT_DIR/binaries/openssl-1.1.1f/apps/openssl" s_server @@ \
                          &> /dev/null; then
        echo -e "${GREEN}✓${NC} AFL++ can start fuzzing"
        PASSED=$((PASSED + 1))
    else
        # Check if output directory was created (fuzzing started)
        if [ -d "$TEST_OUTPUT" ]; then
            echo -e "${GREEN}✓${NC} AFL++ can start fuzzing (timed out as expected)"
            PASSED=$((PASSED + 1))
        else
            echo -e "${RED}✗${NC} AFL++ failed to start fuzzing"
            FAILED=$((FAILED + 1))
        fi
    fi
    
    rm -rf "$TEST_OUTPUT" 2>/dev/null
else
    echo -e "${YELLOW}!${NC} Skipping functionality test (missing requirements)"
fi

echo ""

# Summary
echo -e "${BLUE}=========================================="
echo "Verification Summary"
echo -e "==========================================${NC}"
echo ""
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Setup is complete.${NC}"
    echo ""
    echo "You are ready to proceed with Phase 2: PPO Implementation"
    echo ""
    echo "To get started:"
    echo "  1. cd ~/fuzzing-project"
    echo "  2. source venv/bin/activate"
    echo "  3. Continue with the implementation guide"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Run the setup script: ./setup_environment.sh"
    echo "  - Check SETUP_GUIDE.md for detailed instructions"
    echo "  - Review troubleshooting section"
    exit 1
fi
