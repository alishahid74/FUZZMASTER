#!/bin/bash
# AFL++ PPO Fuzzing Binary Collection Script
# Collects binaries from major fuzzing benchmarks for research experiments

set -e

WORK_DIR="$HOME/fuzz_binaries"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "[+] Starting binary collection for AFL++ PPO experiments..."
echo "[+] Working directory: $WORK_DIR"

# ============================================================================
# 1. LAVA-M Dataset (Most Important - Synthetic Bugs)
# ============================================================================
echo ""
echo "=== [1/7] Downloading LAVA-M Binaries ==="
mkdir -p lava-m
cd lava-m

# LAVA-M has 4 instrumented programs with known bugs
for prog in base64 md5sum uniq who; do
    echo "[+] Fetching LAVA-M $prog..."
    
    # Try primary source
    if ! wget -q --show-progress "http://panda.moyix.net/~moyix/lava_corpus/LAVA-M/LAVA-M-$prog.tar.xz" 2>/dev/null; then
        echo "    [!] Primary source failed, trying mirror..."
        # Alternative: build from source
        if [ ! -d "lava" ]; then
            git clone https://github.com/panda-re/lava.git --depth 1
        fi
    fi
done

# Extract if downloaded
for archive in *.tar.xz; do
    [ -e "$archive" ] && tar xf "$archive"
done

cd "$WORK_DIR"

# ============================================================================
# 2. FuzzBench Benchmark Targets
# ============================================================================
echo ""
echo "=== [2/7] Setting up FuzzBench Targets ==="
mkdir -p fuzzbench
cd fuzzbench

# Clone FuzzBench repo for build configurations
if [ ! -d "fuzzbench" ]; then
    git clone https://github.com/google/fuzzbench.git --depth 1
    echo "[+] FuzzBench cloned - targets in: fuzzbench/benchmarks/"
fi

# List of key FuzzBench targets to build
FUZZBENCH_TARGETS=(
    "libpng-1.2.56"
    "libjpeg-turbo-07-2017"
    "libxml2-v2.9.2"
    "libpcap_fuzz_both"
    "openssl_x509"
    "sqlite3_ossfuzz"
    "freetype2-2017"
    "harfbuzz-1.3.2"
)

echo "[+] FuzzBench targets available: ${FUZZBENCH_TARGETS[@]}"
echo "[+] Build with: cd fuzzbench/benchmarks/<target> && make"

cd "$WORK_DIR"

# ============================================================================
# 3. Google Fuzzer Test Suite
# ============================================================================
echo ""
echo "=== [3/7] Cloning Fuzzer Test Suite ==="
if [ ! -d "fuzzer-test-suite" ]; then
    git clone https://github.com/google/fuzzer-test-suite.git --depth 1
    echo "[+] Fuzzer test suite cloned - 20+ targets available"
    echo "[+] Targets in: fuzzer-test-suite/*/build.sh"
fi

# ============================================================================
# 4. GNU Binutils (objdump, readelf, etc.)
# ============================================================================
echo ""
echo "=== [4/7] Downloading GNU Binutils ==="
mkdir -p binutils
cd binutils

# Download multiple versions for variety
BINUTILS_VERSIONS=("2.26" "2.27" "2.28" "2.30" "2.35")

for ver in "${BINUTILS_VERSIONS[@]}"; do
    archive="binutils-$ver.tar.gz"
    if [ ! -f "$archive" ]; then
        echo "[+] Downloading binutils-$ver..."
        wget -q --show-progress "https://ftp.gnu.org/gnu/binutils/$archive" || \
        wget -q --show-progress "http://mirror.keystealth.org/gnu/binutils/$archive" || \
        echo "    [!] Failed to download binutils-$ver"
    fi
done

cd "$WORK_DIR"

# ============================================================================
# 5. Common Target Binaries (Quick Downloads)
# ============================================================================
echo ""
echo "=== [5/7] Downloading Common Fuzz Targets ==="
mkdir -p common-targets
cd common-targets

# libpng
echo "[+] Downloading libpng..."
wget -q --show-progress "https://download.sourceforge.net/libpng/libpng-1.6.37.tar.gz" || true

# libjpeg-turbo
echo "[+] Downloading libjpeg-turbo..."
wget -q --show-progress "https://github.com/libjpeg-turbo/libjpeg-turbo/archive/refs/tags/2.0.6.tar.gz" -O libjpeg-turbo-2.0.6.tar.gz || true

# tcpdump/libpcap
echo "[+] Downloading tcpdump/libpcap..."
wget -q --show-progress "https://www.tcpdump.org/release/tcpdump-4.99.1.tar.gz" || true
wget -q --show-progress "https://www.tcpdump.org/release/libpcap-1.10.1.tar.gz" || true

# sqlite
echo "[+] Downloading sqlite..."
wget -q --show-progress "https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz" || true

