#!/bin/bash
# FuzzMaster - Professional Installation Script
# Quick and easy setup for the complete fuzzing framework

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ███████╗██╗   ██╗███████╗███████╗                              ║
║   ██╔════╝██║   ██║╚══███╔╝╚══███╔╝                              ║
║   █████╗  ██║   ██║  ███╔╝   ███╔╝                               ║
║   ██╔══╝  ██║   ██║ ███╔╝   ███╔╝                                ║
║   ██║     ╚██████╔╝███████╗███████╗                              ║
║   ╚═╝      ╚═════╝ ╚══════╝╚══════╝                              ║
║                                                                   ║
║   ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗           ║
║   ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗          ║
║   ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝          ║
║   ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗          ║
║   ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║          ║
║   ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝          ║
║                                                                   ║
║             Professional Installation Script                      ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Helper functions
print_header() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_step() {
    echo -e "${MAGENTA}[$1/$2]${NC} $3"
}

# Main installation
print_header "FuzzMaster Installation"

PROJECT_ROOT="${1:-$HOME/fuzzing-project}"
print_info "Installation directory: ${CYAN}$PROJECT_ROOT${NC}"

# Step 1: Create directory structure
print_step 1 6 "Creating directory structure..."
mkdir -p "$PROJECT_ROOT"/{binaries,afl-workdir,results,logs,models,config}
cd "$PROJECT_ROOT"
print_success "Directory structure created"

# Step 2: Check AFL++
print_step 2 6 "Checking AFL++ installation..."
if command -v afl-fuzz &> /dev/null; then
    AFL_VERSION=$(afl-fuzz --version 2>&1 | head -1)
    print_success "AFL++ found: $AFL_VERSION"
else
    print_warning "AFL++ not found!"
    echo -e "${YELLOW}Please install AFL++ first:${NC}"
    echo "  cd ~"
    echo "  git clone https://github.com/AFLplusplus/AFLplusplus.git"
    echo "  cd AFLplusplus"
    echo "  make all"
    echo "  sudo make install"
    exit 1
fi

# Step 3: Setup Python environment
print_step 3 6 "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
fi

source venv/bin/activate
print_success "Virtual environment activated"

# Step 4: Install Python dependencies
print_step 4 6 "Installing Python dependencies..."
pip install --upgrade pip -q

# Create requirements file if not exists
cat > requirements.txt << 'REQS'
torch>=2.0.0
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.4.0
seaborn>=0.11.0
scipy>=1.7.0
pyyaml>=5.4.0
colorama>=0.4.6
REQS

pip install -r requirements.txt -q
print_success "Python dependencies installed"

# Step 5: Install FuzzMaster
print_step 5 6 "Installing FuzzMaster..."

# Check if fuzzmaster.py exists
if [ -f "fuzzmaster.py" ]; then
    chmod +x fuzzmaster.py
    print_success "FuzzMaster installed"
else
    print_warning "fuzzmaster.py not found in current directory"
    print_info "Please download fuzzmaster.py to $PROJECT_ROOT"
fi

# Step 6: System configuration
print_step 6 6 "Configuring system for fuzzing..."

# Core pattern
if [ -w /proc/sys/kernel/core_pattern ]; then
    echo core | sudo tee /proc/sys/kernel/core_pattern > /dev/null 2>&1
    print_success "Core pattern configured"
else
    print_warning "Cannot configure core pattern (needs sudo)"
fi

# CPU governor
if [ -d /sys/devices/system/cpu/cpu0/cpufreq ]; then
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1
    print_success "CPU governor configured"
else
    print_info "CPU governor configuration skipped"
fi

# Create quick start scripts
print_header "Creating Helper Scripts"

# Quick start script
cat > run_fuzzmaster.sh << 'RUNNER'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 fuzzmaster.py "$@"
RUNNER
chmod +x run_fuzzmaster.sh
print_success "Created run_fuzzmaster.sh"

# Status checker
cat > check_status.sh << 'STATUS'
#!/bin/bash
echo "=== FuzzMaster Status ==="
echo ""
echo "Running fuzzers:"
ps aux | grep afl-fuzz | grep -v grep | wc -l
echo ""
echo "Total crashes found:"
find ~/fuzzing-project/results -name "id:*" -path "*/crashes/*" 2>/dev/null | wc -l
echo ""
echo "Results directories:"
ls -ld ~/fuzzing-project/results/*/ 2>/dev/null | wc -l
STATUS
chmod +x check_status.sh
print_success "Created check_status.sh"

# Installation complete
print_header "Installation Complete!"

echo -e "${GREEN}✓ FuzzMaster is ready to use!${NC}\n"

print_info "Quick Start Commands:"
echo -e "  ${CYAN}cd $PROJECT_ROOT${NC}"
echo -e "  ${CYAN}source venv/bin/activate${NC}"
echo -e "  ${CYAN}python3 fuzzmaster.py --interactive${NC}"
echo ""

print_info "Or use the helper script:"
echo -e "  ${CYAN}./run_fuzzmaster.sh --interactive${NC}"
echo ""

print_info "Check status anytime:"
echo -e "  ${CYAN}./check_status.sh${NC}"
echo ""

print_header "Next Steps"

echo -e "${YELLOW}1.${NC} Activate environment:"
echo -e "   ${CYAN}source venv/bin/activate${NC}"
echo ""

echo -e "${YELLOW}2.${NC} List available benchmarks:"
echo -e "   ${CYAN}python3 fuzzmaster.py --list${NC}"
echo ""

echo -e "${YELLOW}3.${NC} Start fuzzing (interactive):"
echo -e "   ${CYAN}python3 fuzzmaster.py --interactive${NC}"
echo ""

echo -e "${YELLOW}4.${NC} Or quick command-line:"
echo -e "   ${CYAN}python3 fuzzmaster.py --benchmark openssl --mode quick${NC}"
echo ""

print_success "Happy Fuzzing! 🚀"
echo ""
