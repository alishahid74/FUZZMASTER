"""
Feedback Analyzer for AFL++ Output
This module processes AFL++ fuzzing results and converts them into
state representations and rewards for the PPO agent.
"""

import os
import re
import json
import time
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FuzzingMetrics:
    """Container for fuzzing metrics."""
    
    def __init__(self):
        self.coverage = 0.0
        self.unique_crashes = 0
        self.unique_hangs = 0
        self.total_execs = 0
        self.execs_per_sec = 0.0
        self.paths_total = 0
        self.paths_found = 0
        self.pending_favs = 0
        self.pending_total = 0
        self.bitmap_cvg = 0.0
        self.stability = 0.0
        self.levels = 0
        self.last_crash = 0
        self.last_hang = 0
        self.last_path = 0
        self.cycles_done = 0
        
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            'coverage': self.coverage,
            'unique_crashes': self.unique_crashes,
            'unique_hangs': self.unique_hangs,
            'total_execs': self.total_execs,
            'execs_per_sec': self.execs_per_sec,
            'paths_total': self.paths_total,
            'paths_found': self.paths_found,
            'bitmap_cvg': self.bitmap_cvg,
            'stability': self.stability,
            'cycles_done': self.cycles_done
        }
    
    def __str__(self) -> str:
        return (f"Coverage: {self.coverage:.2f}%, Crashes: {self.unique_crashes}, "
                f"Paths: {self.paths_total}, Exec/s: {self.execs_per_sec:.0f}")


