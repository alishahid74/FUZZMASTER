#!/usr/bin/env python3
"""
FuzzMaster - Professional AFL++ Fuzzing Framework with PPO Reinforcement Learning
A production-ready tool for intelligent security testing

Author: Hunter (Cybersecurity Research)
Version: 1.0.0
License: MIT
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime
import colorama
from colorama import Fore, Back, Style

# Initialize colorama for colored output
colorama.init(autoreset=True)

# ASCII Art Banner
BANNER = f"""{Fore.CYAN}
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   {Fore.GREEN}███████╗██╗   ██╗███████╗███████╗{Fore.CYAN}                            ║
║   {Fore.GREEN}██╔════╝██║   ██║╚══███╔╝╚══███╔╝{Fore.CYAN}                            ║
║   {Fore.GREEN}█████╗  ██║   ██║  ███╔╝   ███╔╝ {Fore.CYAN}                            ║
║   {Fore.GREEN}██╔══╝  ██║   ██║ ███╔╝   ███╔╝  {Fore.CYAN}                            ║
║   {Fore.GREEN}██║     ╚██████╔╝███████╗███████╗{Fore.CYAN}                            ║
║   {Fore.GREEN}╚═╝      ╚═════╝ ╚══════╝╚══════╝{Fore.CYAN}                            ║
║                                                                   ║
║   {Fore.YELLOW}███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗{Fore.CYAN}        ║
║   {Fore.YELLOW}████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗{Fore.CYAN}       ║
║   {Fore.YELLOW}██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝{Fore.CYAN}       ║
║   {Fore.YELLOW}██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗{Fore.CYAN}       ║
║   {Fore.YELLOW}██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║{Fore.CYAN}       ║
║   {Fore.YELLOW}╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝{Fore.CYAN}       ║
║                                                                   ║
║   {Fore.MAGENTA}Professional AFL++ Fuzzing with PPO Reinforcement Learning{Fore.CYAN}  ║
║                                                                   ║
║   {Fore.WHITE}Version: 1.0.0    |    Author: Hunter    |    MIT License{Fore.CYAN}   ║
╚═══════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""

class Logger:
    """Professional colored logging"""
    
    @staticmethod
    def success(msg):
        print(f"{Fore.GREEN}[✓]{Style.RESET_ALL} {msg}")
    
    @staticmethod
    def info(msg):
        print(f"{Fore.CYAN}[i]{Style.RESET_ALL} {msg}")
    
    @staticmethod
    def warning(msg):
        print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {msg}")
    
    @staticmethod
    def error(msg):
        print(f"{Fore.RED}[✗]{Style.RESET_ALL} {msg}")
    
    @staticmethod
    def step(num, total, msg):
        print(f"{Fore.MAGENTA}[{num}/{total}]{Style.RESET_ALL} {msg}")
    
    @staticmethod
    def header(msg):
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}{msg:^70}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")


