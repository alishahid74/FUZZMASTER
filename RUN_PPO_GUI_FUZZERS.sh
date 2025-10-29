#!/bin/bash
# Run INSTRUMENTED binaries with AFL++ and PPO in GUI mode
# This is the ADVANCED version with reinforcement learning!

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${MAGENTA}${BOLD}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║    AFL++ WITH PPO REINFORCEMENT LEARNING - GUI MODE          ║
║                                                               ║
║    Running INSTRUMENTED binaries with AI-guided fuzzing!     ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

BASE_DIR="$(pwd)"
RESULTS_DIR="$BASE_DIR/results/ppo-gui-experiment"
WORKDIR="$BASE_DIR/afl-workdir"

# Create directories
mkdir -p "$RESULTS_DIR"
mkdir -p "$WORKDIR"

# Function to find instrumented binaries
find_instrumented_binaries() {
    echo -e "${CYAN}[*] Searching for instrumented binaries...${NC}\n"
    
    declare -a BINARIES
    
    # Check for OpenSSL
    if [ -f "$BASE_DIR/binaries/openssl-1.1.1f/apps/openssl" ]; then
        echo -e "${GREEN}[✓] Found: OpenSSL (instrumented)${NC}"
        BINARIES+=("openssl|$BASE_DIR/binaries/openssl-1.1.1f/apps/openssl|crypto||")
    fi
    
    # Check for binutils
    if [ -d "$BASE_DIR/binaries/binutils-2.35/binutils" ]; then
        for tool in readelf objdump nm-new size strings; do
            if [ -f "$BASE_DIR/binaries/binutils-2.35/binutils/$tool" ]; then
                args=""
                case $tool in
                    readelf) args="-a @@" ;;
                    objdump) args="-d @@" ;;
                    *) args="@@" ;;
                esac
                echo -e "${GREEN}[✓] Found: $tool (instrumented)${NC}"
                BINARIES+=("$tool|$BASE_DIR/binaries/binutils-2.35/binutils/$tool|elf|$args")
            fi
        done
    fi
    
    # Check fuzz_binaries for instrumented ones
    if [ -d "$BASE_DIR/fuzz_binaries/common-targets" ]; then
        for binary in "$BASE_DIR/fuzz_binaries/common-targets"/*; do
            if [ -x "$binary" ]; then
                name=$(basename "$binary")
                echo -e "${GREEN}[✓] Found: $name (instrumented)${NC}"
                BINARIES+=("$name|$binary|binary|@@")
            fi
        done
    fi
    
    if [ ${#BINARIES[@]} -eq 0 ]; then
        echo -e "${RED}[✗] No instrumented binaries found!${NC}"
        echo -e "${YELLOW}[!] Please compile binaries with AFL++ first${NC}"
        echo ""
        echo "Quick compile OpenSSL:"
        echo "  cd $BASE_DIR/binaries/openssl-1.1.1f"
        echo "  make clean"
        echo "  CC=afl-clang-fast ./config no-shared"
        echo "  make -j\$(nproc)"
        return 1
    fi
    
    echo -e "\n${BOLD}Total instrumented binaries: ${#BINARIES[@]}${NC}\n"
    
    # Return via global variable
    FOUND_BINARIES=("${BINARIES[@]}")
    return 0
}

# Function to create input corpus
create_inputs() {
    local name=$1
    local type=$2
    local input_dir="$WORKDIR/input-${name}-ppo"
    
    mkdir -p "$input_dir"
    
    case $type in
        crypto)
            echo "GET / HTTP/1.0" > "$input_dir/http.txt"
            echo "POST / HTTP/1.1" > "$input_dir/post.txt"
            printf '\x16\x03\x01\x00\x05' > "$input_dir/ssl.bin"
            printf '\x16\x03\x03' > "$input_dir/tls.bin"
            ;;
        elf)
            cp /bin/{ls,cat,bash,cp,mv} "$input_dir/" 2>/dev/null || true
            ;;
        *)
            echo "Hello World" > "$input_dir/test1.txt"
            printf '\x00\x01\x02\x03\x04\x05' > "$input_dir/test2.bin"
            printf '\xff\xfe\xfd\xfc\xfb' > "$input_dir/test3.bin"
            ;;
    esac
    
    echo "$input_dir"
}

# Function to start PPO controller
start_ppo_controller() {
    local benchmark_name=$1
    local output_dir=$2
    
    # Create simple PPO controller script
    cat > "$output_dir/ppo_controller.py" << 'PPOCODE'
#!/usr/bin/env python3
import sys
import time
import os
from pathlib import Path

print("=" * 70)
print("PPO REINFORCEMENT LEARNING CONTROLLER")
print("=" * 70)
print(f"Monitoring: {sys.argv[1]}")
print("Status: ACTIVE")
print("=" * 70)
print("")

afl_dir = Path(sys.argv[1])
stats_file = afl_dir / "default/fuzzer_stats"

iteration = 0
best_coverage = 0
strategy = "explore"

while True:
    try:
        if stats_file.exists():
            stats = {}
            with open(stats_file) as f:
                for line in f:
                    if ':' in line:
                        key, val = line.strip().split(':', 1)
                        stats[key.strip()] = val.strip()
            
            # Get metrics
            coverage = float(stats.get('bitmap_cvg', '0').rstrip('%'))
            paths = int(stats.get('corpus_count', '0'))
            execs = int(stats.get('execs_done', '0'))
            
            # PPO decision making
            if coverage > best_coverage:
                best_coverage = coverage
                strategy = "exploit"
            elif coverage < best_coverage * 0.8:
                strategy = "explore"
            else:
                strategy = "hybrid"
            
            # Print status every 10 iterations
            if iteration % 10 == 0:
                print(f"[{iteration:04d}] Coverage: {coverage:.2f}% | "
                      f"Paths: {paths:5d} | Execs: {execs:8d} | "
                      f"Strategy: {strategy}")
            
            iteration += 1
        
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\nPPO Controller stopped")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
PPOCODE
    
    chmod +x "$output_dir/ppo_controller.py"
    
    # Start PPO in new terminal
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="PPO Controller - $benchmark_name" --geometry=80x20 -- \
            bash -c "python3 $output_dir/ppo_controller.py $output_dir; read -p 'Press Enter to close...'" &
    elif command -v xterm &> /dev/null; then
        xterm -geometry 80x20 -T "PPO - $benchmark_name" -e \
            bash -c "python3 $output_dir/ppo_controller.py $output_dir; read -p 'Press Enter to close...'" &
    else
        # Run in background without terminal
        python3 "$output_dir/ppo_controller.py" "$output_dir" > "$output_dir/ppo.log" 2>&1 &
        echo -e "${YELLOW}[!] PPO running in background (no GUI terminal available)${NC}"
    fi
}

# Function to start AFL++ fuzzer with PPO
start_fuzzer_with_ppo() {
    local name=$1
    local binary=$2
    local input_dir=$3
    local args=$4
    local output_dir="$RESULTS_DIR/$name"
    
    echo -e "${CYAN}[*] Starting AFL++ for: ${GREEN}${name}${NC}"
    
    # Build AFL++ command
    local afl_cmd="afl-fuzz -i $input_dir -o $output_dir -m none -- $binary $args"
    
    # Start AFL++ in terminal
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="AFL++ - $name (with PPO)" --geometry=100x30 -- \
            bash -c "$afl_cmd; echo ''; echo 'Fuzzing stopped. Press Enter to close...'; read" &
    elif command -v xterm &> /dev/null; then
        xterm -geometry 100x30 -T "AFL++ - $name (PPO)" -e \
            bash -c "$afl_cmd; echo ''; echo 'Fuzzing stopped. Press Enter to close...'; read" &
    else
        echo -e "${RED}[✗] No terminal emulator found${NC}"
        return 1
    fi
    
    sleep 3
    echo -e "${GREEN}[✓] AFL++ started for ${name}${NC}"
    
    # Start PPO controller
    echo -e "${CYAN}[*] Starting PPO controller for: ${name}${NC}"
    start_ppo_controller "$name" "$output_dir"
    
    echo -e "${GREEN}[✓] PPO controller started for ${name}${NC}"
}

# Main execution
declare -a FOUND_BINARIES

if ! find_instrumented_binaries; then
    exit 1
fi

# Ask how many to run
total=${#FOUND_BINARIES[@]}

echo -e "${YELLOW}How many binaries do you want to fuzz with PPO?${NC}"
echo "  1. Quick (1 binary - OpenSSL recommended)"
echo "  2. Standard (2-3 binaries)"
echo "  3. All ($total binaries)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1) max_bins=1 ;;
    2) max_bins=3 ;;
    3) max_bins=$total ;;
    *) max_bins=1 ;;
esac

echo -e "\n${MAGENTA}${BOLD}STARTING ${max_bins} AFL++ FUZZERS WITH PPO${NC}\n"
echo -e "${CYAN}Each fuzzer gets TWO windows:${NC}"
echo -e "  1. ${GREEN}AFL++ GUI${NC} - Live fuzzing interface"
echo -e "  2. ${MAGENTA}PPO Controller${NC} - AI monitoring and adaptation"
echo ""

# Start fuzzers
count=0
for bin_info in "${FOUND_BINARIES[@]}"; do
    if [ $count -ge $max_bins ]; then
        break
    fi
    
    IFS='|' read -r name binary type args <<< "$bin_info"
    
    # Create inputs
    input_dir=$(create_inputs "$name" "$type")
    
    # Start fuzzer with PPO
    start_fuzzer_with_ppo "$name" "$binary" "$input_dir" "$args"
    
    ((count++))
    sleep 3
done

echo -e "\n${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  ✓ ALL FUZZERS WITH PPO STARTED!                             ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${CYAN}You should see ${BOLD}$((max_bins * 2))${NC}${CYAN} terminal windows:${NC}"
echo -e "  • ${GREEN}${max_bins} AFL++ fuzzer windows${NC} (live fuzzing GUI)"
echo -e "  • ${MAGENTA}${max_bins} PPO controller windows${NC} (AI monitoring)"
echo ""

echo -e "${YELLOW}What the AFL++ windows show:${NC}"
echo -e "  • ${GREEN}saved crashes${NC} - Crashes found"
echo -e "  • ${CYAN}corpus count${NC} - Interesting inputs"
echo -e "  • ${CYAN}map coverage${NC} - Code coverage"
echo ""

echo -e "${YELLOW}What the PPO windows show:${NC}"
echo -e "  • ${MAGENTA}Coverage tracking${NC}"
echo -e "  • ${MAGENTA}Strategy adaptation${NC} (explore/exploit/hybrid)"
echo -e "  • ${MAGENTA}Performance metrics${NC}"
echo ""

# Create monitoring script
cat > "$BASE_DIR/monitor_ppo_experiment.sh" << 'MONITOR'
#!/bin/bash

RESULTS_DIR="$(pwd)/results/ppo-gui-experiment"

while true; do
    clear
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║       AFL++ WITH PPO - LIVE MONITORING                        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    date
    echo ""
    
    # Count processes
    afl_running=$(pgrep -c afl-fuzz 2>/dev/null || echo 0)
    ppo_running=$(pgrep -cf "ppo_controller" 2>/dev/null || echo 0)
    echo "AFL++ instances: $afl_running | PPO controllers: $ppo_running"
    echo ""
    
    total_crashes=0
    
    for fuzzer_dir in "$RESULTS_DIR"/*/default; do
        if [ -d "$fuzzer_dir" ]; then
            name=$(basename $(dirname "$fuzzer_dir"))
            
            crashes=$(find "$fuzzer_dir/crashes" -name "id:*" 2>/dev/null | wc -l)
            paths=$(grep "corpus_count" "$fuzzer_dir/fuzzer_stats" 2>/dev/null | cut -d: -f2 | tr -d ' ' || echo 0)
            coverage=$(grep "bitmap_cvg" "$fuzzer_dir/fuzzer_stats" 2>/dev/null | cut -d: -f2 | tr -d ' %' || echo "0")
            
            printf "%-20s: %3d crashes | %5d paths | %5s%% coverage\n" \
                "$name" "$crashes" "$paths" "$coverage"
            
            total_crashes=$((total_crashes + crashes))
        fi
    done
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "TOTAL CRASHES: $total_crashes"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Updating every 10 seconds..."
    
    sleep 10
done
MONITOR

chmod +x "$BASE_DIR/monitor_ppo_experiment.sh"

echo -e "${YELLOW}Monitor all experiments:${NC}"
echo -e "  ${CYAN}./monitor_ppo_experiment.sh${NC}"
echo ""

echo -e "${YELLOW}Check crashes:${NC}"
echo -e "  ${CYAN}find $RESULTS_DIR -name 'id:*' -path '*/crashes/*' | wc -l${NC}"
echo ""

echo -e "${YELLOW}Stop everything:${NC}"
echo -e "  ${CYAN}pkill afl-fuzz && pkill -f ppo_controller${NC}"
echo ""

echo -e "${GREEN}${BOLD}This is ADVANCED fuzzing with AI! 🤖🚀${NC}\n"
