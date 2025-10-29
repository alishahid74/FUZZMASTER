"""
Simulation Script for Testing Phase 3
Generates realistic sample data without running full experiments.
Useful for testing analysis and visualization pipeline.
"""

import json
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_baseline_data(duration_hours: float = 2.0, interval_seconds: float = 60.0) -> list:
    """
    Generate simulated baseline AFL++ data.
    
    Args:
        duration_hours: Duration of simulation in hours
        interval_seconds: Data collection interval
        
    Returns:
        List of data points
    """
    num_points = int((duration_hours * 3600) / interval_seconds)
    data = []
    
    # Initial values
    coverage = 10.0
    crashes = 0
    paths = 50
    execs = 0
    execs_per_sec = 150.0
    
    for i in range(num_points):
        elapsed = i * interval_seconds
        
        # Simulate coverage growth (logarithmic)
        coverage += np.random.uniform(0.3, 0.8) * np.exp(-elapsed / 7200)
        coverage = min(coverage, 65.0)  # Cap at 65% for baseline
        
        # Simulate crash discovery (rare events)
        if np.random.random() < 0.05:  # 5% chance per interval
            crashes += np.random.randint(1, 3)
        
        # Simulate path growth
        paths += np.random.randint(2, 8)
        
        # Simulate executions
        execs += int(execs_per_sec * interval_seconds)
        execs_per_sec = 150.0 + np.random.uniform(-10, 10)
        
        # Create data point
        point = {
            'elapsed_time': elapsed,
            'coverage': float(coverage),
            'unique_crashes': int(crashes),
            'unique_hangs': 0,
            'paths_total': int(paths),
            'total_execs': int(execs),
            'execs_per_sec': float(execs_per_sec),
            'stability': float(95.0 + np.random.uniform(-2, 2)),
            'cycles_done': int(elapsed / 1800),  # Cycle every 30 min
            'pending_favs': int(10 + np.random.randint(-2, 5))
        }
        
        data.append(point)
    
    return data


def generate_ppo_data(duration_hours: float = 2.0, interval_seconds: float = 300.0) -> list:
    """
    Generate simulated PPO-enhanced data.
    Shows improvement over baseline.
    
    Args:
        duration_hours: Duration of simulation in hours
        interval_seconds: Update interval (PPO updates every 5 min)
        
    Returns:
        List of training data points
    """
    num_points = int((duration_hours * 3600) / interval_seconds)
    data = []
    
    # Initial values (start similar to baseline)
    coverage = 12.0
    crashes = 0
    paths = 60
    execs = 0
    execs_per_sec = 220.0  # Faster due to better mutation selection
    
    for i in range(num_points):
        elapsed = i * interval_seconds
        
        # PPO learns over time, so improvement accelerates
        learning_boost = min(1.5, 1.0 + (elapsed / 7200) * 0.5)
        
        # Simulate better coverage growth
        coverage += np.random.uniform(0.8, 1.5) * learning_boost
        coverage = min(coverage, 82.0)  # Cap at 82% for PPO
        
        # Simulate better crash discovery
        if np.random.random() < 0.08:  # 8% chance (higher than baseline)
            crashes += np.random.randint(1, 4)
        
        # Simulate more path discovery
        paths += np.random.randint(5, 12)
        
        # Simulate faster execution
        execs += int(execs_per_sec * interval_seconds)
        execs_per_sec = 220.0 + np.random.uniform(-15, 15)
        
        # Select random mutation strategy
        action = np.random.randint(0, 8)
        strategy_names = ['BITFLIP', 'BYTEFLIP', 'ARITHMETIC', 'INTERESTING',
                         'HAVOC_LIGHT', 'HAVOC_MEDIUM', 'HAVOC_HEAVY', 'SPLICE']
        
        # Simulate reward
        prev_coverage = data[-1]['state'][0] * 100 if data else 10.0
        coverage_reward = (coverage - prev_coverage) * 10.0
        crash_reward = (crashes - (data[-1].get('unique_crashes', 0) if data else 0)) * 50.0
        reward = coverage_reward + crash_reward + np.random.uniform(0, 5)
        
        # Create PPO training point
        point = {
            'elapsed_time': elapsed,
            'coverage': float(coverage),
            'unique_crashes': int(crashes),
            'unique_hangs': 0,
            'paths_total': int(paths),
            'total_execs': int(execs),
            'execs_per_sec': float(execs_per_sec),
            'stability': float(96.0 + np.random.uniform(-2, 2)),
            'cycles_done': int(elapsed / 1800),
            'pending_favs': int(8 + np.random.randint(-2, 4)),
            'episode': i,
            'action': int(action),
            'strategy': strategy_names[action],
            'reward': float(reward),
            'state': [
                coverage / 100.0,
                np.random.uniform(0, 0.1),
                crashes / 100.0,
                np.random.uniform(0, 0.05),
                execs_per_sec / 1000.0,
                paths / 1000.0,
                np.random.uniform(0, 0.1),
                0.96,
                elapsed / 36000,
                0.08
            ],
            'done': False
        }
        
        # Add occasional PPO update stats
        if i % 3 == 0:  # Every 3 updates
            point['policy_loss'] = float(np.random.uniform(0.01, 0.1))
            point['value_loss'] = float(np.random.uniform(0.001, 0.05))
            point['entropy'] = float(np.random.uniform(0.5, 1.5))
            point['mean_return'] = float(reward + np.random.uniform(-10, 10))
        
        data.append(point)
    
    return data