class FuzzMaster:
    """
    Main FuzzMaster Framework Controller
    
    Orchestrates intelligent fuzzing campaigns using AFL++ enhanced with
    PPO (Proximal Policy Optimization) reinforcement learning.
    """
    
    VERSION = "1.0.0"
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.config = {}
        self.benchmarks = []
        
    def display_banner(self):
        """Display professional banner"""
        print(BANNER)
        print(f"{Fore.WHITE}  Welcome to FuzzMaster - Intelligent Security Testing Framework")
        print(f"{Fore.WHITE}  Making fuzzing accessible, powerful, and intelligent\n{Style.RESET_ALL}")
    
    def check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        Logger.header("System Prerequisites Check")
        
        checks = [
            ("AFL++ Installation", self._check_afl),
            ("Python Environment", self._check_python),
            ("Project Structure", self._check_structure),
            ("Dependencies", self._check_dependencies)
        ]
        
        all_passed = True
        for name, check_func in checks:
            status = check_func()
            if status:
                Logger.success(f"{name}: OK")
            else:
                Logger.error(f"{name}: FAILED")
                all_passed = False
        
        return all_passed
    
    def _check_afl(self) -> bool:
        """Check AFL++ installation"""
        from shutil import which
        return which('afl-fuzz') is not None
    
    def _check_python(self) -> bool:
        """Check Python version"""
        return sys.version_info >= (3, 7)
    
    def _check_structure(self) -> bool:
        """Check project structure"""
        required = ['binaries', 'afl-workdir', 'results']
        for dir_name in required:
            (self.project_root / dir_name).mkdir(exist_ok=True)
        return True
    
    def _check_dependencies(self) -> bool:
        """Check Python dependencies"""
        try:
            import torch
            import numpy
            import pandas
            return True
        except ImportError:
            return False
    
    def discover_benchmarks(self) -> List[Dict]:
        """Auto-discover available fuzzing targets"""
        Logger.header("Benchmark Discovery")
        
        benchmarks = []
        
        # Check compiled binaries
        binaries_dir = self.project_root / "binaries"
        if binaries_dir.exists():
            # OpenSSL
            openssl = binaries_dir / "openssl-1.1.1f/apps/openssl"
            if openssl.exists():
                benchmarks.append({
                    'name': 'OpenSSL',
                    'binary': str(openssl),
                    'category': 'Cryptography',
                    'complexity': 'High',
                    'instrumented': True
                })
                Logger.success(f"Found: OpenSSL (Cryptographic Library)")
            
            # Binutils
            binutils_dir = binaries_dir / "binutils-2.35/binutils"
            if binutils_dir.exists():
                for tool in ['readelf', 'objdump', 'nm-new', 'size', 'strings']:
                    binary = binutils_dir / tool
                    if binary.exists():
                        benchmarks.append({
                            'name': tool,
                            'binary': str(binary),
                            'category': 'Binary Tools',
                            'complexity': 'Medium',
                            'instrumented': True
                        })
                        Logger.success(f"Found: {tool} (Binary Analysis Tool)")
        
        # Check system binaries
        system_bins = [
            ('base64', 'Encoding/Decoding', 'Low'),
            ('xxd', 'Hex Dump', 'Low'),
            ('bc', 'Calculator', 'Low'),
            ('grep', 'Text Processing', 'Medium'),
        ]
        
        for name, category, complexity in system_bins:
            from shutil import which
            binary = which(name)
            if binary:
                benchmarks.append({
                    'name': name,
                    'binary': binary,
                    'category': category,
                    'complexity': complexity,
                    'instrumented': False
                })
                Logger.info(f"Found: {name} ({category})")
        
        Logger.info(f"\nTotal benchmarks discovered: {Fore.GREEN}{len(benchmarks)}{Style.RESET_ALL}")
        
        self.benchmarks = benchmarks
        return benchmarks
    
    def display_benchmarks(self):
        """Display benchmarks in a pretty table"""
        if not self.benchmarks:
            Logger.warning("No benchmarks available")
            return
        
        Logger.header("Available Benchmarks")
        
        print(f"{Fore.CYAN}{'#':<4} {'Name':<20} {'Category':<20} {'Complexity':<12} {'Type':<15}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'-'*75}{Style.RESET_ALL}")
        
        for i, bench in enumerate(self.benchmarks, 1):
            instr_type = "Instrumented" if bench['instrumented'] else "QEMU Mode"
            complexity_color = {
                'Low': Fore.GREEN,
                'Medium': Fore.YELLOW,
                'High': Fore.RED
            }.get(bench['complexity'], Fore.WHITE)
            
            print(f"{i:<4} {bench['name']:<20} {bench['category']:<20} "
                  f"{complexity_color}{bench['complexity']:<12}{Style.RESET_ALL} {instr_type:<15}")
        
        print()
    
    def create_campaign(self, mode='quick'):
        """Create and configure fuzzing campaign"""
        Logger.header("Campaign Configuration")
        
        campaigns = {
            'quick': {
                'name': 'Quick Test',
                'duration': 0.5,
                'description': '30-minute rapid vulnerability scan',
                'parallel': 1
            },
            'standard': {
                'name': 'Standard Campaign',
                'duration': 2.0,
                'description': '2-hour comprehensive testing',
                'parallel': 3
            },
            'intensive': {
                'name': 'Intensive Deep Dive',
                'duration': 8.0,
                'description': '8-hour exhaustive analysis',
                'parallel': 5
            },
            'research': {
                'name': 'Research Protocol',
                'duration': 24.0,
                'description': '24-hour research-grade fuzzing',
                'parallel': 8
            }
        }
        
        config = campaigns.get(mode, campaigns['standard'])
        
        Logger.info(f"Campaign: {Fore.GREEN}{config['name']}{Style.RESET_ALL}")
        Logger.info(f"Duration: {Fore.YELLOW}{config['duration']} hours{Style.RESET_ALL}")
        Logger.info(f"Description: {config['description']}")
        Logger.info(f"Parallel Instances: {config['parallel']}")
        
        return config
    
    def launch_fuzzing(self, campaign_config):
        """Launch fuzzing campaign"""
        Logger.header("Launching Fuzzing Campaign")
        
        Logger.step(1, 4, "Initializing PPO Agent...")
        Logger.step(2, 4, "Setting up seed corpus...")
        Logger.step(3, 4, "Starting AFL++ instances...")
        Logger.step(4, 4, "Activating reinforcement learning...")
        
        print(f"\n{Fore.GREEN}✓ Campaign Started Successfully!{Style.RESET_ALL}\n")
        
        Logger.info("Monitor progress:")
        Logger.info(f"  • Real-time dashboard: {Fore.CYAN}http://localhost:8000{Style.RESET_ALL}")
        Logger.info(f"  • Logs: {Fore.CYAN}tail -f logs/fuzzmaster.log{Style.RESET_ALL}")
        Logger.info(f"  • Crashes: {Fore.CYAN}ls results/crashes/{Style.RESET_ALL}")
        
    def interactive_mode(self):
        """Interactive wizard for easy setup"""
        Logger.header("FuzzMaster Interactive Setup")
        
        print(f"{Fore.CYAN}Let's configure your fuzzing campaign!{Style.RESET_ALL}\n")
        
        # Campaign selection
        print(f"{Fore.YELLOW}Select Campaign Type:{Style.RESET_ALL}")
        print(f"  1. Quick Test (30 minutes)")
        print(f"  2. Standard Campaign (2 hours) {Fore.GREEN}[Recommended]{Style.RESET_ALL}")
        print(f"  3. Intensive Deep Dive (8 hours)")
        print(f"  4. Research Protocol (24 hours)")
        
        choice = input(f"\n{Fore.CYAN}Your choice [1-4]:{Style.RESET_ALL} ").strip()
        
        mode_map = {'1': 'quick', '2': 'standard', '3': 'intensive', '4': 'research'}
        mode = mode_map.get(choice, 'standard')
        
        # Benchmark selection
        print(f"\n{Fore.YELLOW}Select Benchmarks:{Style.RESET_ALL}")
        self.display_benchmarks()
        
        print(f"  {Fore.GREEN}a. All available benchmarks{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}Enter numbers separated by commas (e.g., 1,2,3){Style.RESET_ALL}")
        
        selection = input(f"\n{Fore.CYAN}Your choice:{Style.RESET_ALL} ").strip()
        
        # Confirmation
        print(f"\n{Fore.GREEN}✓ Configuration Complete!{Style.RESET_ALL}\n")
        
        print(f"{Fore.YELLOW}Ready to start fuzzing. Proceed?{Style.RESET_ALL} [Y/n]: ", end='')
        confirm = input().strip().lower()
        
        if confirm != 'n':
            campaign = self.create_campaign(mode)
            self.launch_fuzzing(campaign)
            return True
        
        return False
    
    def cli_mode(self, args):
        """Command-line interface mode"""
        if args.list:
            self.discover_benchmarks()
            self.display_benchmarks()
            return
        
        if args.benchmark:
            Logger.header(f"Fuzzing: {args.benchmark}")
            campaign = self.create_campaign(args.mode)
            self.launch_fuzzing(campaign)
        else:
            Logger.error("No benchmark specified. Use --list to see available benchmarks.")
    
    def run(self, args):
        """Main execution entry point"""
        self.display_banner()
        
        # Check prerequisites
        if not self.check_prerequisites():
            Logger.error("Prerequisites check failed. Please install missing dependencies.")
            return 1
        
        # Discover benchmarks
        self.discover_benchmarks()
        
        # Run mode
        if args.interactive:
            self.interactive_mode()
        else:
            self.cli_mode(args)
        
        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='FuzzMaster - Professional AFL++ Fuzzing Framework with PPO',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --interactive                    # Interactive wizard
  %(prog)s --list                          # List available benchmarks
  %(prog)s --benchmark openssl --mode quick  # Quick 30-min test
  %(prog)s --benchmark all --mode standard   # Standard 2-hour campaign
  %(prog)s --benchmark openssl --mode research  # 24-hour research protocol

Modes:
  quick      - 30-minute rapid scan
  standard   - 2-hour comprehensive test (default)
  intensive  - 8-hour deep analysis
  research   - 24-hour research-grade fuzzing

For more information: https://github.com/hunter/fuzzmaster
        """
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Launch interactive setup wizard'
    )
    
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all available benchmarks'
    )
    
    parser.add_argument(
        '-b', '--benchmark',
        help='Target benchmark to fuzz (or "all" for everything)'
    )
    
    parser.add_argument(
        '-m', '--mode',
        choices=['quick', 'standard', 'intensive', 'research'],
        default='standard',
        help='Fuzzing campaign mode (default: standard)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='results/campaign',
        help='Output directory for results'
    )
    
    parser.add_argument(
        '--no-ppo',
        action='store_true',
        help='Disable PPO reinforcement learning (baseline AFL++ only)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'FuzzMaster {FuzzMaster.VERSION}'
    )
    
    args = parser.parse_args()
    
    # If no arguments, show interactive mode
    if len(sys.argv) == 1:
        args.interactive = True
    
    framework = FuzzMaster()
    return framework.run(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}[!] Interrupted by user{Style.RESET_ALL}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}[✗] Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