# gif2png (small, good starter target)
echo "[+] Downloading gif2png..."
wget -q --show-progress "http://www.catb.org/~esr/gif2png/gif2png-2.5.14.tar.gz" || true

cd "$WORK_DIR"

# ============================================================================
# 6. Pre-built Binaries from Debian Packages (Quick Testing)
# ============================================================================
echo ""
echo "=== [6/7] Extracting Binaries from System Packages ==="
mkdir -p debian-bins
cd debian-bins

# Copy common system binaries for quick testing
SYSTEM_BINS=(
    "/usr/bin/file"
    "/usr/bin/readelf"
    "/usr/bin/objdump"
    "/usr/bin/nm"
    "/usr/bin/strings"
    "/usr/bin/size"
    "/usr/bin/sqlite3"
    "/usr/bin/tcpdump"
)

for bin in "${SYSTEM_BINS[@]}"; do
    if [ -f "$bin" ]; then
        binname=$(basename "$bin")
        cp "$bin" "./$binname-system" 2>/dev/null || true
        echo "[+] Copied: $binname"
    fi
done

cd "$WORK_DIR"

# ============================================================================
# 7. Create AFL++ Build Script for Instrumentation
# ============================================================================
echo ""
echo "=== [7/7] Creating AFL++ Build Helper Scripts ==="

cat > build_with_afl.sh << 'EOF'
#!/bin/bash
# Helper script to build targets with AFL++ instrumentation
# Usage: ./build_with_afl.sh <source_dir> <output_name>