class FeedbackAnalyzer:
    """
    Analyzes AFL++ fuzzing output and generates state representations
    and rewards for reinforcement learning.
    """
    
    def __init__(self, output_dir: str, history_size: int = 10):
        """
        Initialize the feedback analyzer.
        
        Args:
            output_dir: AFL++ output directory
            history_size: Number of historical states to maintain
        """
        self.output_dir = Path(output_dir)
        self.history_size = history_size
        
        # Fuzzer stats file
        self.fuzzer_stats_file = self.output_dir / "default" / "fuzzer_stats"
        
        # Historical data
        self.metrics_history: List[FuzzingMetrics] = []
        self.last_update_time = time.time()
        
        # Baseline metrics (for computing improvements)
        self.baseline_metrics: Optional[FuzzingMetrics] = None
        
        # State normalization parameters
        self.state_mean = None
        self.state_std = None
        
        logger.info(f"Feedback Analyzer initialized for: {output_dir}")
    
    def parse_fuzzer_stats(self) -> Optional[FuzzingMetrics]:
        """
        Parse AFL++ fuzzer_stats file.
        
        Returns:
            FuzzingMetrics object or None if parsing fails
        """
        if not self.fuzzer_stats_file.exists():
            logger.warning(f"Fuzzer stats file not found: {self.fuzzer_stats_file}")
            return None
        
        try:
            metrics = FuzzingMetrics()
            
            with open(self.fuzzer_stats_file, 'r') as f:
                content = f.read()
            
            # Parse key metrics using regex
            patterns = {
                'total_execs': r'execs_done\s*:\s*(\d+)',
                'execs_per_sec': r'execs_per_sec\s*:\s*([\d.]+)',
                'paths_total': r'paths_total\s*:\s*(\d+)',
                'unique_crashes': r'saved_crashes\s*:\s*(\d+)',
                'unique_hangs': r'saved_hangs\s*:\s*(\d+)',
                'bitmap_cvg': r'bitmap_cvg\s*:\s*([\d.]+)%',
                'stability': r'stability\s*:\s*([\d.]+)%',
                'pending_favs': r'pending_favs\s*:\s*(\d+)',
                'pending_total': r'pending_total\s*:\s*(\d+)',
                'cycles_done': r'cycles_done\s*:\s*(\d+)',
                'last_crash': r'last_crash\s*:\s*(\d+)',
                'last_path': r'last_path\s*:\s*(\d+)',
            }
            
            for attr, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    value = match.group(1)
                    if '.' in value:
                        setattr(metrics, attr, float(value))
                    else:
                        setattr(metrics, attr, int(value))
            
            # Calculate coverage as bitmap coverage percentage
            metrics.coverage = metrics.bitmap_cvg
            
            # Update paths_found
            metrics.paths_found = metrics.paths_total
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error parsing fuzzer stats: {e}")
            return None
    
    def get_current_metrics(self) -> Optional[FuzzingMetrics]:
        """
        Get current fuzzing metrics.
        
        Returns:
            Current FuzzingMetrics or None
        """
        return self.parse_fuzzer_stats()
    
    def update(self) -> bool:
        """
        Update metrics history with current fuzzing state.
        
        Returns:
            True if update successful, False otherwise
        """
        metrics = self.get_current_metrics()
        
        if metrics is None:
            return False
        
        # Add to history
        self.metrics_history.append(metrics)
        
        # Maintain history size
        if len(self.metrics_history) > self.history_size:
            self.metrics_history.pop(0)
        
        # Set baseline if not set
        if self.baseline_metrics is None:
            self.baseline_metrics = metrics
        
        self.last_update_time = time.time()
        
        return True
    
    def get_state_vector(self) -> np.ndarray:
        """
        Generate state vector for RL agent.
        
        State includes:
        - Current coverage
        - Coverage rate (change)
        - Crash count
        - Crash rate
        - Execution speed
        - Path count
        - Path discovery rate
        - Stability
        - Cycles completed
        - Pending interesting cases
        
        Returns:
            Normalized state vector
        """
        if len(self.metrics_history) == 0:
            # Return zero state if no metrics
            return np.zeros(10)
        
        current = self.metrics_history[-1]
        
        # Calculate rates if we have history
        if len(self.metrics_history) >= 2:
            previous = self.metrics_history[-2]
            time_delta = max(self.last_update_time - (self.last_update_time - 60), 1.0)  # Assume 60s interval
            
            coverage_rate = (current.coverage - previous.coverage) / time_delta
            crash_rate = (current.unique_crashes - previous.unique_crashes) / time_delta
            path_rate = (current.paths_total - previous.paths_total) / time_delta
        else:
            coverage_rate = 0.0
            crash_rate = 0.0
            path_rate = 0.0
        
        # Construct state vector
        state = np.array([
            current.coverage / 100.0,           # 0: Normalized coverage (0-1)
            coverage_rate,                       # 1: Coverage growth rate
            current.unique_crashes / 100.0,      # 2: Normalized crash count
            crash_rate,                          # 3: Crash discovery rate
            current.execs_per_sec / 1000.0,     # 4: Normalized exec speed
            current.paths_total / 1000.0,       # 5: Normalized path count
            path_rate,                           # 6: Path discovery rate
            current.stability / 100.0,           # 7: Normalized stability
            current.cycles_done / 10.0,         # 8: Normalized cycles
            current.pending_favs / 100.0,       # 9: Normalized pending cases
        ])
        
        return state
    
    def compute_reward(self) -> float:
        """
        Compute reward signal for RL agent.
        
        Reward components:
        - Coverage improvement (most important)
        - New crashes discovered
        - Path diversity
        - Execution speed
        
        Returns:
            Reward value
        """
        if len(self.metrics_history) < 2:
            return 0.0
        
        current = self.metrics_history[-1]
        previous = self.metrics_history[-2]
        
        # Coverage improvement reward (highest weight)
        coverage_reward = (current.coverage - previous.coverage) * 10.0
        
        # Crash discovery reward
        crash_reward = (current.unique_crashes - previous.unique_crashes) * 50.0
        
        # Path discovery reward
        path_reward = (current.paths_total - previous.paths_total) * 1.0
        
        # Execution speed reward (small bonus for maintaining speed)
        speed_reward = min(current.execs_per_sec / 1000.0, 1.0) * 0.5
        
        # Stability penalty (want stable fuzzing)
        stability_reward = (current.stability / 100.0) * 0.5
        
        # Total reward
        reward = coverage_reward + crash_reward + path_reward + speed_reward + stability_reward
        
        return reward
    
    def get_state_and_reward(self) -> Tuple[np.ndarray, float]:
        """
        Get current state and reward.
        
        Returns:
            Tuple of (state_vector, reward)
        """
        state = self.get_state_vector()
        reward = self.compute_reward()
        
        return state, reward
    
    def is_done(self) -> bool:
        """
        Check if fuzzing episode should terminate.
        
        Returns:
            True if episode is done
        """
        if len(self.metrics_history) == 0:
            return False
        
        current = self.metrics_history[-1]
        
        # Terminate if no progress for extended period
        if len(self.metrics_history) >= self.history_size:
            # Check if coverage hasn't improved
            first = self.metrics_history[0]
            if current.coverage <= first.coverage and current.paths_total <= first.paths_total:
                return True
        
        return False
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics.
        
        Returns:
            Dictionary of summary statistics
        """
        if len(self.metrics_history) == 0:
            return {}
        
        current = self.metrics_history[-1]
        
        summary = {
            'current_metrics': current.to_dict(),
            'history_length': len(self.metrics_history),
            'baseline_set': self.baseline_metrics is not None,
        }
        
        if self.baseline_metrics:
            summary['improvement'] = {
                'coverage': current.coverage - self.baseline_metrics.coverage,
                'crashes': current.unique_crashes - self.baseline_metrics.unique_crashes,
                'paths': current.paths_total - self.baseline_metrics.paths_total,
            }
        
        return summary
    
    def save_history(self, filepath: str):
        """Save metrics history to file."""
        history_data = [m.to_dict() for m in self.metrics_history]
        
        with open(filepath, 'w') as f:
            json.dump(history_data, f, indent=2)
        
        logger.info(f"Metrics history saved to {filepath}")
    
    def load_history(self, filepath: str):
        """Load metrics history from file."""
        with open(filepath, 'r') as f:
            history_data = json.load(f)
        
        self.metrics_history.clear()
        for data in history_data:
            metrics = FuzzingMetrics()
            for key, value in data.items():
                setattr(metrics, key, value)
            self.metrics_history.append(metrics)
        
        logger.info(f"Metrics history loaded from {filepath}")


if __name__ == "__main__":
    # Test the feedback analyzer
    print("Testing Feedback Analyzer...")
    
    # Create a mock output directory
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()
        (output_dir / "default").mkdir()
        
        # Create a mock fuzzer_stats file
        stats_file = output_dir / "default" / "fuzzer_stats"
        stats_content = """
start_time        : 1234567890
last_update       : 1234567900
fuzzer_pid        : 12345
cycles_done       : 5
execs_done        : 100000
execs_per_sec     : 2500.50
paths_total       : 150
paths_found       : 150
saved_crashes     : 3
saved_hangs       : 1
bitmap_cvg        : 45.67%
stability         : 98.50%
pending_favs      : 10
pending_total     : 25
last_path         : 1234567895
last_crash        : 1234567890
"""
        with open(stats_file, 'w') as f:
            f.write(stats_content)
        
        # Test analyzer
        analyzer = FeedbackAnalyzer(str(output_dir))
        
        # Test parsing
        metrics = analyzer.get_current_metrics()
        print(f"Parsed metrics: {metrics}")
        
        # Test update
        analyzer.update()
        state, reward = analyzer.get_state_and_reward()
        print(f"State vector shape: {state.shape}")
        print(f"State vector: {state}")
        print(f"Reward: {reward}")
        
        # Test summary
        summary = analyzer.get_summary()
        print(f"Summary: {json.dumps(summary, indent=2)}")
        
        print("Feedback Analyzer test completed!")
