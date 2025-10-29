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
