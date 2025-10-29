"""
AFL++ + PPO Fuzzing Controller
Main integration module that coordinates the PPO agent, feedback analyzer,
and mutation strategy selector with AFL++ fuzzing.
"""

import os
import sys
import time
import signal
import subprocess
import json
import numpy as np
from pathlib import Path
from typing import Optional, Dict
import logging
from datetime import datetime

# Import our modules
from ppo_agent import PPOAgent
from feedback_analyzer import FeedbackAnalyzer
from mutation_selector import MutationStrategySelector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FuzzingController:
    """
    Main controller that orchestrates AFL++ fuzzing with PPO optimization.
    """
    
    def __init__(
        self,
        binary_path: str,
        input_dir: str,
        output_dir: str,
        afl_args: Optional[list] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize the fuzzing controller.
        
        Args:
            binary_path: Path to target binary
            input_dir: Directory with initial test cases
            output_dir: AFL++ output directory
            afl_args: Additional AFL++ arguments
            config: Configuration dictionary
        """
        self.binary_path = Path(binary_path)
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.afl_args = afl_args or []
        self.config = config or {}
        
        # Validate paths
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {binary_path}")
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get configuration
        ppo_config = self.config.get('ppo', {})
        experiment_config = self.config.get('experiment', {})
        
        # Initialize components
        self.state_dim = 10  # As defined in FeedbackAnalyzer
        self.mutation_selector = MutationStrategySelector()
        self.action_dim = self.mutation_selector.get_num_actions()
        
        self.agent = PPOAgent(
            state_dim=self.state_dim,
            action_dim=self.action_dim,
            hidden_dim=ppo_config.get('hidden_dim', 128),
            learning_rate=ppo_config.get('learning_rate', 3e-4),
            gamma=ppo_config.get('gamma', 0.99),
            gae_lambda=ppo_config.get('gae_lambda', 0.95),
            clip_epsilon=ppo_config.get('clip_epsilon', 0.2),
            value_coef=ppo_config.get('value_coef', 0.5),
            entropy_coef=ppo_config.get('entropy_coef', 0.01),
        )
        
        self.feedback_analyzer = FeedbackAnalyzer(
            output_dir=str(self.output_dir),
            history_size=experiment_config.get('history_size', 10)
        )
        
        # Fuzzing process
        self.fuzzer_process: Optional[subprocess.Popen] = None
        self.running = False
        
        # Training parameters
        self.update_interval = experiment_config.get('update_interval', 300)  # 5 minutes
        self.max_duration = experiment_config.get('duration_hours', 8) * 3600  # Convert to seconds
        self.checkpoint_interval = experiment_config.get('checkpoint_interval', 3600)  # 1 hour
        
        # Statistics
        self.start_time = None
        self.episodes = 0
        self.total_updates = 0
        self.training_stats = []
        
        # Checkpoint directory
        self.checkpoint_dir = self.output_dir / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        logger.info("Fuzzing Controller initialized")
        logger.info(f"Binary: {self.binary_path}")
        logger.info(f"Input: {self.input_dir}")
        logger.info(f"Output: {self.output_dir}")
        logger.info(f"Max duration: {self.max_duration/3600:.1f} hours")
    
    def start_fuzzer(self) -> bool:
        """
        Start AFL++ fuzzer process.
        
        Returns:
            True if started successfully
        """
        try:
            # Build AFL++ command
            afl_cmd = [
                'afl-fuzz',
                '-i', str(self.input_dir),
                '-o', str(self.output_dir),
                '-Q',  # QEMU mode
                '-m', 'none',  # No memory limit
            ] + self.afl_args + ['--', str(self.binary_path)]
            
            logger.info(f"Starting AFL++: {' '.join(afl_cmd)}")
            
            # Start fuzzer in background
            self.fuzzer_process = subprocess.Popen(
                afl_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Wait a bit to ensure it started
            time.sleep(5)
            
            if self.fuzzer_process.poll() is not None:
                # Process died
                stderr = self.fuzzer_process.stderr.read().decode()
                logger.error(f"AFL++ failed to start: {stderr}")
                return False
            
            logger.info(f"AFL++ started with PID: {self.fuzzer_process.pid}")
            self.running = True
            return True
            
        except Exception as e:
            logger.error(f"Error starting AFL++: {e}")
            return False
    
    def stop_fuzzer(self):
        """Stop AFL++ fuzzer process."""
        if self.fuzzer_process and self.running:
            try:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self.fuzzer_process.pid), signal.SIGTERM)
                
                # Wait for termination
                self.fuzzer_process.wait(timeout=10)
                logger.info("AFL++ stopped gracefully")
                
            except subprocess.TimeoutExpired:
                # Force kill if necessary
                os.killpg(os.getpgid(self.fuzzer_process.pid), signal.SIGKILL)
                logger.warning("AFL++ force killed")
            except Exception as e:
                logger.error(f"Error stopping AFL++: {e}")
            
            self.running = False
    
    def training_step(self) -> Dict:
        """
        Perform one training step: collect data, update agent.
        
        Returns:
            Dictionary of training statistics
        """
        # Update feedback analyzer
        if not self.feedback_analyzer.update():
            logger.warning("Failed to update feedback analyzer")
            return {}
        
        # Get current state and reward
        state, reward = self.feedback_analyzer.get_state_and_reward()
        
        # Select action
        action = self.agent.select_action(state)
        
        # Apply mutation strategy
        strategy = self.mutation_selector.select_strategy(action)
        logger.info(f"Selected mutation strategy: {strategy.name}")
        
        # Store transition
        done = self.feedback_analyzer.is_done()
        self.agent.store_transition(reward, done)
        
        # Update strategy stats
        current_metrics = self.feedback_analyzer.get_current_metrics()
        if current_metrics and len(self.feedback_analyzer.metrics_history) >= 2:
            prev_metrics = self.feedback_analyzer.metrics_history[-2]
            self.mutation_selector.update_strategy_stats(
                coverage_gain=current_metrics.coverage - prev_metrics.coverage,
                crashes=current_metrics.unique_crashes - prev_metrics.unique_crashes,
                paths=current_metrics.paths_total - prev_metrics.paths_total
            )
        
        # Perform PPO update if we have enough data
        update_stats = {}
        if len(self.agent.states) >= 32:  # Minimum batch size
            update_stats = self.agent.update(n_epochs=10, batch_size=32)
            self.total_updates += 1
            logger.info(f"PPO update #{self.total_updates} completed")
            if update_stats:
                logger.info(f"  Policy loss: {update_stats['policy_loss']:.4f}")
                logger.info(f"  Value loss: {update_stats['value_loss']:.4f}")
                logger.info(f"  Mean return: {update_stats['mean_return']:.4f}")
        
        stats = {
            'episode': self.episodes,
            'action': action,
            'strategy': strategy.name,
            'reward': reward,
            'state': state.tolist(),
            'done': done,
        }
        
        if update_stats:
            stats.update(update_stats)
        
        if done:
            self.episodes += 1
            logger.info(f"Episode {self.episodes} completed")
        
        return stats
    
    def save_checkpoint(self, suffix: str = ""):
        """
        Save a checkpoint of the current state.
        
        Args:
            suffix: Optional suffix for checkpoint name
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = f"checkpoint_{timestamp}{suffix}"
        checkpoint_path = self.checkpoint_dir / checkpoint_name
        checkpoint_path.mkdir(exist_ok=True)
        
        # Save agent
        self.agent.save(str(checkpoint_path / "agent.pt"))
        
        # Save feedback history
        self.feedback_analyzer.save_history(str(checkpoint_path / "metrics_history.json"))
        
        # Save strategy stats
        strategy_stats = {
            'performance': self.mutation_selector.get_strategy_performance(),
            'distribution': self.mutation_selector.get_strategy_distribution()
        }
        with open(checkpoint_path / "strategy_stats.json", 'w') as f:
            json.dump(strategy_stats, f, indent=2)
        
        # Save training stats
        with open(checkpoint_path / "training_stats.json", 'w') as f:
            json.dump(self.training_stats, f, indent=2)
        
        logger.info(f"Checkpoint saved: {checkpoint_path}")
    
    def run(self):
        """
        Main training loop: run AFL++ with PPO optimization.
        """
        logger.info("Starting fuzzing with PPO optimization...")
        
        # Start AFL++
        if not self.start_fuzzer():
            logger.error("Failed to start fuzzer")
            return
        
        self.start_time = time.time()
        last_update = self.start_time
        last_checkpoint = self.start_time
        
        try:
            while self.running:
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                # Check if we've exceeded max duration
                if elapsed >= self.max_duration:
                    logger.info(f"Max duration reached: {elapsed/3600:.1f} hours")
                    break
                
                # Perform training step at regular intervals
                if current_time - last_update >= self.update_interval:
                    logger.info(f"Training step at {elapsed/3600:.2f} hours")
                    
                    stats = self.training_step()
                    if stats:
                        stats['elapsed_time'] = elapsed
                        self.training_stats.append(stats)
                    
                    # Print current metrics
                    summary = self.feedback_analyzer.get_summary()
                    if summary:
                        logger.info(f"Current metrics: {summary.get('current_metrics', {})}")
                    
                    last_update = current_time
                
                # Save checkpoint periodically
                if current_time - last_checkpoint >= self.checkpoint_interval:
                    self.save_checkpoint(suffix="_periodic")
                    last_checkpoint = current_time
                
                # Sleep briefly
                time.sleep(10)
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
        
        except Exception as e:
            logger.error(f"Error during fuzzing: {e}", exc_info=True)
        
        finally:
            # Cleanup
            logger.info("Stopping fuzzer and saving final checkpoint...")
            self.stop_fuzzer()
            self.save_checkpoint(suffix="_final")
            
            # Print final summary
            self.print_summary()
    
    def print_summary(self):
        """Print final summary of the fuzzing session."""
        logger.info("\n" + "="*60)
        logger.info("FUZZING SESSION SUMMARY")
        logger.info("="*60)
        
        if self.start_time:
            duration = time.time() - self.start_time
            logger.info(f"Duration: {duration/3600:.2f} hours")
        
        logger.info(f"Episodes: {self.episodes}")
        logger.info(f"PPO Updates: {self.total_updates}")
        
        # Feedback summary
        feedback_summary = self.feedback_analyzer.get_summary()
        if feedback_summary:
            logger.info("\nFinal Metrics:")
            for key, value in feedback_summary.get('current_metrics', {}).items():
                logger.info(f"  {key}: {value}")
            
            if 'improvement' in feedback_summary:
                logger.info("\nImprovement from Baseline:")
                for key, value in feedback_summary['improvement'].items():
                    logger.info(f"  {key}: {value:+.2f}")
        
        # Strategy summary
        logger.info("\n" + self.mutation_selector.get_summary())
        
        logger.info("\n" + "="*60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AFL++ with PPO Optimization')
    parser.add_argument('binary', help='Path to target binary')
    parser.add_argument('--input', '-i', required=True, help='Input corpus directory')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--config', '-c', help='Configuration file (YAML/JSON)')
    parser.add_argument('--duration', '-d', type=float, default=8.0, help='Duration in hours')
    parser.add_argument('--update-interval', '-u', type=int, default=300, help='Update interval in seconds')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        'experiment': {
            'duration_hours': args.duration,
            'update_interval': args.update_interval
        }
    }
    
    if args.config:
        import yaml
        with open(args.config) as f:
            loaded_config = yaml.safe_load(f)
            config.update(loaded_config)
    
    # Create controller
    controller = FuzzingController(
        binary_path=args.binary,
        input_dir=args.input,
        output_dir=args.output,
        config=config
    )
    
    # Run fuzzing
    controller.run()


if __name__ == "__main__":
    main()
