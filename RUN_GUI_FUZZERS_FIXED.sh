#!/bin/bash
# Run AFL++ Fuzzers in GUI Mode - FIXED for non-instrumented binaries
# Uses -n flag for non-instrumented binaries

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║       AFL++ MULTI-BINARY FUZZING - GUI MODE                   ║
║                                                               ║
║   Each fuzzer in its own terminal window!                     ║
║   (Using dumb mode for non-instrumented binaries)             ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

BASE_DIR="$(pwd)"
BINS_DIR="$BASE_DIR/fuzz_binaries/debian-bins"
RESULTS_DIR="$BASE_DIR/results/gui-fuzzing-experiment"
WORKDIR="$BASE_DIR/afl-workdir"

# Create directories
mkdir -p "$RESULTS_DIR"
mkdir -p "$WORKDIR"

# Function to create input corpus
create_inputs() {
    local name=$1
    local type=$2
    local input_dir="$WORKDIR/input-${name}"
    
    mkdir -p "$input_dir"
    
    case $type in
        elf)
            cp /bin/{ls,cat,bash,cp,mv} "$input_dir/" 2>/dev/null || true
            ;;
        text)
            echo "Hello World" > "$input_dir/test1.txt"
            echo "Test data 123" > "$input_dir/test2.txt"
            echo "Sample text" > "$input_dir/test3.txt"
            ;;
        pcap)
            printf '\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00' > "$input_dir/test.pcap"
            ;;
        sql)
            echo "SELECT 1;" > "$input_dir/test1.sql"
            echo "CREATE TABLE t(id INT);" > "$input_dir/test2.sql"
            ;;
        *)
            echo "Hello" > "$input_dir/test1.bin"
            printf '\x00\x01\x02\x03\x04\x05' > "$input_dir/test2.bin"
            printf '\xff\xfe\xfd\xfc' > "$input_dir/test3.bin"
            ;;
    esac
    
    echo "$input_dir"
}

# Function to start fuzzer in new terminal
start_fuzzer() {
    local name=$1
    local binary=$2
    local input_dir=$3
    local args=$4
    local output_dir="$RESULTS_DIR/$name"
    
    echo -e "${CYAN}[*]${NC} Starting fuzzer for: ${GREEN}${name}${NC}"
    
    # Build AFL command with -n flag for non-instrumented binaries
    local afl_cmd="afl-fuzz -n -i $input_dir -o $output_dir -m none -- $binary $args"
    
    # Detect terminal emulator and launch
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="AFL++ - $name" --geometry=100x30 -- bash -c "$afl_cmd; echo ''; echo 'Fuzzing stopped. Press Enter to close...'; read" &
    elif command -v xterm &> /dev/null; then
        xterm -geometry 100x30 -T "AFL++ - $name" -e bash -c "$afl_cmd; echo ''; echo 'Fuzzing stopped. Press Enter to close...'; read" &
    elif command -v konsole &> /dev/null; then
        konsole --title "AFL++ - $name" -e bash -c "$afl_cmd; echo ''; echo 'Fuzzing stopped. Press Enter to close...'; read" &
    elif command -v xfce4-terminal &> /dev/null; then
        xfce4-terminal --title="AFL++ - $name" --geometry=100x30 -e "bash -c '$afl_cmd; echo; echo Fuzzing\ stopped.\ Press\ Enter\ to\ close...; read'" &
    elif command -v qterminal &> /dev/null; then
        qterminal -e "bash -c '$afl_cmd; echo; echo Fuzzing\ stopped.\ Press\ Enter\ to\ close...; read'" &
    else
        echo -e "${RED}[✗]${NC} No supported terminal emulator found!"
        echo "Please install one of: gnome-terminal, xterm, konsole, xfce4-terminal, qterminal"
        return 1
    fi
    
    sleep 2
    echo -e "${GREEN}[✓]${NC} ${name} launched in new terminal"
}

# Main execution
echo -e "\n${CYAN}${BOLD}DISCOVERING BINARIES${NC}\n"

# Array to store binary info
declare -a BINARIES

# Discover binaries
if [ ! -d "$BINS_DIR" ]; then
    echo -e "${RED}[✗]${NC} Directory not found: $BINS_DIR"
    exit 1
fi

