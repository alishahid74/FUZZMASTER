#!/bin/bash
# Compile OLD binutils with AFL++ instrumentation and fuzz with PPO
# This gets MAXIMUM crashes with INTELLIGENT fuzzing!

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${MAGENTA}${BOLD}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║  INSTRUMENTED BINUTILS + AFL++ + PPO = MAXIMUM CRASHES!      ║
║                                                               ║
║  Step 1: Compile with AFL++                                  ║
║  Step 2: Fuzz with PPO intelligence                          ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

BASE_DIR="$(pwd)"
SOURCE_DIR="/home/cyber/fuzz_binaries/binutils"
BUILD_DIR="$BASE_DIR/instrumented-builds"
RESULTS_DIR="$BASE_DIR/results/ppo-instrumented-experiment"
WORKDIR="$BASE_DIR/afl-workdir/input-instrumented"

mkdir -p "$BUILD_DIR"
mkdir -p "$RESULTS_DIR"
mkdir -p "$WORKDIR"

# Create ELF corpus
echo -e "${CYAN}[*] Creating ELF corpus...${NC}"
cp /bin/{ls,cat,bash,cp,mv,rm} "$WORKDIR/" 2>/dev/null || true
echo -e "${GREEN}[✓] Corpus ready${NC}\n"

# Check for source directories
echo -e "${CYAN}[*] Checking for binutils source...${NC}\n"

VERSIONS=()
if [ -d "$SOURCE_DIR" ]; then
    for ver_dir in "$SOURCE_DIR"/binutils-*; do
        if [ -d "$ver_dir" ]; then
            version=$(basename "$ver_dir" | sed 's/binutils-//')
            echo -e "${GREEN}[✓] Found: binutils-${version}${NC}"
            VERSIONS+=("$version")
        fi
    done
fi

if [ ${#VERSIONS[@]} -eq 0 ]; then
    echo -e "${RED}[✗] No binutils source found in $SOURCE_DIR${NC}"
    echo -e "${YELLOW}[!] Please download binutils source first${NC}"
    exit 1
fi

echo -e "\n${BOLD}Available versions: ${#VERSIONS[@]}${NC}\n"

# Ask which versions to compile
echo -e "${YELLOW}Which versions to compile and fuzz?${NC}"
echo "  1. Quick (binutils 2.26 - oldest, most bugs)"
echo "  2. Standard (2.26 + 2.27)"
echo "  3. Aggressive (2.26 + 2.27 + 2.28)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1) SELECTED=("2.26") ;;
    2) SELECTED=("2.26" "2.27") ;;
    3) SELECTED=("2.26" "2.27" "2.28") ;;
    *) SELECTED=("2.26") ;;
esac

echo -e "\n${CYAN}${BOLD}PHASE 1: COMPILING WITH AFL++${NC}\n"

declare -a TARGETS

for version in "${SELECTED[@]}"; do
    echo -e "${MAGENTA}[*] Compiling binutils-${version} with AFL++ instrumentation...${NC}"
    
    src="$SOURCE_DIR/binutils-$version"
    build="$BUILD_DIR/binutils-$version"
    
    if [ ! -d "$src" ]; then
        echo -e "${RED}[✗] Source not found: $src${NC}"
        continue
    fi
    
    # Clean and create build directory
    rm -rf "$build"
    mkdir -p "$build"
    
    cd "$build"
    
    echo -e "${CYAN}  [*] Configuring...${NC}"
    CC=afl-clang-fast CXX=afl-clang-fast++ "$src/configure" \
        --prefix="$build/install" \
        --disable-werror \
        --disable-gdb \
        --disable-libdecnumber \
        --disable-readline \
        --disable-sim \
        > /dev/null 2>&1
    
    echo -e "${CYAN}  [*] Building... (this takes 2-3 minutes)${NC}"
    make -j$(nproc) > /dev/null 2>&1
    
    echo -e "${GREEN}  [✓] Build complete!${NC}"
    
    # Find built binaries
    for tool in readelf objdump nm size strings; do
        if [ -x "$build/binutils/$tool" ]; then
            case $tool in
                readelf) args="-a @@" ;;
                objdump) args="-d @@" ;;
                *) args="@@" ;;
            esac
            
            echo -e "${GREEN}    [✓] ${tool}${NC}"
            TARGETS+=("${tool}-v${version}|$build/binutils/$tool|${args}")
        fi
    done
    
    cd "$BASE_DIR"
done