def create_sample_experiment(output_dir: str):
    """
    Create a complete sample experiment with realistic data.
    
    Args:
        output_dir: Directory to save sample data
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create data directory
    data_dir = output_path / "data"
    data_dir.mkdir(exist_ok=True)
    
    logger.info("Generating sample baseline data...")
    baseline_data = generate_baseline_data(duration_hours=2.0, interval_seconds=60.0)
    
    baseline_file = data_dir / "baseline_data.json"
    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    logger.info(f"Saved {len(baseline_data)} baseline points to {baseline_file}")
    
    logger.info("Generating sample PPO data...")
    ppo_data = generate_ppo_data(duration_hours=2.0, interval_seconds=300.0)
    
    ppo_file = data_dir / "ppo_training_data.json"
    with open(ppo_file, 'w') as f:
        json.dump(ppo_data, f, indent=2)
    logger.info(f"Saved {len(ppo_data)} PPO points to {ppo_file}")
    
    # Create summary
    summary = {
        'experiment_date': '2025-10-22T12:00:00',
        'binary': 'binaries/openssl-1.1.1f/apps/openssl',
        'baseline_duration_hours': 2.0,
        'ppo_duration_hours': 2.0,
        'results_directory': str(output_path),
        'note': 'This is simulated data for testing purposes',
        'baseline_final': {
            'coverage': baseline_data[-1]['coverage'],
            'unique_crashes': baseline_data[-1]['unique_crashes'],
            'paths_total': baseline_data[-1]['paths_total'],
            'execs_per_sec': baseline_data[-1]['execs_per_sec']
        },
        'ppo_final': {
            'coverage': ppo_data[-1]['coverage'],
            'unique_crashes': ppo_data[-1]['unique_crashes'],
            'paths_total': ppo_data[-1]['paths_total'],
            'execs_per_sec': ppo_data[-1]['execs_per_sec']
        }
    }
    
    summary_file = output_path / "experiment_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved summary to {summary_file}")
    
    logger.info("\n" + "="*60)
    logger.info("Sample Experiment Data Generated Successfully!")
    logger.info("="*60)
    logger.info(f"Location: {output_path}")
    logger.info(f"Baseline points: {len(baseline_data)}")
    logger.info(f"PPO points: {len(ppo_data)}")
    logger.info("\nYou can now test analysis and visualization:")
    logger.info(f"  python data_analysis.py {output_dir}")
    logger.info(f"  python visualizer.py {output_dir}")
    logger.info("="*60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Sample Experimental Data')
    parser.add_argument('--output', '-o', default='results/sample-experiment',
                       help='Output directory for sample data')
    parser.add_argument('--baseline-hours', type=float, default=2.0,
                       help='Simulated baseline duration')
    parser.add_argument('--ppo-hours', type=float, default=2.0,
                       help='Simulated PPO duration')
    
    args = parser.parse_args()
    
    create_sample_experiment(args.output)


if __name__ == "__main__":
    main()
