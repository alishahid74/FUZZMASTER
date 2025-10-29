"""
Comprehensive Benchmark Runner
Runs AFL++ experiments across multiple benchmark targets
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Runs fuzzing experiments across multiple benchmark programs.
    """
    
    # Benchmark configuration
    BENCHMARKS = {
        'openssl': {
            'binary': 'binaries/openssl-1.1.1f/apps/openssl',
            'args': ['s_client'],
            'input_seeds': ['openssl-seeds'],
            'description': 'OpenSSL 1.1.1f - TLS/SSL toolkit'
        },
        'file': {
            'binary': 'binaries/lava-m/file/file',
            'args': [],
            'input_seeds': ['file-seeds'],
            'description': 'LAVA-M: file - File type detection'
        },
        'readelf': {
            'binary': 'binaries/binutils/readelf',
            'args': ['-a'],
            'input_seeds': ['elf-seeds'],
            'description': 'GNU binutils readelf - ELF file parser'
        },
        'tcpdump': {
            'binary': 'binaries/tcpdump/tcpdump',
            'args': ['-r', '-'],
            'input_seeds': ['pcap-seeds'],
            'description': 'tcpdump - Network packet analyzer'
        },
        'sqlite3': {
            'binary': 'binaries/sqlite/sqlite3',
            'args': [],
            'input_seeds': ['sql-seeds'],
            'description': 'SQLite 3 - SQL database engine'
        }
    }
    
    def __init__(self, project_root: str, results_base: str):
        """
        Initialize benchmark runner.
        
        Args:
            project_root: Root directory of fuzzing project
            results_base: Base directory for all results
        """
        self.project_root = Path(project_root)
        self.results_base = Path(results_base)
        self.results_base.mkdir(parents=True, exist_ok=True)
        
        # Verify project structure
        self.binaries_dir = self.project_root / "binaries"
        self.seeds_dir = self.project_root / "afl-workdir" / "seeds"
        
        logger.info(f"Benchmark Runner initialized")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Results base: {self.results_base}")
    
    def setup_seeds(self, benchmark_name: str) -> Path:
        """
        Set up input seeds for a benchmark.
        
        Args:
            benchmark_name: Name of the benchmark
            
        Returns:
            Path to seeds directory
        """
        config = self.BENCHMARKS[benchmark_name]
        seeds_dir = self.seeds_dir / benchmark_name
        seeds_dir.mkdir(parents=True, exist_ok=True)
        
        # Create minimal seed files if they don't exist
        if not any(seeds_dir.iterdir()):
            logger.info(f"Creating seed files for {benchmark_name}")
            
            if benchmark_name == 'openssl':
                # Create SSL handshake seed
                seed_file = seeds_dir / "ssl_hello.bin"
                seed_file.write_bytes(b"\x16\x03\x01\x00\x05\x01\x00\x00\x01\x03")
                
            elif benchmark_name == 'file':
                # Create various file format seeds
                (seeds_dir / "text.txt").write_text("Hello World")
                (seeds_dir / "empty").write_bytes(b"")
                
            elif benchmark_name == 'readelf':
                # Copy a minimal ELF file
                (seeds_dir / "minimal.elf").write_bytes(
                    b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                )
                
            elif benchmark_name == 'tcpdump':
                # Create minimal PCAP header
                pcap_header = (
                    b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00"
                    b"\x00\x00\x00\x00\x00\x00\x00\x00"
                    b"\xff\xff\x00\x00\x01\x00\x00\x00"
                )
                (seeds_dir / "minimal.pcap").write_bytes(pcap_header)
                
            elif benchmark_name == 'sqlite3':
                # Create simple SQL statements
                (seeds_dir / "create.sql").write_text("CREATE TABLE test (id INT);")
                (seeds_dir / "select.sql").write_text("SELECT 1;")
        
        return seeds_dir
    
    def verify_binary(self, binary_path: Path) -> bool:
        """
        Verify that a binary exists and is executable.
        
        Args:
            binary_path: Path to binary
            
        Returns:
            True if binary is valid
        """
        if not binary_path.exists():
            logger.error(f"Binary not found: {binary_path}")
            return False
        
        if not os.access(binary_path, os.X_OK):
            logger.warning(f"Binary not executable: {binary_path}")
            try:
                os.chmod(binary_path, 0o755)
                logger.info(f"Made binary executable: {binary_path}")
            except Exception as e:
                logger.error(f"Could not make binary executable: {e}")
                return False
        
        return True
    
    def run_baseline_experiment(
        self,
        benchmark_name: str,
        duration_hours: float = 1.0,
        timeout: int = 1000
    ) -> bool:
        """
        Run baseline AFL++ experiment on a benchmark.
        
        Args:
            benchmark_name: Name of benchmark to test
            duration_hours: Duration in hours
            timeout: Timeout in milliseconds
            
        Returns:
            True if successful
        """
        if benchmark_name not in self.BENCHMARKS:
            logger.error(f"Unknown benchmark: {benchmark_name}")
            return False
        
        config = self.BENCHMARKS[benchmark_name]
        binary_path = self.project_root / config['binary']
        
        # Verify binary
        if not self.verify_binary(binary_path):
            logger.error(f"Cannot run benchmark {benchmark_name}: binary issues")
            return False
        
        # Setup seeds
        seeds_dir = self.setup_seeds(benchmark_name)
        
        # Create output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = self.results_base / f"{benchmark_name}_baseline_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("="*60)
        logger.info(f"Running BASELINE on: {config['description']}")
        logger.info("="*60)
        
        # Build AFL++ command
        afl_cmd = [
            'afl-fuzz',
            '-i', str(seeds_dir),
            '-o', str(output_dir),
            '-m', 'none',
            '-t', str(timeout),
            '-Q',  # QEMU mode for binary-only fuzzing
            '--',
            str(binary_path)
        ] + config.get('args', [])
        
        # Add @@ if needed (for file input)
        if benchmark_name in ['file', 'readelf']:
            afl_cmd.append('@@')
        
        logger.info(f"Command: {' '.join(afl_cmd)}")
        
        try:
            # Start AFL++
            process = subprocess.Popen(
                afl_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for startup
            time.sleep(15)
            
            if process.poll() is not None:
                stderr = process.stderr.read().decode()
                logger.error(f"AFL++ failed to start: {stderr}")
                return False
            
            logger.info(f"AFL++ started (PID: {process.pid})")
            
            # Run for specified duration
            duration_seconds = duration_hours * 3600
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds:
                elapsed = time.time() - start_time
                
                # Check if still running
                if process.poll() is not None:
                    logger.error("AFL++ process terminated unexpectedly")
                    return False
                
                # Log progress every 5 minutes
                if int(elapsed) % 300 == 0 and elapsed > 0:
                    logger.info(f"Progress: {elapsed/3600:.2f} hours / {duration_hours:.2f} hours")
                
                time.sleep(60)
            
            # Stop AFL++
            logger.info("Stopping AFL++...")
            os.killpg(os.getpgid(process.pid), 15)  # SIGTERM
            process.wait(timeout=10)
            
            # Collect final stats
            stats_file = output_dir / "default" / "fuzzer_stats"
            if stats_file.exists():
                logger.info(f"Final stats saved: {stats_file}")
                self._log_final_stats(stats_file)
            
            logger.info(f"Baseline experiment complete: {benchmark_name}")
            logger.info(f"Results saved to: {output_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during baseline experiment: {e}", exc_info=True)
            return False
    
    def run_ppo_experiment(
        self,
        benchmark_name: str,
        duration_hours: float = 1.0,
        timeout: int = 1000
    ) -> bool:
        """
        Run PPO-enhanced experiment on a benchmark.
        
        Args:
            benchmark_name: Name of benchmark to test
            duration_hours: Duration in hours
            timeout: Timeout in milliseconds
            
        Returns:
            True if successful
        """
        if benchmark_name not in self.BENCHMARKS:
            logger.error(f"Unknown benchmark: {benchmark_name}")
            return False
        
        config = self.BENCHMARKS[benchmark_name]
        binary_path = self.project_root / config['binary']
        
        # Verify binary
        if not self.verify_binary(binary_path):
            return False
        
        # Setup seeds
        seeds_dir = self.setup_seeds(benchmark_name)
        
        # Create output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = self.results_base / f"{benchmark_name}_ppo_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("="*60)
        logger.info(f"Running PPO-ENHANCED on: {config['description']}")
        logger.info("="*60)
        
        try:
            # Import fuzzing controller
            sys.path.insert(0, str(self.project_root))
            from fuzzing_controller import FuzzingController
            
            # Create controller
            controller = FuzzingController(
                binary_path=str(binary_path),
                input_dir=str(seeds_dir),
                output_dir=str(output_dir),
                config={'experiment': {'duration_hours': duration_hours}}
            )
            
            # Start fuzzing
            logger.info("Starting PPO-enhanced fuzzing...")
            success = controller.start_fuzzer()
            
            if not success:
                logger.error("Failed to start PPO fuzzer")
                return False
            
            # Run for specified duration
            duration_seconds = duration_hours * 3600
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds:
                elapsed = time.time() - start_time
                
                # Training step
                if elapsed > 60:  # Wait 1 minute before training
                    controller.training_step()
                
                # Log progress
                if int(elapsed) % 300 == 0 and elapsed > 0:
                    logger.info(f"Progress: {elapsed/3600:.2f} hours / {duration_hours:.2f} hours")
                
                time.sleep(60)
            
            # Stop fuzzing
            logger.info("Stopping PPO-enhanced fuzzing...")
            controller.stop_fuzzer()
            
            # Save checkpoint
            controller.save_checkpoint(suffix="_final")
            
            logger.info(f"PPO experiment complete: {benchmark_name}")
            logger.info(f"Results saved to: {output_dir}")
            
            return True
            
        except ImportError as e:
            logger.error(f"Could not import fuzzing_controller: {e}")
            logger.error("Make sure all Phase 2 files are in the project root")
            return False
        except Exception as e:
            logger.error(f"Error during PPO experiment: {e}", exc_info=True)
            return False
    
    def _log_final_stats(self, stats_file: Path):
        """Log final fuzzing statistics."""
        try:
            with open(stats_file, 'r') as f:
                stats = {}
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        stats[key.strip()] = value.strip()
                
                logger.info("\nFinal Statistics:")
                logger.info(f"  Total Execs: {stats.get('execs_done', 'N/A')}")
                logger.info(f"  Execs/sec: {stats.get('execs_per_sec', 'N/A')}")
                logger.info(f"  Coverage: {stats.get('bitmap_cvg', 'N/A')}")
                logger.info(f"  Crashes: {stats.get('saved_crashes', 'N/A')}")
                logger.info(f"  Paths: {stats.get('paths_total', 'N/A')}")
                
        except Exception as e:
            logger.error(f"Could not read stats: {e}")
    
    def run_all_benchmarks(
        self,
        mode: str = 'both',
        duration_hours: float = 1.0,
        benchmarks: Optional[List[str]] = None
    ):
        """
        Run experiments on all benchmarks.
        
        Args:
            mode: 'baseline', 'ppo', or 'both'
            duration_hours: Duration per experiment
            benchmarks: List of specific benchmarks to run (None = all)
        """
        if benchmarks is None:
            benchmarks = list(self.BENCHMARKS.keys())
        
        results = {
            'start_time': datetime.now().isoformat(),
            'mode': mode,
            'duration_hours': duration_hours,
            'benchmarks': {}
        }
        
        for benchmark in benchmarks:
            if benchmark not in self.BENCHMARKS:
                logger.warning(f"Skipping unknown benchmark: {benchmark}")
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"BENCHMARK: {benchmark}")
            logger.info(f"{'='*60}\n")
            
            benchmark_results = {}
            
            # Run baseline
            if mode in ['baseline', 'both']:
                logger.info(f"Running baseline for {benchmark}...")
                success = self.run_baseline_experiment(
                    benchmark,
                    duration_hours=duration_hours
                )
                benchmark_results['baseline'] = 'success' if success else 'failed'
            
            # Run PPO
            if mode in ['ppo', 'both']:
                logger.info(f"Running PPO for {benchmark}...")
                success = self.run_ppo_experiment(
                    benchmark,
                    duration_hours=duration_hours
                )
                benchmark_results['ppo'] = 'success' if success else 'failed'
            
            results['benchmarks'][benchmark] = benchmark_results
        
        # Save summary
        results['end_time'] = datetime.now().isoformat()
        summary_file = self.results_base / "benchmark_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info("ALL BENCHMARKS COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Summary saved to: {summary_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run AFL++ experiments across multiple benchmarks'
    )
    parser.add_argument('--project-root', default='.',
                       help='Fuzzing project root directory')
    parser.add_argument('--results', '-r', default='benchmark_results',
                       help='Base directory for results')
    parser.add_argument('--mode', choices=['baseline', 'ppo', 'both'],
                       default='both', help='Which experiments to run')
    parser.add_argument('--duration', type=float, default=1.0,
                       help='Duration per experiment in hours')
    parser.add_argument('--benchmarks', nargs='+',
                       help='Specific benchmarks to run (default: all)')
    parser.add_argument('--list', action='store_true',
                       help='List available benchmarks and exit')
    
    args = parser.parse_args()
    
    runner = BenchmarkRunner(args.project_root, args.results)
    
    if args.list:
        print("\nAvailable Benchmarks:")
        print("="*60)
        for name, config in runner.BENCHMARKS.items():
            print(f"\n{name}:")
            print(f"  {config['description']}")
            print(f"  Binary: {config['binary']}")
        print("\n" + "="*60)
        sys.exit(0)
    
    runner.run_all_benchmarks(
        mode=args.mode,
        duration_hours=args.duration,
        benchmarks=args.benchmarks
    )


if __name__ == "__main__":
    main()