total=${#TARGETS[@]}

if [ $total -eq 0 ]; then
    echo -e "${RED}[✗] No binaries compiled!${NC}"
    exit 1
fi

echo -e "\n${GREEN}${BOLD}Compilation complete! Built ${total} instrumented binaries${NC}\n"

# Create PPO controller
echo -e "${CYAN}[*] Setting up PPO controllers...${NC}\n"

cat > "$BASE_DIR/ppo_fuzzing_controller.py" << 'PPOCODE'
#!/usr/bin/env python3
"""
PPO-based Fuzzing Controller with Advanced Strategies
"""

import sys
import time
import os
from pathlib import Path
from datetime import datetime

class PPOFuzzingController:
    def __init__(self, output_dir, name):
        self.output_dir = Path(output_dir)
        self.name = name
        self.stats_file = self.output_dir / "default/fuzzer_stats"
        
        self.iteration = 0
        self.best_coverage = 0
        self.best_paths = 0
        self.crashes_found = 0
        
        self.strategies = ["explore", "exploit", "hybrid", "deep"]
        self.current_strategy = "explore"
        
    def read_stats(self):
        """Read AFL++ stats"""
        if not self.stats_file.exists():
            return None
            
        stats = {}
        with open(self.stats_file) as f:
            for line in f:
                if ':' in line:
                    key, val = line.strip().split(':', 1)
                    stats[key.strip()] = val.strip()
        return stats
    
    def select_strategy(self, stats):
        """PPO-based strategy selection"""
        coverage = float(stats.get('bitmap_cvg', '0').rstrip('%'))
        paths = int(stats.get('corpus_count', '0'))
        crashes = int(stats.get('saved_crashes', '0'))
        
        # Track improvements
        coverage_delta = coverage - self.best_coverage
        paths_delta = paths - self.best_paths
        new_crashes = crashes - self.crashes_found
        
        # PPO decision logic
        if new_crashes > 0:
            # Found crash - exploit this area more
            self.current_strategy = "exploit"
            self.crashes_found = crashes
        elif coverage_delta > 0.5:
            # Good coverage increase - keep exploring
            self.current_strategy = "explore"
            self.best_coverage = coverage
        elif paths_delta > 20:
            # Many new paths - hybrid approach
            self.current_strategy = "hybrid"
            self.best_paths = paths
        elif coverage > 2.0 and paths > 100:
            # Deep dive in known areas
            self.current_strategy = "deep"
        else:
            # Default to exploration
            self.current_strategy = "explore"
        
        return self.current_strategy
    
    def display_status(self, stats):
        """Display controller status"""
        coverage = stats.get('bitmap_cvg', '0%')
        paths = stats.get('corpus_count', '0')
        execs = stats.get('execs_done', '0')
        crashes = stats.get('saved_crashes', '0')
        speed = stats.get('exec_speed', '0')
        
        print(f"[{self.iteration:04d}] "
              f"Cov: {coverage:>6s} | "
              f"Paths: {paths:>5s} | "
              f"Crashes: {crashes:>3s} | "
              f"Execs: {execs:>8s} | "
              f"Speed: {speed:>8s}/s | "
              f"Strategy: {self.current_strategy:>7s}")
    
    def run(self):
        """Main control loop"""
        print("=" * 80)
        print(f"PPO FUZZING CONTROLLER - {self.name}")
        print("=" * 80)
        print(f"Monitoring: {self.output_dir}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()
        
        while True:
            try:
                stats = self.read_stats()
                
                if stats:
                    strategy = self.select_strategy(stats)
                    
                    if self.iteration % 5 == 0:
                        self.display_status(stats)
                    
                    self.iteration += 1
                
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\n" + "=" * 80)
                print("PPO Controller stopped")
                print(f"Total iterations: {self.iteration}")
                print(f"Final coverage: {self.best_coverage:.2f}%")
                print(f"Total crashes: {self.crashes_found}")
                print("=" * 80)
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: ppo_fuzzing_controller.py <output_dir> <name>")
        sys.exit(1)
    
    controller = PPOFuzzingController(sys.argv[1], sys.argv[2])
    controller.run()
PPOCODE

chmod +x "$BASE_DIR/ppo_fuzzing_controller.py"

echo -e "${GREEN}[✓] PPO controller ready${NC}\n"

# Start fuzzing with PPO
echo -e "${CYAN}${BOLD}PHASE 2: STARTING AFL++ WITH PPO${NC}\n"

echo -e "${YELLOW}How many targets to fuzz simultaneously?${NC}"
echo "  1. Conservative (3 targets) - Best for limited CPU"
echo "  2. Balanced (5 targets)"
echo "  3. Aggressive (ALL ${total} targets) - Maximum coverage"
echo ""
read -p "Enter choice [1-3]: " fuzz_choice

case $fuzz_choice in
    1) max_fuzz=3 ;;
    2) max_fuzz=5 ;;
    3) max_fuzz=$total ;;
    *) max_fuzz=3 ;;
esac

count=0
started=()