for binary in "$BINS_DIR"/*-system; do
    if [ -x "$binary" ]; then
        name=$(basename "$binary" | sed 's/-system//')
        
        # Determine type and args
        case $name in
            readelf)
                type="elf"
                args="-a @@"
                ;;
            objdump)
                type="elf"
                args="-d @@"
                ;;
            nm|size)
                type="elf"
                args="@@"
                ;;
            file)
                type="binary"
                args="@@"
                ;;
            strings)
                type="text"
                args="@@"
                ;;
            tcpdump)
                type="pcap"
                args="-r @@"
                ;;
            sqlite3)
                type="sql"
                args="@@"
                ;;
            *)
                type="binary"
                args="@@"
                ;;
        esac
        
        echo -e "${GREEN}[✓]${NC} Found: ${name} (${type})"
        BINARIES+=("$name|$binary|$type|$args")
    fi
done

# Ask user how many to run
total=${#BINARIES[@]}
echo -e "\n${BOLD}Total binaries found: ${total}${NC}\n"

echo -e "${YELLOW}How many binaries do you want to fuzz?${NC}"
echo "  1. Quick (3 binaries)"
echo "  2. Standard (5 binaries)"
echo "  3. All ($total binaries)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        max_bins=3
        ;;
    2)
        max_bins=5
        ;;
    3)
        max_bins=$total
        ;;
    *)
        max_bins=3
        ;;
esac

echo -e "\n${CYAN}${BOLD}STARTING ${max_bins} FUZZERS${NC}\n"
echo -e "${YELLOW}Note: Using dumb mode (-n) for non-instrumented binaries${NC}"
echo -e "${YELLOW}This is slower but works without recompilation${NC}\n"

# Start fuzzers
count=0
for bin_info in "${BINARIES[@]}"; do
    if [ $count -ge $max_bins ]; then
        break
    fi
    
    IFS='|' read -r name binary type args <<< "$bin_info"
    
    # Create inputs
    input_dir=$(create_inputs "$name" "$type")
    
    # Start fuzzer
    start_fuzzer "$name" "$binary" "$input_dir" "$args"
    
    ((count++))
    sleep 3  # Stagger starts
done

echo -e "\n${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  ✓ ALL ${max_bins} FUZZERS STARTED IN SEPARATE WINDOWS!              ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${CYAN}You should now see ${max_bins} terminal windows with AFL++ running!${NC}\n"

echo -e "${YELLOW}What You'll See in Each Window:${NC}"
echo -e "  • ${GREEN}saved crashes${NC} - Number of unique crashes found"
echo -e "  • ${CYAN}corpus count${NC} - Number of interesting test cases"
echo -e "  • ${CYAN}map coverage${NC} - Code coverage percentage"
echo -e "  • ${CYAN}exec speed${NC} - Executions per second"
echo ""

echo -e "${YELLOW}Monitor All Fuzzers:${NC}"
echo -e "  ${CYAN}./monitor_gui_fuzzers.sh${NC} (in another terminal)"
echo ""

echo -e "${YELLOW}Check Crashes:${NC}"
echo -e "  ${CYAN}find $RESULTS_DIR -name 'id:*' -path '*/crashes/*' | wc -l${NC}"
echo ""

echo -e "${YELLOW}Stop All Fuzzers:${NC}"
echo -e "  • Press ${RED}Ctrl+C${NC} in each terminal window"
echo -e "  • Or run: ${CYAN}pkill afl-fuzz${NC}"
echo ""

# Create monitoring script
cat > "$BASE_DIR/monitor_gui_fuzzers.sh" << 'MONITOR'
#!/bin/bash
# Monitor all running GUI fuzzers

RESULTS_DIR="$(pwd)/results/gui-fuzzing-experiment"

echo "Starting monitoring... (Press Ctrl+C to stop)"
echo ""

while true; do
    clear
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║          GUI FUZZING EXPERIMENT - LIVE MONITORING             ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    date
    echo ""
    
    # Count running fuzzers
    running=$(pgrep -c afl-fuzz 2>/dev/null || echo 0)
    echo "Running fuzzers: $running"
    echo ""
    
    total_crashes=0
    total_paths=0
    
    for fuzzer_dir in "$RESULTS_DIR"/*/default; do
        if [ -d "$fuzzer_dir" ]; then
            name=$(basename $(dirname "$fuzzer_dir"))
            
            # Count crashes
            crashes=$(find "$fuzzer_dir/crashes" -name "id:*" 2>/dev/null | wc -l)
            
            # Get stats
            paths=0
            execs=0
            coverage="0.00"
            if [ -f "$fuzzer_dir/fuzzer_stats" ]; then
                paths=$(grep "corpus_count" "$fuzzer_dir/fuzzer_stats" 2>/dev/null | cut -d: -f2 | tr -d ' ' || echo 0)
                execs=$(grep "execs_done" "$fuzzer_dir/fuzzer_stats" 2>/dev/null | cut -d: -f2 | tr -d ' ' || echo 0)
                coverage=$(grep "bitmap_cvg" "$fuzzer_dir/fuzzer_stats" 2>/dev/null | cut -d: -f2 | tr -d ' %' || echo "0.00")
            fi
            
            printf "%-15s: %3d crashes | %5d paths | %8d execs | %5s%% coverage\n" \
                "$name" "$crashes" "$paths" "$execs" "$coverage"
            
            total_crashes=$((total_crashes + crashes))
            total_paths=$((total_paths + paths))
        fi
    done
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    printf "TOTAL: %d crashes | %d unique paths\n" "$total_crashes" "$total_paths"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Updating every 10 seconds... (Press Ctrl+C to stop)"
    
    sleep 10
done
MONITOR

chmod +x "$BASE_DIR/monitor_gui_fuzzers.sh"

echo -e "${CYAN}💡 TIP: Open another terminal and run:${NC}"
echo -e "   ${BOLD}./monitor_gui_fuzzers.sh${NC}"
echo -e "   ${CYAN}This shows a summary of ALL fuzzers updating every 10 seconds!${NC}"
echo ""

echo -e "${GREEN}Happy Fuzzing! 🚀${NC}\n"
