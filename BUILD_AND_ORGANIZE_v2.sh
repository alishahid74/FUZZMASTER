#!/bin/bash
# Master Build & Organize Script (Auto-detection version)
# Automatically finds LAVA-M and binutils regardless of structure

set -e

FUZZ_DIR="$HOME/fuzz_binaries"
EXP_DIR="$HOME/FUZZING_EXPERIMENTS"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Master Build & Organize - AFL++ Fuzzing Setup v2          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will:"
echo "  1. Auto-detect LAVA-M location"
echo "  2. Build LAVA-M with AFL++"
echo "  3. Build binutils with AFL++"
echo "  4. Organize into separate experiment directories"
echo ""
echo "Source: $FUZZ_DIR"
echo "Target: $EXP_DIR"
echo ""

# Check AFL++ is installed
if ! command -v afl-clang-fast &> /dev/null; then
    echo "[ERROR] AFL++ not found!"
    echo ""
    echo "Install with:"
    echo "  sudo apt update"
    echo "  sudo apt install afl++"
    exit 1
fi

echo "[✓] AFL++ found: $(afl-fuzz --version 2>&1 | head -1)"

# ============================================================================
# Auto-detect LAVA-M location
# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Detecting LAVA-M location..."
echo "════════════════════════════════════════════════════════════════"

LAVA_LOCATIONS=(
    "$FUZZ_DIR/lava-m/lava/LAVA-M"
    "$FUZZ_DIR/lava-m/LAVA-M"
    "$FUZZ_DIR/lava/LAVA-M"
)

LAVA_BASE=""
for loc in "${LAVA_LOCATIONS[@]}"; do
    if [ -d "$loc" ]; then
        LAVA_BASE="$loc"
        echo "[✓] Found LAVA-M at: $LAVA_BASE"
        break
    fi
done

if [ -z "$LAVA_BASE" ]; then
    echo "[!] LAVA-M not found in standard locations"
    echo "Searched:"
    for loc in "${LAVA_LOCATIONS[@]}"; do
        echo "  - $loc"
    done
    echo ""
    echo "Checking what's in lava-m directory..."
    if [ -d "$FUZZ_DIR/lava-m" ]; then
        echo "Contents of $FUZZ_DIR/lava-m:"
        ls -la "$FUZZ_DIR/lava-m"
    fi
    echo ""
    echo "Continuing with binutils only..."
else
    # List available targets
    echo ""
    echo "Available LAVA-M targets:"
    ls -d "$LAVA_BASE"/LAVA-M-* 2>/dev/null | while read dir; do
        echo "  - $(basename $dir)"
    done
fi

# ============================================================================
# STEP 1: Build LAVA-M
# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "STEP 1: Building LAVA-M with AFL++"
echo "════════════════════════════════════════════════════════════════"

export CC=afl-clang-fast
export CXX=afl-clang-fast++

BUILT_TARGETS=()

if [ -n "$LAVA_BASE" ]; then
    cd "$LAVA_BASE"
    
    for target in base64 md5sum uniq who; do
        BUILD_DIR="LAVA-M-$target/coreutils-8.24-lava-safe"
        
        if [ ! -d "$BUILD_DIR" ]; then
            echo "[SKIP] $target - directory not found"
            continue
        fi
        
        echo ""
        echo "[BUILD] $target..."
        cd "$BUILD_DIR"
        
        # Clean
        make clean &>/dev/null || true
        
        # Configure
        echo "  [+] Configuring..."
        if ./configure --prefix="$PWD/install" \
                    --disable-nls \
                    FORCE_UNSAFE_CONFIGURE=1 \
                    >/dev/null 2>&1; then
            
            # Build
            echo "  [+] Compiling (may take 2-5 minutes)..."
            if make -j$(nproc) >/dev/null 2>&1; then
                
                # Install
                echo "  [+] Installing..."
                make install >/dev/null 2>&1
                
                if [ -f "install/bin/$target" ]; then
                    echo "  [✓] $target built successfully!"
                    BUILT_TARGETS+=("$target:$PWD/install/bin/$target")
                else
                    echo "  [✗] $target build failed (binary not found)"
                fi
            else
                echo "  [✗] $target compilation failed"
            fi
        else
            echo "  [✗] $target configure failed"
        fi
        
        cd "$LAVA_BASE"
    done
else
    echo "[SKIP] LAVA-M not found, skipping..."
fi

# ============================================================================
# STEP 2: Build Binutils
# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "STEP 2: Building GNU Binutils with AFL++"
echo "════════════════════════════════════════════════════════════════"

BINUTILS_DIR="$FUZZ_DIR/binutils"
BINUTILS_BUILT=""