if [ $# -lt 2 ]; then
    echo "Usage: $0 <source_dir> <output_name>"
    exit 1
fi

SOURCE_DIR="$1"
OUTPUT_NAME="$2"
BUILD_DIR="$WORK_DIR/afl-builds/$OUTPUT_NAME"

export CC="afl-clang-fast"
export CXX="afl-clang-fast++"
export AFL_USE_ASAN=1  # Optional: enable ASAN

mkdir -p "$BUILD_DIR"
cd "$SOURCE_DIR"

if [ -f "configure" ]; then
    ./configure --prefix="$BUILD_DIR"
    make clean
    make -j$(nproc)
    make install
elif [ -f "CMakeLists.txt" ]; then
    mkdir -p build && cd build
    cmake .. -DCMAKE_INSTALL_PREFIX="$BUILD_DIR"
    make -j$(nproc)
    make install
elif [ -f "Makefile" ]; then
    make clean
    make -j$(nproc)
    cp -r . "$BUILD_DIR/"
else
    echo "Unknown build system"
    exit 1
fi

echo "[+] Built: $OUTPUT_NAME -> $BUILD_DIR"
EOF

chmod +x build_with_afl.sh

# Create quick-build script for LAVA-M
cat > build_lavam.sh << 'EOF'
#!/bin/bash
# Build LAVA-M targets with AFL++ instrumentation
LAVA_DIR="$WORK_DIR/lava-m"
cd "$LAVA_DIR"

export CC=afl-clang-fast
export CXX=afl-clang-fast++

for prog in base64 md5sum uniq who; do
    if [ -d "LAVA-M/LAVA-M-$prog" ]; then
        echo "[+] Building $prog with AFL++..."
        cd "LAVA-M/LAVA-M-$prog"
        ./configure --prefix="$LAVA_DIR/instrumented/$prog"
        make clean && make -j$(nproc)
        make install
        cd "$LAVA_DIR"
    fi
done
EOF

chmod +x build_lavam.sh

# Create binutils build script
cat > build_binutils.sh << 'EOF'
#!/bin/bash
# Build binutils with AFL++ instrumentation
BINUTILS_DIR="$WORK_DIR/binutils"
cd "$BINUTILS_DIR"

export CC=afl-clang-fast
export CXX=afl-clang-fast++

for archive in binutils-*.tar.gz; do
    [ -e "$archive" ] || continue
    
    version=$(echo "$archive" | sed 's/binutils-\(.*\)\.tar\.gz/\1/')
    echo "[+] Building binutils-$version..."
    
    tar xzf "$archive"
    cd "binutils-$version"
    
    ./configure --prefix="$BINUTILS_DIR/afl-$version" \
                --disable-werror \
                --disable-gdb \
                --disable-libdecnumber \
                --disable-readline \
                --disable-sim
    
    make -j$(nproc)
    make install
    
    cd "$BINUTILS_DIR"
done
EOF

chmod +x build_binutils.sh

# ============================================================================
# Summary and Quick-Start Guide
# ============================================================================

cat > README.md << 'EOFREADME'
# AFL++ PPO Fuzzing Binary Collection

## Directory Structure
```
fuzz_binaries/
├── lava-m/              # LAVA-M synthetic bugs (base64, md5sum, uniq, who)
├── fuzzbench/           # FuzzBench targets (libpng, libjpeg, libxml2, etc.)
├── fuzzer-test-suite/   # Google's 20+ fuzzing targets
├── binutils/            # GNU binutils sources (objdump, readelf, etc.)
├── common-targets/      # libpng, sqlite, tcpdump, gif2png sources
├── debian-bins/         # System binaries for quick testing
└── build_*.sh          # AFL++ build helper scripts
```

## Quick Start

### 1. Pre-built Binaries (Immediate Testing)
```bash
cd debian-bins/
# Use these for quick AFL++ tests (not instrumented)
ls -lh *-system
```

### 2. Build LAVA-M (Recommended First Step)
```bash
./build_lavam.sh
# Instrumented binaries in: lava-m/instrumented/*/bin/
```

### 3. Build GNU Binutils
```bash
./build_binutils.sh
# Instrumented binaries in: binutils/afl-*/bin/
```

### 4. Build Custom Target
```bash
./build_with_afl.sh <source_dir> <output_name>
```

## Recommended Targets for PPO Experiments

### Small/Fast (Quick iteration for RL training):
- **gif2png** - Simple image converter (~10KB input)
- **LAVA-M base64** - Base64 encoder with known bugs
- **file** - File type identifier

### Medium (Balanced complexity):
- **objdump** - ELF binary parser
- **readelf** - ELF binary analyzer
- **libpng** - PNG image parser
- **sqlite3** - SQL parser

### Large/Complex (Challenging targets):
- **tcpdump** - Network packet parser
- **libxml2** - XML parser
- **tshark** - Network protocol analyzer

## LAVA-M Benchmark Stats
Target   | LOC    | DUAs | Bugs | Time(s)
---------|--------|------|------|--------
base64   | 10809  | 631  | 17518| 16
md5sum   | 10809  | 631  | 17518| 16  
uniq     | 10809  | 631  | 17518| 16
who      | 10809  | 631  | 17518| 16
readelf  | 21052  | 3849 | 276367| 354
bash     | 98871  | 3832 | 447645| 153
tshark   | 2186252| 9853 | 1240777| 542

## AFL++ PPO Integration Notes

### Running with your SymbolicHunter/PPO setup:
```bash
# Basic AFL++ run
afl-fuzz -i seeds/ -o findings/ -m none -- ./target @@

# With PPO integration (your setup)
afl-fuzz -i seeds/ -o findings/ -m none -p ppo -- ./target @@
```

### Corpus Generation Tips:
1. LAVA-M comes with seed inputs
2. FuzzBench targets include corpus in benchmarks/
3. For binutils: use small ELF files as seeds
4. For image targets: use minimal valid images

### Performance Testing:
- Start with LAVA-M for reproducibility
- Use binutils for real-world complexity
- FuzzBench targets for paper comparisons

## Building from Source (Manual)

### Example: libpng with AFL++
```bash
cd common-targets/
tar xzf libpng-1.6.37.tar.gz
cd libpng-1.6.37

export CC=afl-clang-fast
export CXX=afl-clang-fast++

./configure --prefix=$PWD/install
make -j$(nproc)
make install
```

### Example: sqlite with AFL++
```bash
cd common-targets/
tar xzf sqlite-autoconf-3420000.tar.gz
cd sqlite-autoconf-3420000

export CC=afl-clang-fast
./configure --prefix=$PWD/install
make -j$(nproc)
make install
```

## Resources
- LAVA-M Paper: http://seclab.cs.sunysb.edu/seclab/pubs/lava.pdf
- FuzzBench: https://github.com/google/fuzzbench
- Fuzzer Test Suite: https://github.com/google/fuzzer-test-suite
- AFL++ Docs: https://github.com/AFLplusplus/AFLplusplus

## Notes for PPO Experiments
- **Reproducibility**: Use LAVA-M (known bugs, fixed seeds)
- **Baselines**: Compare against standard AFL++ on same targets
- **Metrics**: Track exec/s, unique crashes, time-to-bug
- **Dataset**: Use 638 malware samples + these benchmarks
EOFREADME

echo ""
echo "============================================================================"
echo "[✓] Binary Collection Complete!"
echo "============================================================================"
echo ""
echo "Summary:"
echo "  - LAVA-M dataset:      $WORK_DIR/lava-m/"
echo "  - FuzzBench targets:   $WORK_DIR/fuzzbench/"
echo "  - Fuzzer test suite:   $WORK_DIR/fuzzer-test-suite/"
echo "  - GNU binutils:        $WORK_DIR/binutils/"
echo "  - Common targets:      $WORK_DIR/common-targets/"
echo "  - Quick test bins:     $WORK_DIR/debian-bins/"
echo ""
echo "Next Steps:"
echo "  1. Read the guide:     cat $WORK_DIR/README.md"
echo "  2. Build LAVA-M:       cd $WORK_DIR && ./build_lavam.sh"
echo "  3. Build binutils:     cd $WORK_DIR && ./build_binutils.sh"
echo ""
echo "For your PPO experiments, start with LAVA-M for reproducible baselines!"
echo "============================================================================"
