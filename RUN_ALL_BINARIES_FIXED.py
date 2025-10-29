#!/usr/bin/env python3
"""
Run experiments on all available binaries - FIXED VERSION
Actually runs for the specified duration
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta

# ANSI Colors
GREEN = '\033[92m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

BANNER = f"""{CYAN}{BOLD}
╔═══════════════════════════════════════════════════════════════╗
║          MULTI-BINARY FUZZING EXPERIMENT RUNNER               ║
║                                                               ║
║   Running AFL++ on ALL available binaries                     ║
╚═══════════════════════════════════════════════════════════════╝
{RESET}"""

class MultiBinaryRunner:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.bins_dir = self.base_dir / "fuzz_binaries/debian-bins"
        self.results_dir = self.base_dir / "results/multi-binary-experiment"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.fuzzers = []
        self.start_time = None
        self.end_time = None
        
    def discover_binaries(self):
        """Find all available binaries"""
        print(f"{CYAN}[*] Discovering binaries...{RESET}\n")
        
        binaries = []
        
        for binary_file in self.bins_dir.iterdir():
            if binary_file.is_file() and os.access(binary_file, os.X_OK):
                name = binary_file.stem.replace('-system', '')
                
                # Determine input type and args
                if 'file' in name:
                    input_type = 'binary'
                    args = '@@'
                elif 'readelf' in name:
                    input_type = 'elf'
                    args = '-a @@'
                elif 'objdump' in name:
                    input_type = 'elf'
                    args = '-d @@'
                elif 'nm' in name or 'size' in name:
                    input_type = 'elf'
                    args = '@@'
                elif 'strings' in name:
                    input_type = 'text'
                    args = '@@'
                elif 'tcpdump' in name:
                    input_type = 'pcap'
                    args = '-r @@'
                elif 'sqlite3' in name:
                    input_type = 'sql'
                    args = '@@'
                else:
                    input_type = 'binary'
                    args = '@@'
                
                binaries.append({
                    'name': name,
                    'path': str(binary_file),
                    'input_type': input_type,
                    'args': args
                })
                
                print(f"{GREEN}[✓] {name:15s} - {input_type:10s} - {binary_file}{RESET}")
        
        print(f"\n{BOLD}Total binaries found: {len(binaries)}{RESET}\n")
        return binaries
    
    def create_input_corpus(self, binary_info):
        """Create seed corpus for binary"""
        name = binary_info['name']
        input_type = binary_info['input_type']
        
        input_dir = self.base_dir / f"afl-workdir/input-{name}"
        input_dir.mkdir(parents=True, exist_ok=True)
        
        if input_type == 'elf':
            # Copy ELF binaries as seeds
            import shutil
            for bin_file in ['/bin/ls', '/bin/cat', '/bin/bash', '/bin/cp', '/bin/mv']:
                if Path(bin_file).exists():
                    try:
                        shutil.copy(bin_file, input_dir / Path(bin_file).name)
                    except:
                        pass
        
        elif input_type == 'text':
            (input_dir / "test1.txt").write_text("Hello World\n")
            (input_dir / "test2.txt").write_text("Test data\n123\n")
            (input_dir / "test3.txt").write_text("Sample input\nMultiple lines\n")
        
        elif input_type == 'pcap':
            # Create minimal PCAP file
            pcap_header = b'\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00'
            (input_dir / "test.pcap").write_bytes(pcap_header)
        
        elif input_type == 'sql':
            (input_dir / "test.sql").write_text("SELECT 1;\n")
            (input_dir / "test2.sql").write_text("CREATE TABLE test (id INT);\n")
        
        else:
            # Generic binary inputs
            (input_dir / "test1.bin").write_bytes(b"\x00\x01\x02\x03\x04\x05")
            (input_dir / "test2.bin").write_bytes(b"Hello")
            (input_dir / "test3.bin").write_bytes(b"\xff\xfe\xfd\xfc")
        
        return input_dir
    
    def start_fuzzer(self, binary_info):
        """Start AFL++ fuzzer for a binary"""
        name = binary_info['name']
        binary_path = binary_info['path']
        args = binary_info['args']
        
        print(f"{CYAN}[*] Starting fuzzer for: {name}{RESET}")
        
        # Create input corpus
        input_dir = self.create_input_corpus(binary_info)
        
        # Output directory
        output_dir = self.results_dir / name
        
        # Build AFL++ command (NO timeout - we'll manage it ourselves)
        cmd = [
            'afl-fuzz',
            '-i', str(input_dir),
            '-o', str(output_dir),
            '-m', 'none',
            '--'
        ]
        
        cmd.append(binary_path)
        
        if args:
            cmd.extend(args.split())
        
        # Start fuzzer
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            self.fuzzers.append({
                'name': name,
                'process': process,
                'output_dir': output_dir,
                'binary': binary_info
            })
            
            print(f"{GREEN}[✓] {name} started (PID: {process.pid}){RESET}")
            return True
            
        except Exception as e:
            print(f"{RED}[✗] Failed to start {name}: {e}{RESET}")
            return False
    
    def stop_all_fuzzers(self):
        """Stop all running fuzzers"""
        print(f"\n{YELLOW}[*] Stopping all fuzzers...{RESET}")
        
        for fuzzer_info in self.fuzzers:
            try:
                fuzzer_info['process'].terminate()
                fuzzer_info['process'].wait(timeout=5)
                print(f"{GREEN}[✓] Stopped {fuzzer_info['name']}{RESET}")
            except:
                try:
                    fuzzer_info['process'].kill()
                except:
                    pass
    
    def monitor_progress(self, duration_hours):
        """Monitor all running fuzzers for specified duration"""
        print(f"\n{CYAN}{'='*70}")
        print(f"MONITORING FUZZERS")
        print(f"{'='*70}{RESET}\n")
        
        self.end_time = self.start_time + timedelta(hours=duration_hours)
        
        print(f"{CYAN}[*] Will run until: {self.end_time.strftime('%H:%M:%S')}{RESET}")
        print(f"{CYAN}[*] Press Ctrl+C to stop early{RESET}\n")
        
        try:
            while datetime.now() < self.end_time:
                time.sleep(30)  # Check every 30 seconds
                self.display_status()
        
        except KeyboardInterrupt:
            print(f"\n{YELLOW}[!] Interrupted by user{RESET}")
        
        # Stop all fuzzers
        self.stop_all_fuzzers()
    
    def display_status(self):
        """Display current status"""
        runtime = datetime.now() - self.start_time
        remaining = self.end_time - datetime.now()
        
        print(f"\n{CYAN}{'='*70}")
        print(f"STATUS - Runtime: {runtime} | Remaining: {remaining}")
        print(f"{'='*70}{RESET}\n")
        
        total_crashes = 0
        total_paths = 0
        
        for fuzzer_info in self.fuzzers:
            name = fuzzer_info['name']
            output_dir = fuzzer_info['output_dir']
            
            # Count crashes
            crashes = len(list(output_dir.rglob("crashes/id:*")))
            
            # Get paths from stats
            stats_file = output_dir / "default/fuzzer_stats"
            paths = 0
            execs = 0
            if stats_file.exists():
                with open(stats_file) as f:
                    for line in f:
                        if 'corpus_count' in line:
                            paths = int(line.split(':')[1].strip())
                        elif 'execs_done' in line:
                            try:
                                execs = int(line.split(':')[1].strip())
                            except:
                                pass
            
            print(f"{name:15s}: {crashes:3d} crashes | {paths:5d} paths | {execs:8d} execs")
            
            total_crashes += crashes
            total_paths += paths
        
        print(f"\n{BOLD}TOTAL: {total_crashes} crashes | {total_paths} paths{RESET}\n")
    
    def generate_report(self):
        """Generate final report"""
        print(f"\n{CYAN}[*] Generating final report...{RESET}")
        
        report = []
        report.append("=" * 70)
        report.append("MULTI-BINARY FUZZING RESULTS")
        report.append("=" * 70)
        report.append(f"Start Time: {self.start_time}")
        report.append(f"End Time: {datetime.now()}")
        report.append(f"Duration: {datetime.now() - self.start_time}")
        report.append("")
        
        total_crashes = 0
        
        for fuzzer_info in self.fuzzers:
            name = fuzzer_info['name']
            output_dir = fuzzer_info['output_dir']
            
            crashes = list(output_dir.rglob("crashes/id:*"))
            total_crashes += len(crashes)
            
            # Get final stats
            stats_file = output_dir / "default/fuzzer_stats"
            paths = 0
            coverage = 0
            execs = 0
            if stats_file.exists():
                with open(stats_file) as f:
                    for line in f:
                        if 'corpus_count' in line:
                            paths = int(line.split(':')[1].strip())
                        elif 'bitmap_cvg' in line:
                            coverage = float(line.split(':')[1].strip().rstrip('%'))
                        elif 'execs_done' in line:
                            try:
                                execs = int(line.split(':')[1].strip())
                            except:
                                pass
            
            report.append(f"\n{name}:")
            report.append(f"  Crashes: {len(crashes)}")
            report.append(f"  Paths: {paths}")
            report.append(f"  Coverage: {coverage}%")
            report.append(f"  Executions: {execs:,}")
            
            if crashes:
                report.append(f"  Crash files:")
                for crash in crashes[:5]:  # Show first 5
                    report.append(f"    - {crash}")
        
        report.append("")
        report.append("=" * 70)
        report.append(f"SUMMARY: {total_crashes} total crashes found")
        report.append("=" * 70)
        
        report_text = "\n".join(report)
        print(report_text)
        
        # Save report
        report_file = self.results_dir / "EXPERIMENT_REPORT.txt"
        report_file.write_text(report_text)
        
        print(f"\n{GREEN}[✓] Report saved: {report_file}{RESET}")
        
        return total_crashes
    
    def run(self, duration_hours=1.0, max_binaries=None):
        """Run the complete experiment"""
        print(BANNER)
        
        # Discover binaries
        binaries = self.discover_binaries()
        
        if not binaries:
            print(f"{RED}[✗] No binaries found!{RESET}")
            return 1
        
        # Limit number of binaries if specified
        if max_binaries:
            binaries = binaries[:max_binaries]
            print(f"{YELLOW}[!] Limiting to {max_binaries} binaries{RESET}\n")
        
        # Start fuzzers
        print(f"\n{CYAN}{'='*70}")
        print(f"STARTING FUZZERS")
        print(f"{'='*70}{RESET}\n")
        
        self.start_time = datetime.now()
        
        for binary_info in binaries:
            self.start_fuzzer(binary_info)
            time.sleep(2)  # Stagger starts
        
        print(f"\n{GREEN}[✓] All {len(self.fuzzers)} fuzzers started!{RESET}")
        print(f"{CYAN}[*] Will run for {duration_hours} hours ({duration_hours * 60} minutes){RESET}\n")
        
        # Monitor
        self.monitor_progress(duration_hours)
        
        # Generate report
        total_crashes = self.generate_report()
        
        print(f"\n{GREEN}{BOLD}{'='*70}")
        print(f"EXPERIMENT COMPLETE!")
        print(f"{'='*70}{RESET}\n")
        print(f"Results directory: {self.results_dir}")
        print(f"Total crashes found: {total_crashes}")
        print(f"Duration: {datetime.now() - self.start_time}\n")
        
        return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Run fuzzing experiments on multiple binaries')
    parser.add_argument('--duration', type=float, default=1.0, help='Duration in hours (default: 1.0)')
    parser.add_argument('--max-binaries', type=int, help='Maximum number of binaries to fuzz')
    parser.add_argument('--quick', action='store_true', help='Quick test (0.5 hours, 3 binaries)')
    parser.add_argument('--all', action='store_true', help='Fuzz all available binaries')
    
    args = parser.parse_args()
    
    if args.quick:
        duration = 0.5
        max_binaries = 3
    elif args.all:
        duration = args.duration
        max_binaries = None
    else:
        duration = args.duration
        max_binaries = args.max_binaries
    
    base_dir = Path.cwd()
    runner = MultiBinaryRunner(base_dir)
    
    return runner.run(duration, max_binaries)


if __name__ == '__main__':
    sys.exit(main())
