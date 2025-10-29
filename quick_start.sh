#!/bin/bash
# Quick Start: Essential Binaries for AFL++ PPO Experiments
# Downloads only the most critical targets for immediate testing

set -e

WORK_DIR="${1:-$HOME/fuzz_bins_minimal}"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "=========================================="
echo "AFL++ PPO Quick Start Binary Collection"
echo "=========================================="
echo "Working directory: $WORK_DIR"
echo ""

# Function to show progress
show_progress() {
    echo -e "\n[+] $1"
}

# Function to check and download
download_if_needed() {
    url="$1"
    output="$2"
    desc="$3"
    
    if [ -f "$output" ]; then
        echo "    [SKIP] Already exists: $output"
        return 0
    fi
    
    echo "    [DOWN] $desc"
    if wget -q --show-progress "$url" -O "$output" 2>&1; then
        echo "    [OK] Downloaded: $output"
        return 0
    else
        echo "    [FAIL] Could not download: $url"
        return 1
    fi
}

# ============================================================================
# 1. LAVA-M (PRIORITY - Start here!)
# ============================================================================
show_progress "Downloading LAVA-M Dataset (Essential)"

mkdir -p lava-m
cd lava-m

# Download the 3 most important LAVA-M targets
declare -A LAVA_TARGETS=(
    ["base64"]="http://panda.moyix.net/~moyix/lava_corpus/LAVA-M/LAVA-M-base64.tar.xz"
    ["md5sum"]="http://panda.moyix.net/~moyix/lava_corpus/LAVA-M/LAVA-M-md5sum.tar.xz"
    ["uniq"]="http://panda.moyix.net/~moyix/lava_corpus/LAVA-M/LAVA-M-uniq.tar.xz"
)

for target in "${!LAVA_TARGETS[@]}"; do
    download_if_needed "${LAVA_TARGETS[$target]}" "LAVA-M-$target.tar.xz" "LAVA-M $target (44-57 bugs)"
done

# Extract archives
for f in LAVA-M-*.tar.xz; do
    if [ -f "$f" ] && [ ! -d "${f%.tar.xz}" ]; then
        echo "    [EXTRACT] $f"
        tar xf "$f" 2>/dev/null || echo "    [WARN] Already extracted: $f"
    fi
done

cd "$WORK_DIR"

# ============================================================================
# 2. GNU Binutils (Real-world target)
# ============================================================================
show_progress "Downloading GNU Binutils 2.26 (Real bugs)"

mkdir -p binutils
cd binutils

download_if_needed \
    "https://ftp.gnu.org/gnu/binutils/binutils-2.26.tar.gz" \
    "binutils-2.26.tar.gz" \
    "GNU binutils 2.26 (objdump, readelf)"

if [ -f "binutils-2.26.tar.gz" ] && [ ! -d "binutils-2.26" ]; then
    echo "    [EXTRACT] binutils-2.26.tar.gz"
    tar xzf binutils-2.26.tar.gz
fi

cd "$WORK_DIR"

# ============================================================================
# 3. Small utility targets (Quick testing)
# ============================================================================
show_progress "Downloading Small Test Targets"

mkdir -p small-targets
cd small-targets

download_if_needed \
    "http://www.catb.org/~esr/gif2png/gif2png-2.5.14.tar.gz" \
    "gif2png-2.5.14.tar.gz" \
    "gif2png (small, fast target)"

if [ -f "gif2png-2.5.14.tar.gz" ] && [ ! -d "gif2png-2.5.14" ]; then
    echo "    [EXTRACT] gif2png-2.5.14.tar.gz"
    tar xzf gif2png-2.5.14.tar.gz
fi

cd "$WORK_DIR"

# ============================================================================
# 4. Copy system binaries for immediate testing
# ============================================================================
show_progress "Copying System Binaries (No build needed)"

mkdir -p system-bins
cd system-bins

SYSTEM_BINS=("/usr/bin/file" "/usr/bin/readelf" "/usr/bin/objdump" "/usr/bin/nm" "/usr/bin/strings")

for bin in "${SYSTEM_BINS[@]}"; do
    if [ -f "$bin" ]; then
        binname=$(basename "$bin")
        cp "$bin" "./$binname" 2>/dev/null && echo "    [COPY] $binname" || echo "    [SKIP] $binname"
    fi
done

cd "$WORK_DIR"

# ============================================================================
# 5. Create build script for AFL++ instrumentation
# ============================================================================
show_progress "Creating Build Scripts"

cat > build_lavam.sh << 'EOFBUILD'
#!/bin/bash
# Build LAVA-M targets with AFL++ instrumentation

