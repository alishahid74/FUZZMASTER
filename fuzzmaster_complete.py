#!/usr/bin/env python3
"""
FuzzMaster - Complete Integration
Runs AFL++, AFL++ with PPO, and AFL++ without PPO automatically
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from complete_fuzzing_engine import FuzzingEngine
import argparse
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

BANNER = f"""{Fore.CYAN}
╔═══════════════════════════════════════════════════════════════════╗
║                  FUZZMASTER - Complete Edition                    ║
║                                                                   ║
║   Automatic Fuzzing with 3 Modes:                                ║
║   1. AFL++ Baseline                                               ║
║   2. AFL++ with PPO (Reinforcement Learning)                      ║
║   3. AFL++ without PPO (Custom Mutations)                         ║
╚═══════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""


def main():
    print(BANNER)
    
    parser = argparse.ArgumentParser(
        description='FuzzMaster - Run comparative fuzzing experiments automatically'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick test (30 minutes, OpenSSL only)'
    )
    
    parser.add_argument(
        '--standard',
        action='store_true',
        help='Standard test (1 hour, multiple benchmarks)'
    )
    
    parser.add_argument(
        '--research',
        action='store_true',
        help='Research protocol (2+ hours, all benchmarks)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=1.0,
        help='Custom duration in hours'
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.quick:
        duration = 0.5
        mode_name = "Quick Test"
    elif args.research:
        duration = 2.0
        mode_name = "Research Protocol"
    else:
        duration = args.duration
        mode_name = "Standard Campaign"
    
    print(f"\n{Fore.GREEN}Starting: {mode_name}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Duration: {duration} hours{Style.RESET_ALL}\n")
    
    # Setup engine
    project_root = Path.cwd()
    engine = FuzzingEngine(str(project_root))
    
    # Find OpenSSL
    openssl_bin = project_root / "binaries/openssl-1.1.1f/apps/openssl"
    
    if not openssl_bin.exists():
        print(f"{Fore.RED}[✗] OpenSSL not found at: {openssl_bin}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] Please compile OpenSSL first{Style.RESET_ALL}")
        return 1
    
    benchmark = {
        'name': 'OpenSSL',
        'binary': str(openssl_bin),
        'args': ''
    }
    
    print(f"{Fore.GREEN}[✓] Found benchmark: OpenSSL{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[✓] Binary: {openssl_bin}{Style.RESET_ALL}\n")
    
    # Run comparative experiment
    print(f"{Fore.CYAN}Starting all 3 fuzzing modes...{Style.RESET_ALL}\n")
    
    try:
        engine.run_comparative_experiment(benchmark, duration)
        
        print(f"\n{Fore.GREEN}{'='*70}")
        print(f"{Fore.GREEN}FUZZING COMPLETE!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}Results saved to:{Style.RESET_ALL}")
        print(f"  • {project_root}/results/afl-baseline/")
        print(f"  • {project_root}/results/afl-ppo/")
        print(f"  • {project_root}/results/afl-no-ppo/")
        print(f"  • {project_root}/results/comparative_report.json")
        print(f"  • {project_root}/results/COMPARATIVE_RESULTS.md\n")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Interrupted by user{Style.RESET_ALL}")
        return 130
    except Exception as e:
        print(f"\n{Fore.RED}[✗] Error: {e}{Style.RESET_ALL}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
