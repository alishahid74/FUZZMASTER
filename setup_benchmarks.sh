#!/bin/bash
# Benchmark Setup Script
# Downloads and compiles multiple benchmark programs for fuzzing

set -e

PROJECT_ROOT="${1:-$HOME/fuzzing-project}"
BINARIES_DIR="$PROJECT_ROOT/binaries"

echo "======================================"
echo "Benchmark Setup Script"
echo "======================================"
echo "Project Root: $PROJECT_ROOT"
echo "Binaries Dir: $BINARIES_DIR"
echo ""

# Create directories
mkdir -p "$BINARIES_DIR"
cd "$BINARIES_DIR"

# Function to check if AFL++ is available
check_afl() {
    if ! command -v afl-gcc &> /dev/null; then
        echo "ERROR: AFL++ not found. Please install AFL++ first."
        exit 1
    fi
    echo "✓ AFL++ found: $(which afl-gcc)"
}

# Function to download and build OpenSSL
setup_openssl() {
    echo ""
    echo "=== Setting up OpenSSL 1.1.1f ==="
    
    if [ -f "openssl-1.1.1f/apps/openssl" ]; then
        echo "✓ OpenSSL already built"
        return 0
    fi
    
    if [ ! -d "openssl-1.1.1f" ]; then
        echo "Downloading OpenSSL 1.1.1f..."
        wget -q https://www.openssl.org/source/openssl-1.1.1f.tar.gz
        tar -xzf openssl-1.1.1f.tar.gz
        rm openssl-1.1.1f.tar.gz
    fi
    
    cd openssl-1.1.1f
    echo "Configuring OpenSSL..."
    CC=afl-gcc ./config no-shared --prefix=$(pwd)/install
    
    echo "Building OpenSSL (this may take a while)..."
    make -j$(nproc) 2>&1 | tee build.log
    
    if [ -f "apps/openssl" ]; then
        echo "✓ OpenSSL built successfully"
    else
        echo "✗ OpenSSL build failed"
        return 1
    fi
    
    cd ..
}

# Function to download and build GNU binutils (readelf, objdump)
setup_binutils() {
    echo ""
    echo "=== Setting up GNU binutils ==="
    
    if [ -f "binutils-2.35/binutils/readelf" ]; then
        echo "✓ binutils already built"
        return 0
    fi
    
    if [ ! -d "binutils-2.35" ]; then
        echo "Downloading binutils 2.35..."
        wget -q https://ftp.gnu.org/gnu/binutils/binutils-2.35.tar.xz
        tar -xf binutils-2.35.tar.xz
        rm binutils-2.35.tar.xz
    fi
    
    cd binutils-2.35
    echo "Configuring binutils..."
    CC=afl-gcc ./configure --disable-werror --prefix=$(pwd)/install
    
    echo "Building binutils..."
    make -j$(nproc) 2>&1 | tee build.log
    
    if [ -f "binutils/readelf" ]; then
        echo "✓ binutils built successfully"
        # Create symlink for easy access
        mkdir -p ../binutils
        ln -sf $(pwd)/binutils/readelf ../binutils/readelf
        ln -sf $(pwd)/binutils/objdump ../binutils/objdump
    else
        echo "✗ binutils build failed"
        return 1
    fi
    
    cd ..
}

# Function to download and build tcpdump
setup_tcpdump() {
    echo ""
    echo "=== Setting up tcpdump ==="
    
    if [ -f "tcpdump-4.9.3/tcpdump" ]; then
        echo "✓ tcpdump already built"
        return 0
    fi
    
    # First build libpcap
    if [ ! -d "libpcap-1.9.1" ]; then
        echo "Downloading libpcap..."
        wget -q https://www.tcpdump.org/release/libpcap-1.9.1.tar.gz
        tar -xzf libpcap-1.9.1.tar.gz
        rm libpcap-1.9.1.tar.gz
    fi
    
    cd libpcap-1.9.1
    if [ ! -f "libpcap.a" ]; then
        echo "Building libpcap..."
        CC=afl-gcc ./configure --disable-shared
        make -j$(nproc) 2>&1 | tee build.log
    fi
    cd ..
    
    # Now build tcpdump
    if [ ! -d "tcpdump-4.9.3" ]; then
        echo "Downloading tcpdump..."
        wget -q https://www.tcpdump.org/release/tcpdump-4.9.3.tar.gz
        tar -xzf tcpdump-4.9.3.tar.gz
        rm tcpdump-4.9.3.tar.gz
    fi
    
    cd tcpdump-4.9.3
    echo "Configuring tcpdump..."
    CC=afl-gcc CFLAGS="-I$(pwd)/../libpcap-1.9.1" LDFLAGS="-L$(pwd)/../libpcap-1.9.1" ./configure
    
    echo "Building tcpdump..."
    make -j$(nproc) 2>&1 | tee build.log
    
    if [ -f "tcpdump" ]; then
        echo "✓ tcpdump built successfully"
        mkdir -p ../tcpdump
        ln -sf $(pwd)/tcpdump ../tcpdump/tcpdump
    else
        echo "✗ tcpdump build failed"
        return 1
    fi
    
    cd ..
}