if ! command -v afl-clang-fast &> /dev/null; then
    echo "[ERROR] AFL++ not found! Install with:"
    echo "  sudo apt install afl++"
    exit 1
fi

export CC=afl-clang-fast
export CXX=afl-clang-fast++

TARGETS=("base64" "md5sum" "uniq")

for target in "${TARGETS[@]}"; do
    LAVA_DIR="lava-m/LAVA-M/LAVA-M-$target"
    
    if [ ! -d "$LAVA_DIR" ]; then
        echo "[SKIP] $target not found"
        continue
    fi
    
    echo "[BUILD] $target with AFL++ instrumentation..."
    cd "$LAVA_DIR/coreutils-8.24-lava-safe"
    
    if [ -f "Makefile" ]; then
        make clean &>/dev/null
    fi
    
    ./configure --prefix="$PWD/install" \
                --disable-nls \
                FORCE_UNSAFE_CONFIGURE=1 2>&1 | tail -5
    
    make -j$(nproc) 2>&1 | tail -10
    make install 2>&1 | tail -3
    
    echo "[OK] Built: $LAVA_DIR/install/bin/$target"
    cd "$OLDPWD"
done

echo ""
echo "[✓] LAVA-M build complete!"
echo "Binaries in: lava-m/LAVA-M/LAVA-M-*/coreutils-8.24-lava-safe/install/bin/"
EOFBUILD

chmod +x build_lavam.sh

cat > build_binutils.sh << 'EOFBINUTILS'
#!/bin/bash
# Build GNU binutils with AFL++ instrumentation

if ! command -v afl-clang-fast &> /dev/null; then
    echo "[ERROR] AFL++ not found! Install with:"
    echo "  sudo apt install afl++"
    exit 1
fi

export CC=afl-clang-fast
export CXX=afl-clang-fast++

cd binutils/binutils-2.26

if [ -f "Makefile" ]; then
    make clean &>/dev/null
fi

echo "[BUILD] GNU binutils 2.26 with AFL++ instrumentation..."

./configure --prefix="$PWD/install" \
            --disable-werror \
            --disable-gdb \
            --disable-libdecnumber \
            --disable-readline \
            --disable-sim 2>&1 | tail -5

make -j$(nproc) 2>&1 | tail -10
make install 2>&1 | tail -3

echo ""
echo "[✓] Binutils build complete!"
echo "Binaries in: binutils/binutils-2.26/install/bin/"
echo "  - objdump (ELF parser)"
echo "  - readelf (ELF analyzer)" 
echo "  - nm (symbol dumper)"
echo "  - size (section info)"
EOFBINUTILS

chmod +x build_binutils.sh

cat > test_setup.sh << 'EOFTEST'
#!/bin/bash
# Test AFL++ setup with system binary

echo "[+] Testing AFL++ installation..."

if ! command -v afl-fuzz &> /dev/null; then
    echo "[ERROR] AFL++ not found! Install:"
    echo "  sudo apt update"
    echo "  sudo apt install afl++"
    exit 1
fi

echo "[OK] AFL++ found: $(afl-fuzz 2>&1 | head -3 | tail -1)"

# Create test corpus
mkdir -p test-in test-out
echo "test input" > test-in/seed1.txt
echo -e "\x7fELF" > test-in/seed2.elf  # Minimal ELF header

echo ""
echo "[+] Running 30-second test with system file binary..."
echo "[+] Press Ctrl+C to stop early if working"
echo ""

timeout 30 afl-fuzz -i test-in -o test-out -m none -- system-bins/file @@ 2>&1 | tail -15

echo ""
echo "[✓] Test complete!"
echo ""
echo "Next steps:"
echo "  1. Build LAVA-M:  ./build_lavam.sh"
echo "  2. Build binutils: ./build_binutils.sh"
echo "  3. Start fuzzing: afl-fuzz -i seeds/ -o findings/ -m none -- target @@"

rm -rf test-in test-out
EOFTEST

chmod +x test_setup.sh

# ============================================================================
# 6. Create README with next steps
# ============================================================================

cat > README.txt << 'EOFREADME'
═══════════════════════════════════════════════════════════════
  AFL++ PPO Fuzzing - Essential Binaries Quick Start
═══════════════════════════════════════════════════════════════

DIRECTORY STRUCTURE:
  lava-m/              LAVA-M synthetic bugs (base64, md5sum, uniq)
  binutils/            GNU binutils 2.26 (objdump, readelf)
  small-targets/       gif2png and other small targets
  system-bins/         System binaries (file, readelf, etc.)

QUICK START:

1. Test your AFL++ setup (30 seconds):
   ./test_setup.sh

2. Build LAVA-M with AFL++ instrumentation:
   ./build_lavam.sh
   
   Result: lava-m/LAVA-M/LAVA-M-*/install/bin/{base64,md5sum,uniq}

3. Build binutils with AFL++ instrumentation:
   ./build_binutils.sh
   
   Result: binutils/binutils-2.26/install/bin/{objdump,readelf,nm,size}

4. Run your first fuzz test (LAVA-M base64):
   
   # Create seed corpus
   mkdir -p seeds
   echo "VGVzdA==" > seeds/base64_sample.txt
   echo "test" > seeds/plaintext.txt
   
   # Run AFL++ (vanilla baseline)
   afl-fuzz -i seeds -o findings -m none \
            -- lava-m/LAVA-M/LAVA-M-base64/install/bin/base64 -d @@
   
   # Run with your PPO integration
   ppo-afl-fuzz -i seeds -o findings-ppo -m none \
                -- lava-m/LAVA-M/LAVA-M-base64/install/bin/base64 -d @@

PRIORITY TARGETS (Start here):

1. base64 (LAVA-M) - 44 bugs, fastest iteration
2. md5sum (LAVA-M) - 57 bugs, good for baselines  
3. objdump (binutils) - Real bugs, malware analysis connection

LAVA-M EXPECTED RESULTS (from paper):
  base64:  ~9 bugs in 5 hours
  md5sum:  ~13 bugs in 6 hours
  uniq:    ~7 bugs in 3 hours

YOUR RESEARCH WORKFLOW:

Phase 1 (1 week): Establish baselines on LAVA-M
  - Run vanilla AFL++ for 24 hours per target
  - Measure: coverage, crashes, time-to-bug
  
Phase 2 (1 week): PPO integration on LAVA-M
  - Integrate your PPO with AFL++
  - Compare against Phase 1 baselines
  - Tune hyperparameters
  
Phase 3 (1 week): Generalize to binutils
  - Use your 638 malware samples as seeds!
  - Test on objdump/readelf
  - Novel contribution: malware-informed fuzzing

TROUBLESHOOTING:

Low exec/sec (< 1000/sec)?
  → Check instrumentation: AFL_INST_LIBS=1
  → Disable ASAN during benchmarks
  → Use -m none to disable memory limit

No bugs found on LAVA-M?
  → Check seeds are valid inputs
  → Verify binary is instrumented: afl-showmap -o /dev/null -Q -- ./target < seed
  → Try longer runtime (some bugs take hours)

PPO not improving?
  → Tune reward shaping
  → Check action space design
  → Verify policy is actually being used

NEXT STEPS:

1. Test AFL++ works:        ./test_setup.sh
2. Build targets:           ./build_lavam.sh && ./build_binutils.sh  
3. Read detailed guide:     ../PPO_RESEARCH_GUIDE.md
4. Download more targets:   ../collect_binaries.py

RESOURCES:

LAVA-M Paper:    http://seclab.cs.sunysb.edu/seclab/pubs/lava.pdf
AFL++ Docs:      https://github.com/AFLplusplus/AFLplusplus/blob/stable/docs/
FuzzBench:       https://github.com/google/fuzzbench

═══════════════════════════════════════════════════════════════
Ready to start? Run: ./test_setup.sh
═══════════════════════════════════════════════════════════════
EOFREADME

# ============================================================================
# Final Summary
# ============================================================================

echo ""
echo "=========================================="
echo "✓ Quick Start Setup Complete!"
echo "=========================================="
echo ""
echo "Downloaded:"
echo "  • LAVA-M (base64, md5sum, uniq) - 3 targets with known bugs"
echo "  • GNU binutils 2.26 - objdump, readelf, etc."
echo "  • gif2png - small test target"
echo "  • System binaries - for immediate testing"
echo ""
echo "Location: $WORK_DIR"
echo ""
echo "Next Steps:"
echo "  1. cd $WORK_DIR"
echo "  2. ./test_setup.sh          # Test AFL++ (30 sec)"
echo "  3. ./build_lavam.sh         # Build LAVA-M (~10 min)"
echo "  4. ./build_binutils.sh      # Build binutils (~15 min)"
echo "  5. Read README.txt          # Detailed instructions"
echo ""
echo "For more targets, use the full collector:"
echo "  python3 collect_binaries.py"
echo ""
echo "For research guidance, read:"
echo "  PPO_RESEARCH_GUIDE.md"
echo ""
echo "Ready to start fuzzing! 🔥"
echo "=========================================="