if [ -d "$BINUTILS_DIR" ]; then
    cd "$BINUTILS_DIR"
    
    # Find first binutils archive
    for archive in binutils-*.tar.gz; do
        [ -e "$archive" ] || continue
        
        version=$(echo "$archive" | sed 's/binutils-\(.*\)\.tar\.gz/\1/')
        BUILD_DIR="binutils-$version"
        
        echo ""
        echo "[BUILD] binutils-$version..."
        
        # Extract if needed
        if [ ! -d "$BUILD_DIR" ]; then
            echo "  [+] Extracting..."
            tar xzf "$archive" 2>/dev/null
        fi
        
        cd "$BUILD_DIR"
        
        # Clean
        make clean &>/dev/null || true
        
        # Configure
        echo "  [+] Configuring..."
        if ./configure --prefix="$PWD/install" \
                    --disable-werror \
                    --disable-gdb \
                    --disable-libdecnumber \
                    --disable-readline \
                    --disable-sim \
                    >/dev/null 2>&1; then
            
            # Build
            echo "  [+] Compiling (may take 10-15 minutes)..."
            if make -j$(nproc) >/dev/null 2>&1; then
                
                # Install
                echo "  [+] Installing..."
                make install >/dev/null 2>&1
                
                if [ -f "install/bin/objdump" ]; then
                    echo "  [✓] binutils-$version built successfully!"
                    BINUTILS_BUILT="$PWD/install"
                else
                    echo "  [✗] binutils-$version build failed"
                fi
            else
                echo "  [✗] binutils-$version compilation failed"
            fi
        else
            echo "  [✗] binutils-$version configure failed"
        fi
        
        cd "$BINUTILS_DIR"
        
        # Only build first version for speed
        [ -n "$BINUTILS_BUILT" ] && break
    done
else
    echo "[SKIP] Binutils directory not found at: $BINUTILS_DIR"
fi

# ============================================================================
# STEP 3: Organize into Experiment Directories
# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "STEP 3: Organizing into Experiment Directories"
echo "════════════════════════════════════════════════════════════════"

mkdir -p "$EXP_DIR"
CREATED_EXPERIMENTS=()

# Function to create experiment directory
create_exp() {
    local name="$1"
    local binary="$2"
    local seed_type="$3"
    
    if [ ! -f "$binary" ]; then
        return 1
    fi
    
    local exp_dir="$EXP_DIR/$name"
    mkdir -p "$exp_dir"/{binary,seeds,findings}
    
    # Copy binary
    cp "$binary" "$exp_dir/binary/target"
    chmod +x "$exp_dir/binary/target"
    
    # Create seeds based on type
    case "$seed_type" in
        "text")
            echo "test input" > "$exp_dir/seeds/seed1.txt"
            echo "hello world" > "$exp_dir/seeds/seed2.txt"
            echo -e "line1\nline2\nline3" > "$exp_dir/seeds/seed3.txt"
            ;;
        "base64")
            echo "VGVzdA==" > "$exp_dir/seeds/seed1.b64"
            echo "SGVsbG8gV29ybGQ=" > "$exp_dir/seeds/seed2.b64"
            echo "Zm9vYmFy" > "$exp_dir/seeds/seed3.b64"
            ;;
        "elf")
            cp /bin/ls "$exp_dir/seeds/seed1.elf" 2>/dev/null || true
            cp /bin/cat "$exp_dir/seeds/seed2.elf" 2>/dev/null || true
            cp /bin/echo "$exp_dir/seeds/seed3.elf" 2>/dev/null || true
            ;;
    esac
    
    # Create run script
    cat > "$exp_dir/RUN.sh" << 'EOFRUN'
#!/bin/bash
cd "$(dirname "$0")"
echo "══════════════════════════════════════════════"
echo "AFL++ Fuzzing: $(basename $(pwd))"
echo "══════════════════════════════════════════════"
echo "Binary: binary/target"
echo "Seeds:  seeds/"
echo "Output: findings/"
echo "══════════════════════════════════════════════"
echo ""
echo "Press Ctrl+C to stop fuzzing"
echo ""
sleep 1
afl-fuzz -i seeds -o findings -m none -- ./binary/target @@
EOFRUN
    chmod +x "$exp_dir/RUN.sh"
    
    # Create info file
    cat > "$exp_dir/INFO.txt" << EOFINFO
Target: $name
Binary: $(basename $binary)
Seeds: $seed_type format
Location: $exp_dir

