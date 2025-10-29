"""
Experiment Runner for AFL++ Fuzzing
Runs both baseline and PPO-enhanced experiments, collecting data for comparison.
"""

import os
import sys
import time
import json
import subprocess
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging
import shutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """
    Manages experimental runs for baseline and PPO-enhanced fuzzing.
    """
    
    def __init__(
        self,
        binary_path: str,
        input_dir: str,
        results_dir: str,
        config: Optional[Dict] = None
    ):
        """
        Initialize experiment runner.
        
        Args:
            binary_path: Path to target binary
            input_dir: Directory with initial corpus
            results_dir: Directory to store all results
            config: Configuration dictionary
        """
        self.binary_path = Path(binary_path)
        self.input_dir = Path(input_dir)
        self.results_dir = Path(results_dir)
        self.config = config or {}
        
        # Validate paths
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {binary_path}")
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Create results directory structure
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_dir = self.results_dir / "baseline"
        self.ppo_dir = self.results_dir / "ppo"
        self.data_dir = self.results_dir / "data"
        self.logs_dir = self.results_dir / "logs"
        
        for d in [self.baseline_dir, self.ppo_dir, self.data_dir, self.logs_dir]:
            d.mkdir(exist_ok=True)
        
        # Experiment configuration
        self.baseline_duration = self.config.get('baseline_duration', 2.0)  # hours
        self.ppo_duration = self.config.get('ppo_duration', 2.0)  # hours
        self.collection_interval = self.config.get('collection_interval', 60)  # seconds
        
        logger.info("Experiment Runner initialized")
        logger.info(f"Binary: {self.binary_path}")
        logger.info(f"Baseline duration: {self.baseline_duration} hours")
        logger.info(f"PPO duration: {self.ppo_duration} hours")
    
    def run_baseline_experiment(self) -> bool:
        """
        Run baseline AFL++ experiment without PPO.
        
        Returns:
            True if successful
        """
        logger.info("="*60)
        logger.info("Starting BASELINE Experiment (AFL++ only)")
        logger.info("="*60)
        
        output_dir = self.baseline_dir / "afl-output"
        output_dir.mkdir(exist_ok=True)
        
        # Build AFL++ command
        afl_cmd = [
            'afl-fuzz',
            '-i', str(self.input_dir),
            '-o', str(output_dir),
            '-Q',  # QEMU mode
            '-m', 'none',  # No memory limit
            '--',
            str(self.binary_path)
        ]
        
        logger.info(f"Command: {' '.join(afl_cmd)}")
        
        try:
            # Start AFL++
            logger.info("Starting AFL++ process...")
            process = subprocess.Popen(
                afl_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for startup
            time.sleep(10)
            
            if process.poll() is not None:
                stderr = process.stderr.read().decode()
                logger.error(f"AFL++ failed to start: {stderr}")
                return False
            
            logger.info(f"AFL++ started (PID: {process.pid})")
            
            # Collect data periodically
            start_time = time.time()
            duration_seconds = self.baseline_duration * 3600
            data_points = []
            
            while time.time() - start_time < duration_seconds:
                elapsed = time.time() - start_time
                
                # Collect metrics
                metrics = self._collect_metrics(output_dir / "default")
                if metrics:
                    metrics['elapsed_time'] = elapsed
                    metrics['elapsed_hours'] = elapsed / 3600
                    data_points.append(metrics)
                    
                    logger.info(f"Baseline [{elapsed/3600:.2f}h]: "
                              f"Coverage={metrics.get('coverage', 0):.2f}%, "
                              f"Crashes={metrics.get('unique_crashes', 0)}, "
                              f"Paths={metrics.get('paths_total', 0)}")
                
                # Sleep until next collection
                time.sleep(self.collection_interval)
            
            # Stop AFL++
            logger.info("Stopping AFL++...")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=10)
            
            # Save collected data
            self._save_experiment_data(data_points, self.data_dir / "baseline_data.json")
            
            logger.info("Baseline experiment completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during baseline experiment: {e}", exc_info=True)
            return False
    
    def run_ppo_experiment(self) -> bool:
        """
        Run PPO-enhanced AFL++ experiment.
        
        Returns:
            True if successful
        """
        logger.info("="*60)
        logger.info("Starting PPO-ENHANCED Experiment")
        logger.info("="*60)
        
        output_dir = self.ppo_dir / "afl-output"
        output_dir.mkdir(exist_ok=True)
        
        # Import fuzzing controller
        try:
            from fuzzing_controller import FuzzingController
        except ImportError:
            logger.error("Could not import FuzzingController. Ensure fuzzing_controller.py is available.")
            return False
        
        try:
            # Create controller
            controller = FuzzingController(
                binary_path=str(self.binary_path),
                input_dir=str(self.input_dir),
                output_dir=str(output_dir),
                config=self.config
            )
            
            # Override duration
            controller.max_duration = self.ppo_duration * 3600
            
            # Start fuzzing
            logger.info("Starting PPO-enhanced fuzzing...")
            if not controller.start_fuzzer():
                logger.error("Failed to start fuzzer")
                return False
            
            # Monitor and collect data
            start_time = time.time()
            duration_seconds = self.ppo_duration * 3600
            data_points = []
            
            while time.time() - start_time < duration_seconds:
                elapsed = time.time() - start_time
                
                # Perform training step
                if elapsed > 60:  # Wait 1 minute before first training step
                    stats = controller.training_step()
                    if stats:
                        data_points.append(stats)
                
                # Collect metrics
                metrics = self._collect_metrics(output_dir / "default")
                if metrics:
                    metrics['elapsed_time'] = elapsed
                    metrics['elapsed_hours'] = elapsed / 3600
                    
                    logger.info(f"PPO [{elapsed/3600:.2f}h]: "
                              f"Coverage={metrics.get('coverage', 0):.2f}%, "
                              f"Crashes={metrics.get('unique_crashes', 0)}, "
                              f"Paths={metrics.get('paths_total', 0)}")
                
                # Sleep until next collection
                time.sleep(self.collection_interval)
            
            # Stop fuzzing
            logger.info("Stopping PPO-enhanced fuzzing...")
            controller.stop_fuzzer()
            
            # Save final checkpoint
            controller.save_checkpoint(suffix="_final")
            
            # Save training data
            self._save_experiment_data(
                controller.training_stats,
                self.data_dir / "ppo_training_data.json"
            )
            
            logger.info("PPO experiment completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during PPO experiment: {e}", exc_info=True)
            return False
    
    def _collect_metrics(self, fuzzer_dir: Path) -> Optional[Dict]:
        """
        Collect metrics from AFL++ fuzzer_stats file.
        
        Args:
            fuzzer_dir: Directory containing fuzzer_stats
            
        Returns:
            Dictionary of metrics or None
        """
        stats_file = fuzzer_dir / "fuzzer_stats"
        
        if not stats_file.exists():
            return None
        
        try:
            metrics = {}
            
            with open(stats_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Parse common metrics
                        if key == 'execs_done':
                            metrics['total_execs'] = int(value)
                        elif key == 'execs_per_sec':
                            metrics['execs_per_sec'] = float(value)
                        elif key == 'paths_total':
                            metrics['paths_total'] = int(value)
                        elif key == 'saved_crashes':
                            metrics['unique_crashes'] = int(value)
                        elif key == 'saved_hangs':
                            metrics['unique_hangs'] = int(value)
                        elif key == 'bitmap_cvg':
                            metrics['coverage'] = float(value.replace('%', ''))
                        elif key == 'stability':
                            metrics['stability'] = float(value.replace('%', ''))
                        elif key == 'cycles_done':
                            metrics['cycles_done'] = int(value)
                        elif key == 'pending_favs':
                            metrics['pending_favs'] = int(value)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return None
    
    def _save_experiment_data(self, data: List[Dict], filepath: Path):
        """Save experiment data to JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Data saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def run_all_experiments(self):
        """Run both baseline and PPO experiments in sequence."""
        logger.info("\n" + "="*60)
        logger.info("STARTING ALL EXPERIMENTS")
        logger.info("="*60 + "\n")
        
        # Record start time
        overall_start = time.time()
        
        # Run baseline
        logger.info("PHASE 1: Baseline Experiment")
        baseline_success = self.run_baseline_experiment()
        
        if not baseline_success:
            logger.error("Baseline experiment failed. Aborting.")
            return False
        
        logger.info("\n" + "-"*60 + "\n")
        
        # Run PPO
        logger.info("PHASE 2: PPO-Enhanced Experiment")
        ppo_success = self.run_ppo_experiment()
        
        if not ppo_success:
            logger.error("PPO experiment failed.")
            return False
        
        # Calculate total time
        total_time = time.time() - overall_start
        
        logger.info("\n" + "="*60)
        logger.info("ALL EXPERIMENTS COMPLETED")
        logger.info("="*60)
        logger.info(f"Total time: {total_time/3600:.2f} hours")
        logger.info(f"Results saved to: {self.results_dir}")
        
        # Generate summary
        self._generate_summary()
        
        return True
    
    def _generate_summary(self):
        """Generate summary of experimental results."""
        logger.info("\nGenerating experiment summary...")
        
        summary = {
            'experiment_date': datetime.now().isoformat(),
            'binary': str(self.binary_path),
            'baseline_duration_hours': self.baseline_duration,
            'ppo_duration_hours': self.ppo_duration,
            'results_directory': str(self.results_dir)
        }
        
        # Load data files
        baseline_file = self.data_dir / "baseline_data.json"
        ppo_file = self.data_dir / "ppo_training_data.json"
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)
                if baseline_data:
                    final = baseline_data[-1]
                    summary['baseline_final'] = {
                        'coverage': final.get('coverage', 0),
                        'unique_crashes': final.get('unique_crashes', 0),
                        'paths_total': final.get('paths_total', 0),
                        'execs_per_sec': final.get('execs_per_sec', 0)
                    }
        
        if ppo_file.exists():
            with open(ppo_file, 'r') as f:
                ppo_data = json.load(f)
                if ppo_data:
                    summary['ppo_training_steps'] = len(ppo_data)
        
        # Save summary
        summary_file = self.results_dir / "experiment_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary saved to {summary_file}")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("EXPERIMENT SUMMARY")
        logger.info("="*60)
        for key, value in summary.items():
            if isinstance(value, dict):
                logger.info(f"{key}:")
                for k, v in value.items():
                    logger.info(f"  {k}: {v}")
            else:
                logger.info(f"{key}: {value}")
        logger.info("="*60 + "\n")


def main():
    """Main entry point for experiment runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run AFL++ Fuzzing Experiments')
    parser.add_argument('binary', help='Path to target binary')
    parser.add_argument('--input', '-i', required=True, help='Input corpus directory')
    parser.add_argument('--results', '-r', required=True, help='Results directory')
    parser.add_argument('--baseline-duration', type=float, default=2.0, 
                       help='Baseline duration in hours (default: 2.0)')
    parser.add_argument('--ppo-duration', type=float, default=2.0,
                       help='PPO duration in hours (default: 2.0)')
    parser.add_argument('--collection-interval', type=int, default=60,
                       help='Data collection interval in seconds (default: 60)')
    parser.add_argument('--mode', choices=['all', 'baseline', 'ppo'], default='all',
                       help='Which experiments to run')
    
    args = parser.parse_args()
    
    # Build configuration
    config = {
        'baseline_duration': args.baseline_duration,
        'ppo_duration': args.ppo_duration,
        'collection_interval': args.collection_interval,
        'experiment': {
            'update_interval': 300,  # 5 minutes
            'checkpoint_interval': 3600  # 1 hour
        }
    }
    
    # Create runner
    runner = ExperimentRunner(
        binary_path=args.binary,
        input_dir=args.input,
        results_dir=args.results,
        config=config
    )
    
    # Run experiments
    if args.mode == 'all':
        success = runner.run_all_experiments()
    elif args.mode == 'baseline':
        success = runner.run_baseline_experiment()
    elif args.mode == 'ppo':
        success = runner.run_ppo_experiment()
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)
    
    if success:
        logger.info("Experiments completed successfully!")
        sys.exit(0)
    else:
        logger.error("Experiments failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
