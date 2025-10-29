#!/bin/bash
# AFL++ with PPO Fuzzing Framework - Environment Setup Script
# This script sets up the complete environment for fuzzing experiments

set -e  # Exit on error

echo "=========================================="
echo "AFL++ + PPO Fuzzing Framework Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_warning "Running as root. This is okay for VM setup."
fi

# Create project directory structure
print_status "Creating project directory structure..."
mkdir -p ~/fuzzing-project/{afl-workdir,binaries,results,logs,models}
mkdir -p ~/fuzzing-project/afl-workdir/{input,output}
mkdir -p ~/fuzzing-project/results/{graphs,data,reports}

cd ~/fuzzing-project

# System update and dependencies
print_status "Updating system and installing dependencies..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    git \
    wget \
    curl \
    cmake \
    ninja-build \
    clang \
    llvm \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    docker.io \
    gcc-multilib \
    g++-multilib

# Install AFL++
print_status "Installing AFL++..."
if [ ! -d "AFLplusplus" ]; then
    git clone https://github.com/AFLplusplus/AFLplusplus.git
    cd AFLplusplus
    make all
    sudo make install
    cd ..
    print_status "AFL++ installed successfully!"
else
    print_warning "AFL++ directory already exists, skipping..."
fi

# Verify AFL++ installation
if command -v afl-fuzz &> /dev/null; then
    print_status "AFL++ is installed: $(afl-fuzz -h | head -1)"
else
    print_error "AFL++ installation failed!"
    exit 1
fi

# Install QEMU mode for binary-only fuzzing
print_status "Building AFL++ QEMU mode..."
cd AFLplusplus/qemu_mode
./build_qemu_support.sh || print_warning "QEMU mode build had issues, but may still work"
cd ../..

# Create Python virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv ~/fuzzing-project/venv
source ~/fuzzing-project/venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python dependencies
print_status "Installing Python packages..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install \
    numpy \
    matplotlib \
    pandas \
    scipy \
    scikit-learn \
    gym \
    stable-baselines3 \
    tensorboard \
    psutil \
    pytest

# Download OpenSSL 1.1.1f (test binary)
print_status "Downloading OpenSSL 1.1.1f..."
cd ~/fuzzing-project/binaries
if [ ! -f "openssl-1.1.1f.tar.gz" ]; then
    wget https://www.openssl.org/source/openssl-1.1.1f.tar.gz
    tar -xzf openssl-1.1.1f.tar.gz
    print_status "OpenSSL source downloaded and extracted"
else
    print_warning "OpenSSL already downloaded"
fi

# Compile OpenSSL for fuzzing
print_status "Compiling OpenSSL..."
cd openssl-1.1.1f
if [ ! -f "apps/openssl" ]; then
    ./config no-shared
    make -j$(nproc)
    print_status "OpenSSL compiled successfully!"
else
    print_warning "OpenSSL already compiled"
fi

# Create sample input corpus
print_status "Creating initial input corpus..."
cd ~/fuzzing-project/afl-workdir/input
echo "GET / HTTP/1.0" > http_request.txt
echo "test" > test1.txt
echo "fuzzing" > test2.txt
openssl rand 16 > random1.bin
openssl rand 32 > random2.bin

# Create configuration file
print_status "Creating configuration file..."
cat > ~/fuzzing-project/config.yaml << 'EOF'
# AFL++ + PPO Configuration

# AFL++ Settings
afl:
  timeout: 1000
  memory_limit: "none"
  qemu_mode: true
  persistent_mode: true
  defer_forkserver: true
  
# PPO Settings
ppo:
  learning_rate: 0.0003
  gamma: 0.99
  gae_lambda: 0.95
  clip_range: 0.2
  batch_size: 64
  n_epochs: 10
  ent_coef: 0.01
  vf_coef: 0.5
  max_grad_norm: 0.5
  
# Experiment Settings
experiment:
  duration_hours: 8
  metrics_interval: 300  # seconds
  checkpoint_interval: 3600  # seconds
  
# Target Settings
target:
  binary: "binaries/openssl-1.1.1f/apps/openssl"
  args: ["s_server", "@@"]
  input_dir: "afl-workdir/input"
  output_dir: "afl-workdir/output"
EOF

# Create system info script
print_status "Creating system information script..."
cat > ~/fuzzing-project/system_info.sh << 'EOF'
#!/bin/bash
echo "System Information for Fuzzing Experiments"
echo "==========================================="
echo ""
echo "OS: $(uname -s) $(uname -r)"
echo "Distribution: $(lsb_release -d | cut -f2)"
echo "CPU: $(lscpu | grep "Model name" | cut -d: -f2 | xargs)"
echo "CPU Cores: $(nproc)"
echo "RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "AFL++ Version: $(afl-fuzz -h 2>&1 | head -1)"
echo "Python Version: $(python3 --version)"
echo "PyTorch Version: $(python3 -c 'import torch; print(torch.__version__)')"
echo ""
EOF
chmod +x ~/fuzzing-project/system_info.sh

# Create quick start script
print_status "Creating quick start script..."
cat > ~/fuzzing-project/start_fuzzing.sh << 'EOF'
#!/bin/bash
# Quick start script for AFL++ fuzzing

source ~/fuzzing-project/venv/bin/activate

echo "Starting AFL++ fuzzing..."
echo "Target: binaries/openssl-1.1.1f/apps/openssl"
echo "Input: afl-workdir/input"
echo "Output: afl-workdir/output"
echo ""

afl-fuzz -i afl-workdir/input \
         -o afl-workdir/output \
         -Q \
         -m none \
         -- binaries/openssl-1.1.1f/apps/openssl s_server @@
EOF
chmod +x ~/fuzzing-project/start_fuzzing.sh

# Final setup
print_status "Running final checks..."
cd ~/fuzzing-project

# Display system information
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
./system_info.sh
echo ""
echo "Project Directory: ~/fuzzing-project"
echo "Virtual Environment: ~/fuzzing-project/venv"
echo ""
echo "To activate the environment:"
echo "  source ~/fuzzing-project/venv/bin/activate"
echo ""
echo "To start basic AFL++ fuzzing:"
echo "  cd ~/fuzzing-project"
echo "  ./start_fuzzing.sh"
echo ""
print_status "Setup script completed successfully!"