Commands:
  Start fuzzing:  ./RUN.sh
  View crashes:   ls findings/default/crashes/
  View coverage:  cat findings/default/fuzzer_stats
  Clean results:  rm -rf findings/*
EOFINFO
    
    CREATED_EXPERIMENTS+=("$name")
    echo "[✓] Created: $name"
    return 0
}

# Organize LAVA-M binaries
for target_info in "${BUILT_TARGETS[@]}"; do
    target="${target_info%%:*}"
    binary="${target_info#*:}"
    
    case "$target" in
        base64)
            create_exp "lavam_base64" "$binary" "base64"
            ;;
        md5sum)
            create_exp "lavam_md5sum" "$binary" "text"
            ;;
        uniq)
            create_exp "lavam_uniq" "$binary" "text"
            ;;
        who)
            create_exp "lavam_who" "$binary" "text"
            ;;
    esac
done

# Organize binutils binaries
if [ -n "$BINUTILS_BUILT" ]; then
    [ -f "$BINUTILS_BUILT/bin/objdump" ] && create_exp "binutils_objdump" "$BINUTILS_BUILT/bin/objdump" "elf"
    [ -f "$BINUTILS_BUILT/bin/readelf" ] && create_exp "binutils_readelf" "$BINUTILS_BUILT/bin/readelf" "elf"
    [ -f "$BINUTILS_BUILT/bin/nm" ] && create_exp "binutils_nm" "$BINUTILS_BUILT/bin/nm" "elf"
    [ -f "$BINUTILS_BUILT/bin/size" ] && create_exp "binutils_size" "$BINUTILS_BUILT/bin/size" "elf"
fi

# System binaries (always available)
[ -f "/usr/bin/file" ] && create_exp "system_file" "/usr/bin/file" "text"
[ -f "/usr/bin/strings" ] && create_exp "system_strings" "/usr/bin/strings" "elf"

# ============================================================================
# STEP 4: Create Master Control Scripts
# ============================================================================
echo ""
echo "[+] Creating master control scripts..."

# List experiments
cat > "$EXP_DIR/list.sh" << 'EOFLIST'
#!/bin/bash
cd "$(dirname "$0")"
echo "Available Fuzzing Experiments:"
echo "═══════════════════════════════"
for dir in */; do
    if [ -f "${dir}RUN.sh" ]; then
        name="${dir%/}"
        binary_size=$(du -h "${dir}binary/target" 2>/dev/null | cut -f1)
        seed_count=$(ls -1 "${dir}seeds/" 2>/dev/null | wc -l)
        printf "  %-25s (binary: %5s, seeds: %d)\n" "$name" "$binary_size" "$seed_count"
    fi
done
echo ""
echo "To run an experiment:"
echo "  cd <experiment_name>"
echo "  ./RUN.sh"
EOFLIST
chmod +x "$EXP_DIR/list.sh"

# Collect results
cat > "$EXP_DIR/collect_results.sh" << 'EOFCOLLECT'
#!/bin/bash
cd "$(dirname "$0")"
RESULTS="results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS"

echo "Collecting results from all experiments..."
echo ""

for dir in */findings/default/; do
    if [ -d "$dir" ]; then
        name=$(dirname $(dirname "$dir"))
        mkdir -p "$RESULTS/$name"
        
        # Copy crashes
        if [ -d "${dir}crashes" ]; then
            cp -r "${dir}crashes" "$RESULTS/$name/" 2>/dev/null
            crash_count=$(ls -1 "${dir}crashes" 2>/dev/null | wc -l)
        else
            crash_count=0
        fi
        
        # Copy hangs
        if [ -d "${dir}hangs" ]; then
            cp -r "${dir}hangs" "$RESULTS/$name/" 2>/dev/null
        fi
        
        # Copy stats
        if [ -f "${dir}fuzzer_stats" ]; then
            cp "${dir}fuzzer_stats" "$RESULTS/$name/"
        fi
        
        # Create summary
        cat > "$RESULTS/$name/SUMMARY.txt" << EOFSUMMARY
Experiment: $name
Crashes: $crash_count
Collected: $(date)
EOFSUMMARY
        
        echo "[✓] $name: $crash_count crashes"
    fi
done

echo ""
echo "Results collected to: $RESULTS/"
EOFCOLLECT
chmod +x "$EXP_DIR/collect_results.sh"

# ============================================================================
# Final Summary
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✓ SETUP COMPLETE!                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Build Summary:"
echo "  LAVA-M targets built: ${#BUILT_TARGETS[@]}"
echo "  Binutils built: $([ -n "$BINUTILS_BUILT" ] && echo "Yes" || echo "No")"
echo ""
echo "Experiment Directory: $EXP_DIR"
echo ""
echo "Created Experiments (${#CREATED_EXPERIMENTS[@]} total):"
for exp in "${CREATED_EXPERIMENTS[@]}"; do
    exp_dir="$EXP_DIR/$exp"
    binary_size=$(du -h "$exp_dir/binary/target" 2>/dev/null | cut -f1)
    seed_count=$(ls -1 "$exp_dir/seeds/" 2>/dev/null | wc -l)
    printf "  %-25s (binary: %5s, seeds: %d)\n" "$exp" "$binary_size" "$seed_count"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Quick Start:"
echo "  cd $EXP_DIR"
echo "  ./list.sh                    # List all experiments"
echo ""
if [ ${#CREATED_EXPERIMENTS[@]} -gt 0 ]; then
    first_exp="${CREATED_EXPERIMENTS[0]}"
    echo "  cd $first_exp"
    echo "  ./RUN.sh                     # Start fuzzing!"
fi
echo ""
echo "After fuzzing (let run for hours):"
echo "  cd $EXP_DIR"
echo "  ./collect_results.sh         # Gather all results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
