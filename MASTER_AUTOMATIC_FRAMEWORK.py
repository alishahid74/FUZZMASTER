#!/usr/bin/env python3
"""
MASTER AUTOMATIC FUZZING FRAMEWORK
Integrates ALL existing components into one automatic system

Uses your existing:
- ppo_agent.py
- fuzzing_controller.py
- experiment_runner.py
- feedback_analyzer.py
- mutation_selector.py
- data_analysis.py
- visualizer.py
- report_generator.py
- presentation_generator.py
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import json
import signal

# ANSI Colors
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

BANNER = f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     █████╗ ██╗   ██╗████████╗ ██████╗ ███╗   ███╗ █████╗ ████████╗ ║
║    ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝ ║
║    ███████║██║   ██║   ██║   ██║   ██║██╔████╔██║███████║   ██║    ║
║    ██╔══██║██║   ██║   ██║   ██║   ██║██║╚██╔╝██║██╔══██║   ██║    ║
║    ██║  ██║╚██████╔╝   ██║   ╚██████╔╝██║ ╚═╝ ██║██║  ██║   ██║    ║
║    ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝    ║
║                                                                      ║
║          AFL++ PPO Complete Automatic Fuzzing Framework             ║
║                                                                      ║
║   Runs: AFL++ Baseline | AFL++ with PPO | AFL++ without PPO        ║
╚══════════════════════════════════════════════════════════════════════╝
{Colors.RESET}"""


