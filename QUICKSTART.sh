#!/bin/bash
# QUICK START SCRIPT
# Run this after extracting the package

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         FUZZMASTER - Quick Start Installation                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "MASTER_AUTOMATIC_FRAMEWORK.py" ]; then
    echo "❌ Error: MASTER_AUTOMATIC_FRAMEWORK.py not found!"
    echo "Please run this script from the extracted package directory"
    exit 1
fi

echo "✓ Package extracted correctly"
echo ""

# Make scripts executable
echo "Making scripts executable..."
chmod +x *.py *.sh
echo "✓ Done"
echo ""

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Found: $PYTHON_VERSION"
else
    echo "❌ Python 3 not found! Please install Python 3.7+"
    exit 1
fi
echo ""

# Check AFL++
echo "Checking AFL++..."
if command -v afl-fuzz &> /dev/null; then
    AFL_VERSION=$(afl-fuzz --version 2>&1 | head -1)
    echo "✓ Found: $AFL_VERSION"
else
    echo "⚠ AFL++ not found!"
    echo "Install with:"
    echo "  git clone https://github.com/AFLplusplus/AFLplusplus.git"
    echo "  cd AFLplusplus && make && sudo make install"
fi
echo ""

# Check OpenSSL
echo "Checking OpenSSL binary..."
if [ -f "../binaries/openssl-1.1.1f/apps/openssl" ]; then
    echo "✓ Found: OpenSSL binary"
elif [ -f "binaries/openssl-1.1.1f/apps/openssl" ]; then
    echo "✓ Found: OpenSSL binary"
else
    echo "⚠ OpenSSL binary not found"
    echo "Expected: binaries/openssl-1.1.1f/apps/openssl"
fi
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q torch numpy pandas matplotlib seaborn colorama pyyaml 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Python dependencies installed"
else
    echo "⚠ Some dependencies may have failed to install"
    echo "Try: pip install torch numpy pandas matplotlib seaborn colorama pyyaml"
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 SETUP COMPLETE! 🎉                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📖 Quick Start:"
echo ""
echo "   1. Quick 30-minute test:"
echo "      python3 MASTER_AUTOMATIC_FRAMEWORK.py --quick"
echo ""
echo "   2. Standard 1-hour test (RECOMMENDED):"
echo "      python3 MASTER_AUTOMATIC_FRAMEWORK.py --standard"
echo ""
echo "   3. Intensive 2-hour research:"
echo "      python3 MASTER_AUTOMATIC_FRAMEWORK.py --intensive"
echo ""
echo "📚 Documentation:"
echo "   - Read README_START_HERE.md for overview"
echo "   - Read MASTER_INTEGRATION_GUIDE.md for details"
echo ""
echo "💡 Tip: Start with --quick to test everything works!"
echo ""
