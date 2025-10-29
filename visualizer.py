"""
Visualization Generator for AFL++ Experiments
Creates publication-quality graphs for research paper.
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set publication-quality style
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.figsize'] = (8, 5)


class ExperimentVisualizer:
    """
    Creates visualizations for experimental results.
    """
    
    def __init__(self, results_dir: str):
        """
        Initialize visualizer.
        
        Args:
            results_dir: Directory containing experimental results
        """
        self.results_dir = Path(results_dir)
        self.data_dir = self.results_dir / "data"
        self.graphs_dir = self.results_dir / "graphs"
        self.graphs_dir.mkdir(exist_ok=True)
        
        # Load data
        self.baseline_data = self._load_data(self.data_dir / "baseline_data.json")
        self.ppo_data = self._load_data(self.data_dir / "ppo_training_data.json")
        
        logger.info(f"Visualizer initialized with {len(self.baseline_data)} baseline points, "
                   f"{len(self.ppo_data)} PPO points")
    
    def _load_data(self, filepath: Path) -> List[Dict]:
        """Load data from JSON file."""
        if not filepath.exists():
            logger.warning(f"Data file not found: {filepath}")
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    
    def extract_time_series(self, data: List[Dict], metric: str) -> Tuple[np.ndarray, np.ndarray]:
        """Extract time series for a metric."""
        times = []
        values = []
        
        for point in data:
            if metric in point and 'elapsed_time' in point:
                times.append(point['elapsed_time'] / 3600)  # Convert to hours
                values.append(point[metric])
        
        return np.array(times), np.array(values)
    
    def plot_coverage_over_time(self, save_path: Optional[str] = None):
        """
        Generate Figure 1: Code Coverage Over Time
        """
        baseline_times, baseline_cov = self.extract_time_series(self.baseline_data, 'coverage')
        ppo_times, ppo_cov = self.extract_time_series(self.ppo_data, 'coverage')
        
        fig, ax = plt.subplots(figsize=(8, 5))
        
        ax.plot(baseline_times, baseline_cov, marker='o', linestyle='-', 
                label='AFL++', color='#3498db', linewidth=2, markersize=4)
        ax.plot(ppo_times, ppo_cov, marker='s', linestyle='--', 
                label='AFL++ + PPO', color='#e74c3c', linewidth=2, markersize=4)
        
        ax.set_xlabel('Time (Hours)', fontweight='bold')
        ax.set_ylabel('Code Coverage (%)', fontweight='bold')
        ax.set_title('Code Coverage Over Time', fontweight='bold', pad=15)
        ax.legend(loc='lower right', frameon=True)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved coverage plot to {save_path}")
        else:
            plt.savefig(self.graphs_dir / 'fig1_coverage_over_time.png', 
                       dpi=300, bbox_inches='tight')
        
        plt.close()
    
    def plot_crash_discovery(self, save_path: Optional[str] = None):
        """
        Generate Figure 2: Crash Discovery Rate
        """
        baseline_times, baseline_crashes = self.extract_time_series(self.baseline_data, 'unique_crashes')
        ppo_times, ppo_crashes = self.extract_time_series(self.ppo_data, 'unique_crashes')
        
        fig, ax = plt.subplots(figsize=(8, 5))
        
        ax.plot(baseline_times, baseline_crashes, marker='o', linestyle='-',
                label='AFL++', color='#3498db', linewidth=2, markersize=4)
        ax.plot(ppo_times, ppo_crashes, marker='s', linestyle='--',
                label='AFL++ + PPO', color='#e74c3c', linewidth=2, markersize=4)
        
        ax.set_xlabel('Time (Hours)', fontweight='bold')
        ax.set_ylabel('Unique Crashes Discovered', fontweight='bold')
        ax.set_title('Crash Discovery Rate Over Time', fontweight='bold', pad=15)
        ax.legend(loc='upper left', frameon=True)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved crash plot to {save_path}")
        else:
            plt.savefig(self.graphs_dir / 'fig2_crash_discovery.png',
                       dpi=300, bbox_inches='tight')
        
        plt.close()
    
    def plot_execution_speed(self, save_path: Optional[str] = None):
        """
        Generate Figure 3: Execution Speed Comparison
        """
        baseline_times, baseline_speed = self.extract_time_series(self.baseline_data, 'execs_per_sec')
        ppo_times, ppo_speed = self.extract_time_series(self.ppo_data, 'execs_per_sec')
        
        # Compute average speeds
        avg_baseline = np.mean(baseline_speed) if len(baseline_speed) > 0 else 0
        avg_ppo = np.mean(ppo_speed) if len(ppo_speed) > 0 else 0
        
        fig, ax = plt.subplots(figsize=(6, 5))
        
        methods = ['AFL++', 'AFL++ + PPO']
        speeds = [avg_baseline, avg_ppo]
        colors = ['#3498db', '#e74c3c']
        
        bars = ax.bar(methods, speeds, color=colors, width=0.6, edgecolor='black', linewidth=1.5)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}',
                   ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('Execution Speed (Test Cases/sec)', fontweight='bold')
        ax.set_title('Average Execution Speed Comparison', fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved execution speed plot to {save_path}")
        else:
            plt.savefig(self.graphs_dir / 'fig3_execution_speed.png',
                       dpi=300, bbox_inches='tight')
        
        plt.close()
    
    def plot_path_exploration(self, save_path: Optional[str] = None):
        """
        Generate Figure 4: Path Exploration Comparison
        """
        baseline_times, baseline_paths = self.extract_time_series(self.baseline_data, 'paths_total')
        ppo_times, ppo_paths = self.extract_time_series(self.ppo_data, 'paths_total')
        
        # Get final values
        final_baseline = baseline_paths[-1] if len(baseline_paths) > 0 else 0
        final_ppo = ppo_paths[-1] if len(ppo_paths) > 0 else 0
        
        fig, ax = plt.subplots(figsize=(6, 5))
        
        methods = ['AFL++', 'AFL++ + PPO']
        paths = [final_baseline, final_ppo]
        colors = ['#3498db', '#e74c3c']
        
        bars = ax.bar(methods, paths, color=colors, width=0.6, edgecolor='black', linewidth=1.5)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('Unique Code Paths Explored', fontweight='bold')
        ax.set_title('Code Path Exploration Comparison', fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved path exploration plot to {save_path}")
        else:
            plt.savefig(self.graphs_dir / 'fig4_path_exploration.png',
                       dpi=300, bbox_inches='tight')
        
        plt.close()
    
    def plot_comparison_table(self, save_path: Optional[str] = None):
        """
        Generate a comparison table visualization.
        """
        # Extract final values
        metrics = ['coverage', 'unique_crashes', 'paths_total', 'execs_per_sec']
        
        baseline_final = {}
        ppo_final = {}
        
        for metric in metrics:
            _, baseline_vals = self.extract_time_series(self.baseline_data, metric)
            _, ppo_vals = self.extract_time_series(self.ppo_data, metric)
            
            baseline_final[metric] = baseline_vals[-1] if len(baseline_vals) > 0 else 0
            ppo_final[metric] = ppo_vals[-1] if len(ppo_vals) > 0 else 0
        
        # Create table data
        table_data = []
        for metric in metrics:
            baseline_val = baseline_final[metric]
            ppo_val = ppo_final[metric]
            improvement = ((ppo_val - baseline_val) / baseline_val * 100) if baseline_val != 0 else 0
            
            table_data.append([
                metric.replace('_', ' ').title(),
                f"{baseline_val:.2f}",
                f"{ppo_val:.2f}",
                f"{improvement:+.1f}%"
            ])
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.axis('tight')
        ax.axis('off')
        
        table = ax.table(
            cellText=table_data,
            colLabels=['Metric', 'AFL++', 'AFL++ + PPO', 'Improvement'],
            cellLoc='center',
            loc='center',
            colWidths=[0.3, 0.2, 0.2, 0.2]
        )
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # Style header
        for i in range(4):
            table[(0, i)].set_facecolor('#3498db')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Alternate row colors
        for i in range(1, len(table_data) + 1):
            for j in range(4):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#ecf0f1')
        
        plt.title('Performance Comparison Summary', fontweight='bold', pad=20, fontsize=12)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved comparison table to {save_path}")
        else:
            plt.savefig(self.graphs_dir / 'table_comparison.png',
                       dpi=300, bbox_inches='tight')
        
        plt.close()
    
    def generate_all_figures(self):
        """Generate all figures for the paper."""
        logger.info("Generating all figures...")
        
        self.plot_coverage_over_time()
        logger.info("✓ Figure 1: Coverage over time")
        
        self.plot_crash_discovery()
        logger.info("✓ Figure 2: Crash discovery")
        
        self.plot_execution_speed()
        logger.info("✓ Figure 3: Execution speed")
        
        self.plot_path_exploration()
        logger.info("✓ Figure 4: Path exploration")
        
        self.plot_comparison_table()
        logger.info("✓ Comparison table")
        
        logger.info(f"\nAll figures saved to: {self.graphs_dir}")
        logger.info("="*60)


def main():
    """Main entry point for visualization."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Visualizations for Experiments')
    parser.add_argument('results_dir', help='Directory containing experimental results')
    parser.add_argument('--figure', choices=['all', 'coverage', 'crashes', 'speed', 'paths', 'table'],
                       default='all', help='Which figure to generate')
    
    args = parser.parse_args()
    
    visualizer = ExperimentVisualizer(args.results_dir)
    
    if args.figure == 'all':
        visualizer.generate_all_figures()
    elif args.figure == 'coverage':
        visualizer.plot_coverage_over_time()
    elif args.figure == 'crashes':
        visualizer.plot_crash_discovery()
    elif args.figure == 'speed':
        visualizer.plot_execution_speed()
    elif args.figure == 'paths':
        visualizer.plot_path_exploration()
    elif args.figure == 'table':
        visualizer.plot_comparison_table()


if __name__ == "__main__":
    main()