class MasterFramework:
    """Master controller for all fuzzing components"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results_base = self.project_root / "results" / "master-experiment"
        self.results_base.mkdir(parents=True, exist_ok=True)
        
        self.processes = []
        self.start_time = None
        
    def log(self, level, message):
        """Colored logging"""
        colors = {
            'INFO': Colors.CYAN,
            'SUCCESS': Colors.GREEN,
            'WARNING': Colors.YELLOW,
            'ERROR': Colors.RED,
            'STEP': Colors.MAGENTA
        }
        color = colors.get(level, Colors.RESET)
        symbol = {'INFO': 'ℹ', 'SUCCESS': '✓', 'WARNING': '⚠', 'ERROR': '✗', 'STEP': '▶'}.get(level, '•')
        print(f"{color}[{symbol}] {message}{Colors.RESET}")
    
    def check_components(self):
        """Check that all required components exist"""
        self.log('STEP', "Checking components...")
        
        required_files = [
            'ppo_agent.py',
            'fuzzing_controller.py',
            'experiment_runner.py',
            'feedback_analyzer.py',
            'mutation_selector.py',
            'data_analysis.py',
            'visualizer.py',
            'report_generator.py',
            'presentation_generator.py',
            'config.yaml'
        ]
        
        missing = []
        for file in required_files:
            if not (self.project_root / file).exists():
                missing.append(file)
                self.log('WARNING', f"Missing: {file}")
            else:
                self.log('SUCCESS', f"Found: {file}")
        
        if missing:
            self.log('ERROR', f"Missing {len(missing)} required files!")
            self.log('INFO', "Please ensure all project files are in the directory")
            return False
        
        self.log('SUCCESS', "All components found!")
        return True
    
    def run_mode_baseline(self, benchmark, duration):
        """Run AFL++ Baseline mode"""
        self.log('STEP', "Starting Mode 1: AFL++ Baseline")
        
        output_dir = self.results_base / "baseline" / benchmark['name']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use existing experiment_runner.py
        cmd = [
            sys.executable,
            str(self.project_root / "experiment_runner.py"),
            '--benchmark', benchmark['binary'],
            '--output', str(output_dir),
            '--duration', str(duration),
            '--mode', 'baseline',
            '--no-ppo'
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.processes.append({
            'name': f"{benchmark['name']}-baseline",
            'process': process,
            'mode': 'baseline'
        })
        
        self.log('SUCCESS', f"AFL++ Baseline started (PID: {process.pid})")
        return process
    
    def run_mode_ppo(self, benchmark, duration):
        """Run AFL++ with PPO mode"""
        self.log('STEP', "Starting Mode 2: AFL++ with PPO")
        
        output_dir = self.results_base / "with-ppo" / benchmark['name']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use existing fuzzing_controller.py which integrates PPO
        cmd = [
            sys.executable,
            str(self.project_root / "fuzzing_controller.py"),
            '--benchmark', benchmark['binary'],
            '--output', str(output_dir),
            '--duration', str(duration),
            '--enable-ppo'
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.processes.append({
            'name': f"{benchmark['name']}-ppo",
            'process': process,
            'mode': 'with-ppo'
        })
        
        self.log('SUCCESS', f"AFL++ with PPO started (PID: {process.pid})")
        return process
    
    def run_mode_no_ppo(self, benchmark, duration):
        """Run AFL++ without PPO mode"""
        self.log('STEP', "Starting Mode 3: AFL++ without PPO")
        
        output_dir = self.results_base / "no-ppo" / benchmark['name']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use experiment_runner with custom mutations but no PPO
        cmd = [
            sys.executable,
            str(self.project_root / "experiment_runner.py"),
            '--benchmark', benchmark['binary'],
            '--output', str(output_dir),
            '--duration', str(duration),
            '--mode', 'custom',
            '--no-ppo'
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.processes.append({
            'name': f"{benchmark['name']}-no-ppo",
            'process': process,
            'mode': 'no-ppo'
        })
        
        self.log('SUCCESS', f"AFL++ without PPO started (PID: {process.pid})")
        return process
    
    def run_all_modes(self, benchmark, duration):
        """Run all three modes in parallel"""
        print(f"\n{Colors.BOLD}{'='*70}")
        print(f"STARTING COMPARATIVE EXPERIMENT: {benchmark['name']}")
        print(f"{'='*70}{Colors.RESET}\n")
        
        self.start_time = datetime.now()
        
        # Mode 1: Baseline
        self.run_mode_baseline(benchmark, duration)
        time.sleep(3)
        
        # Mode 2: With PPO
        self.run_mode_ppo(benchmark, duration)
        time.sleep(3)
        
        # Mode 3: Without PPO
        self.run_mode_no_ppo(benchmark, duration)
        
        print(f"\n{Colors.GREEN}✓ All 3 modes started successfully!{Colors.RESET}")
        print(f"{Colors.CYAN}Total processes: {len(self.processes)}{Colors.RESET}\n")
        
        # Monitor
        self.monitor_progress(duration)
    
    def monitor_progress(self, duration_hours):
        """Monitor all fuzzing processes"""
        self.log('INFO', f"Monitoring for {duration_hours} hours...")
        self.log('INFO', "Press Ctrl+C to stop early\n")
        
        end_time = self.start_time + timedelta(hours=duration_hours)
        
        try:
            while datetime.now() < end_time:
                time.sleep(30)  # Update every 30 seconds
                self.display_status()
        
        except KeyboardInterrupt:
            self.log('WARNING', "\nUser interrupted - stopping all processes...")
        
        self.stop_all()
        self.generate_reports()
    
    def display_status(self):
        """Display current status"""
        print(f"\n{Colors.CYAN}{'='*70}")
        print(f"STATUS UPDATE - Runtime: {datetime.now() - self.start_time}")
        print(f"{'='*70}{Colors.RESET}\n")
        
        for mode_dir in ['baseline', 'with-ppo', 'no-ppo']:
            mode_path = self.results_base / mode_dir
            if mode_path.exists():
                crashes = len(list(mode_path.rglob("crashes/id:*")))
                print(f"{Colors.GREEN}{mode_dir:15s}: {crashes} crashes{Colors.RESET}")
        
        total = len(list(self.results_base.rglob("crashes/id:*")))
        print(f"\n{Colors.BOLD}TOTAL: {total} crashes{Colors.RESET}\n")
    
    def stop_all(self):
        """Stop all processes"""
        self.log('STEP', "Stopping all processes...")
        
        for proc_info in self.processes:
            try:
                proc_info['process'].terminate()
                proc_info['process'].wait(timeout=5)
                self.log('SUCCESS', f"Stopped {proc_info['name']}")
            except:
                try:
                    proc_info['process'].kill()
                except:
                    pass
        
        self.log('SUCCESS', "All processes stopped")
    
    def generate_reports(self):
        """Generate comprehensive reports using existing tools"""
        self.log('STEP', "Generating reports...")
        
        # Use existing data_analysis.py
        for mode_dir in ['baseline', 'with-ppo', 'no-ppo']:
            mode_path = self.results_base / mode_dir
            if mode_path.exists():
                self.log('INFO', f"Analyzing {mode_dir}...")
                subprocess.run([
                    sys.executable,
                    str(self.project_root / "data_analysis.py"),
                    str(mode_path)
                ], capture_output=True)
        
        # Use existing visualizer.py
        self.log('INFO', "Generating visualizations...")
        subprocess.run([
            sys.executable,
            str(self.project_root / "visualizer.py"),
            str(self.results_base)
        ], capture_output=True)
        
        # Use existing report_generator.py
        self.log('INFO', "Generating research paper...")
        subprocess.run([
            sys.executable,
            str(self.project_root / "report_generator.py"),
            str(self.results_base),
            '-o', str(self.results_base / "FINAL_PAPER.md")
        ], capture_output=True)
        
        # Use existing presentation_generator.py
        self.log('INFO', "Generating presentation...")
        subprocess.run([
            sys.executable,
            str(self.project_root / "presentation_generator.py"),
            '-r', str(self.results_base),
            '-o', str(self.results_base / "FINAL_SLIDES.md")
        ], capture_output=True)
        
        # Create comparison summary
        self.create_comparison_summary()
        
        self.log('SUCCESS', "All reports generated!")
    
    def create_comparison_summary(self):
        """Create comparison summary"""
        summary = {
            'experiment': 'Comparative Fuzzing Analysis',
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'modes': {}
        }
        
        for mode in ['baseline', 'with-ppo', 'no-ppo']:
            mode_path = self.results_base / mode
            if mode_path.exists():
                crashes = list(mode_path.rglob("crashes/id:*"))
                summary['modes'][mode] = {
                    'crashes': len(crashes),
                    'crash_files': [str(c) for c in crashes[:5]]
                }
        
        summary_file = self.results_base / "comparison_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.log('SUCCESS', f"Summary: {summary_file}")
    
    def display_final_results(self):
        """Display final results"""
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*70}")
        print(f"FUZZING COMPLETE!")
        print(f"{'='*70}{Colors.RESET}\n")
        
        print(f"{Colors.CYAN}Results Location:{Colors.RESET}")
        print(f"  📁 {self.results_base}\n")
        
        print(f"{Colors.CYAN}Generated Files:{Colors.RESET}")
        for file in ['FINAL_PAPER.md', 'FINAL_SLIDES.md', 'comparison_summary.json']:
            path = self.results_base / file
            if path.exists():
                print(f"  ✓ {file}")
        
        print(f"\n{Colors.CYAN}Crash Summary:{Colors.RESET}")
        for mode in ['baseline', 'with-ppo', 'no-ppo']:
            mode_path = self.results_base / mode
            if mode_path.exists():
                crashes = len(list(mode_path.rglob("crashes/id:*")))
                print(f"  {mode:15s}: {crashes} crashes")
        
        print(f"\n{Colors.GREEN}✓ All reports ready for submission!{Colors.RESET}\n")


def main():
    print(BANNER)
    
    parser = argparse.ArgumentParser(
        description='Master Automatic Fuzzing Framework - Run all modes'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick 30-minute test'
    )
    
    parser.add_argument(
        '--standard',
        action='store_true',
        help='Standard 1-hour test'
    )
    
    parser.add_argument(
        '--intensive',
        action='store_true',
        help='Intensive 2-hour test'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        help='Custom duration in hours'
    )
    
    args = parser.parse_args()
    
    # Determine duration
    if args.quick:
        duration = 0.5
    elif args.intensive:
        duration = 2.0
    elif args.duration:
        duration = args.duration
    else:
        duration = 1.0  # Standard
    
    # Initialize framework
    project_root = Path.cwd()
    framework = MasterFramework(project_root)
    
    # Check components
    if not framework.check_components():
        return 1
    
    # Find OpenSSL
    openssl = project_root / "binaries/openssl-1.1.1f/apps/openssl"
    if not openssl.exists():
        framework.log('ERROR', f"OpenSSL not found: {openssl}")
        return 1
    
    benchmark = {
        'name': 'OpenSSL',
        'binary': str(openssl)
    }
    
    framework.log('SUCCESS', f"Found benchmark: {benchmark['name']}")
    framework.log('INFO', f"Duration: {duration} hours\n")
    
    # Run experiment
    try:
        framework.run_all_modes(benchmark, duration)
        framework.display_final_results()
        return 0
    
    except KeyboardInterrupt:
        framework.log('WARNING', "\nInterrupted by user")
        return 130
    except Exception as e:
        framework.log('ERROR', f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