# Function to download and build SQLite
setup_sqlite() {
    echo ""
    echo "=== Setting up SQLite ==="
    
    if [ -f "sqlite-autoconf-3330000/sqlite3" ]; then
        echo "✓ SQLite already built"
        return 0
    fi
    
    if [ ! -d "sqlite-autoconf-3330000" ]; then
        echo "Downloading SQLite..."
        wget -q https://www.sqlite.org/2020/sqlite-autoconf-3330000.tar.gz
        tar -xzf sqlite-autoconf-3330000.tar.gz
        rm sqlite-autoconf-3330000.tar.gz
    fi
    
    cd sqlite-autoconf-3330000
    echo "Configuring SQLite..."
    CC=afl-gcc ./configure --prefix=$(pwd)/install
    
    echo "Building SQLite..."
    make -j$(nproc) 2>&1 | tee build.log
    
    if [ -f "sqlite3" ]; then
        echo "✓ SQLite built successfully"
        mkdir -p ../sqlite
        ln -sf $(pwd)/sqlite3 ../sqlite/sqlite3
    else
        echo "✗ SQLite build failed"
        return 1
    fi
    
    cd ..
}

# Function to download LAVA-M dataset
setup_lava_m() {
    echo ""
    echo "=== Setting up LAVA-M dataset ==="
    
    if [ -d "lava-m" ]; then
        echo "✓ LAVA-M already downloaded"
        return 0
    fi
    
    echo "Downloading LAVA-M dataset..."
    echo "NOTE: LAVA-M is large. Using pre-built binaries if available."
    
    mkdir -p lava-m
    cd lava-m
    
    # Download LAVA-M binaries (if available)
    # Otherwise, build from source
    echo "For LAVA-M, please download from:"
    echo "  http://panda.moyix.net/~moyix/lava_corpus.tar.xz"
    echo "Or clone from: https://github.com/panda-re/lava"
    
    cd ..
}

# Function to create seed corpus directories
setup_seeds() {
    echo ""
    echo "=== Setting up seed corpus ==="
    
    SEEDS_DIR="$PROJECT_ROOT/afl-workdir/seeds"
    mkdir -p "$SEEDS_DIR"
    
    # OpenSSL seeds
    mkdir -p "$SEEDS_DIR/openssl"
    if [ ! -f "$SEEDS_DIR/openssl/ssl_hello.bin" ]; then
        echo "Creating OpenSSL seeds..."
        printf '\x16\x03\x01\x00\x05\x01\x00\x00\x01\x03' > "$SEEDS_DIR/openssl/ssl_hello.bin"
    fi
    
    # File seeds
    mkdir -p "$SEEDS_DIR/file"
    echo "Hello World" > "$SEEDS_DIR/file/text.txt"
    touch "$SEEDS_DIR/file/empty"
    
    # ELF seeds
    mkdir -p "$SEEDS_DIR/elf"
    if [ ! -f "$SEEDS_DIR/elf/minimal.elf" ]; then
        # Copy a system binary as seed
        cp /bin/ls "$SEEDS_DIR/elf/ls.elf" 2>/dev/null || true
    fi
    
    # PCAP seeds
    mkdir -p "$SEEDS_DIR/pcap"
    if [ ! -f "$SEEDS_DIR/pcap/minimal.pcap" ]; then
        echo "Creating minimal PCAP seed..."
        printf '\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00' > "$SEEDS_DIR/pcap/minimal.pcap"
    fi
    
    # SQL seeds
    mkdir -p "$SEEDS_DIR/sql"
    echo "CREATE TABLE test (id INT);" > "$SEEDS_DIR/sql/create.sql"
    echo "SELECT 1;" > "$SEEDS_DIR/sql/select.sql"
    
    echo "✓ Seed corpus created"
}

# Main execution
main() {
    echo "Starting benchmark setup..."
    echo ""
    
    # Check prerequisites
    check_afl
    
    # Track successes
    declare -a BUILT=()
    declare -a FAILED=()
    
    # Setup each benchmark
    if setup_openssl; then
        BUILT+=("openssl")
    else
        FAILED+=("openssl")
    fi
    
    if setup_binutils; then
        BUILT+=("binutils")
    else
        FAILED+=("binutils")
    fi
    
    if setup_tcpdump; then
        BUILT+=("tcpdump")
    else
        FAILED+=("tcpdump")
    fi
    
    if setup_sqlite; then
        BUILT+=("sqlite")
    else
        FAILED+=("sqlite")
    fi
    
    setup_lava_m  # This one is informational only
    
    # Setup seeds
    setup_seeds
    
    # Summary
    echo ""
    echo "======================================"
    echo "Setup Complete!"
    echo "======================================"
    echo ""
    
    if [ ${#BUILT[@]} -gt 0 ]; then
        echo "✓ Successfully built:"
        for bench in "${BUILT[@]}"; do
            echo "  - $bench"
        done
    fi
    
    if [ ${#FAILED[@]} -gt 0 ]; then
        echo ""
        echo "✗ Failed to build:"
        for bench in "${FAILED[@]}"; do
            echo "  - $bench"
        done
    fi
    
    echo ""
    echo "Next steps:"
    echo "1. Run benchmark_runner.py --list to see available benchmarks"
    echo "2. Run quick test: python benchmark_runner.py --duration 0.1"
    echo "3. Run full benchmarks: python benchmark_runner.py --duration 1.0"
    echo ""
}

# Run main
main