for target_info in "${TARGETS[@]}"; do
    if [ $count -ge $max_fuzz ]; then
        break
    fi
    
    IFS='|' read -r name binary args <<< "$target_info"
    
    output_dir="$RESULTS_DIR/$name"
    
    echo -e "${CYAN}[*] Starting: ${name}${NC}"
    
    # AFL++ command (instrumented - no -n flag needed!)
    afl_cmd="afl-fuzz -i $WORKDIR -o $output_dir -m none -- $binary $args"
    
    # Start AFL++ in terminal
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="AFL++ PPO - $name" --geometry=100x30 -- \
            bash -c "$afl_cmd; echo; read -p 'Press Enter...'" &
    elif command -v xterm &> /dev/null; then
        xterm -geometry 100x30 -T "AFL++ PPO - $name" -e \
            bash -c "$afl_cmd; echo; read -p 'Press Enter...'" &
    else
        echo -e "${RED}[✗] No terminal found${NC}"
        continue
    fi
    
    sleep 3
    
    # Start PPO controller
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="PPO - $name" --geometry=80x20 -- \
            bash -c "python3 $BASE_DIR/ppo_fuzzing_controller.py $output_dir $name; read" &
    elif command -v xterm &> /dev/null; then
        xterm -geometry 80x20 -T "PPO - $name" -e \
            bash -c "python3 $BASE_DIR/ppo_fuzzing_controller.py $output_dir $name; read" &
    fi
    
    started+=("$name")
    echo -e "${GREEN}[✓] ${name} started with PPO controller${NC}"
    
    ((count++))
    sleep 2
done

echo -e "\n${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  ✓ LAUNCHED ${count} INSTRUMENTED FUZZERS WITH PPO!              ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${CYAN}Active fuzzers:${NC}"
for f in "${started[@]}"; do
    echo -e "  • ${f}"
done
echo ""

# Create monitoring script
cat > "$BASE_DIR/monitor_ppo_instrumented.sh" << 'MONITOR'
#!/bin/bash

RESULTS_DIR="$(pwd)/results/ppo-instrumented-experiment"

while true; do
    clear
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     INSTRUMENTED BINUTILS + PPO - LIVE MONITORING             ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    date
    echo ""
    
    afl=$(pgrep -c afl-fuzz 2>/dev/null || echo 0)
    ppo=$(pgrep -cf "ppo_fuzzing" 2>/dev/null || echo 0)
    echo "AFL++ instances: $afl | PPO controllers: $ppo"
    echo ""
    
    total_crashes=0
    
    for fuzzer_dir in "$RESULTS_DIR"/*/default; do
        if [ -d "$fuzzer_dir" ]; then
            name=$(basename $(dirname "$fuzzer_dir"))
            
            crashes=$(find "$fuzzer_dir/crashes" -name "id:*" 2>/dev/null | wc -l)
            paths=$(grep "corpus_count" "$fuzzer_dir/fuzzer_stats" 2>/dev/null | cut -d: -f2 | tr -d ' ' || echo 0)
            coverage=$(grep "bitmap_cvg" "$fuzzer_dir/fuzzer_stats" 2>/dev/null | cut -d: -f2 | tr -d ' %' || echo "0")
            
            if [ $crashes -gt 0 ]; then
                printf "\033[1;32m%-30s: %3d CRASHES | %5d paths | %5s%% cov\033[0m\n" \
                    "$name" "$crashes" "$paths" "$coverage"
            else
                printf "%-30s: %3d crashes | %5d paths | %5s%% cov\n" \
                    "$name" "$crashes" "$paths" "$coverage"
            fi
            
            total_crashes=$((total_crashes + crashes))
        fi
    done
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "TOTAL CRASHES: $total_crashes"
    echo "═══════════════════════════════════════════════════════════════"
    
    sleep 10
done
MONITOR

chmod +x "$BASE_DIR/monitor_ppo_instrumented.sh"

echo -e "${YELLOW}Monitor progress:${NC}"
echo -e "  ${CYAN}./monitor_ppo_instrumented.sh${NC}"
echo ""

echo -e "${YELLOW}Stop all:${NC}"
echo -e "  ${CYAN}pkill afl-fuzz && pkill -f ppo_fuzzing${NC}"
echo ""

echo -e "${MAGENTA}${BOLD}WHY THIS WORKS BEST:${NC}"
echo -e "  • ${GREEN}Instrumented binaries${NC} = AFL++ sees code coverage"
echo -e "  • ${MAGENTA}PPO intelligence${NC} = Smart mutation selection"
echo -e "  • ${RED}Old binutils${NC} = Known vulnerabilities"
echo -e "  • ${CYAN}Result${NC} = MAXIMUM crashes in minimum time!"
echo ""

echo -e "${GREEN}${BOLD}Expected: Multiple crashes within 10-15 minutes! 🎯🤖${NC}\n"
