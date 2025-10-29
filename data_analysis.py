"""
Data Analysis for AFL++ Experiments
Processes collected data and computes statistics for comparison.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from scipy import stats
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExperimentAnalyzer:
    """
    Analyzes experimental data from baseline and PPO runs.
    """
    
    def __init__(self, results_dir: str):
        """
        Initialize analyzer.
        
        Args:
            results_dir: Directory containing experimental results
        """
        self.results_dir = Path(results_dir)
        self.data_dir = self.results_dir / "data"
        
        # Load data
        self.baseline_data = self._load_data(self.data_dir / "baseline_data.json")
        self.ppo_data = self._load_data(self.data_dir / "ppo_training_data.json")
        
        logger.info(f"Loaded baseline data: {len(self.baseline_data)} points")
        logger.info(f"Loaded PPO data: {len(self.ppo_data)} points")
    
    def _load_data(self, filepath: Path) -> List[Dict]:
        """Load data from JSON file."""
        if not filepath.exists():
            logger.warning(f"Data file not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error loading data from {filepath}: {e}")
            return []
    
    def extract_time_series(self, data: List[Dict], metric: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract time series for a specific metric.
        
        Args:
            data: List of data points
            metric: Metric name to extract
            
        Returns:
            Tuple of (time_array, values_array)
        """
        times = []
        values = []
        
        for point in data:
            if metric in point and 'elapsed_time' in point:
                times.append(point['elapsed_time'])
                values.append(point[metric])
        
        return np.array(times), np.array(values)
    
    def compute_statistics(self) -> Dict:
        """
        Compute comprehensive statistics for both experiments.
        
        Returns:
            Dictionary of statistical results
        """
        stats_dict = {}
        
        # Metrics to analyze
        metrics = ['coverage', 'unique_crashes', 'paths_total', 'execs_per_sec']
        
        for metric in metrics:
            baseline_times, baseline_values = self.extract_time_series(self.baseline_data, metric)
            ppo_times, ppo_values = self.extract_time_series(self.ppo_data, metric)
            
            if len(baseline_values) == 0 or len(ppo_values) == 0:
                continue
            
            stats_dict[metric] = {
                'baseline': {
                    'initial': float(baseline_values[0]) if len(baseline_values) > 0 else 0,
                    'final': float(baseline_values[-1]) if len(baseline_values) > 0 else 0,
                    'mean': float(np.mean(baseline_values)),
                    'std': float(np.std(baseline_values)),
                    'max': float(np.max(baseline_values)),
                    'min': float(np.min(baseline_values))
                },
                'ppo': {
                    'initial': float(ppo_values[0]) if len(ppo_values) > 0 else 0,
                    'final': float(ppo_values[-1]) if len(ppo_values) > 0 else 0,
                    'mean': float(np.mean(ppo_values)),
                    'std': float(np.std(ppo_values)),
                    'max': float(np.max(ppo_values)),
                    'min': float(np.min(ppo_values))
                }
            }
            
            # Compute improvement
            if len(baseline_values) > 0 and len(ppo_values) > 0:
                baseline_final = baseline_values[-1]
                ppo_final = ppo_values[-1]
                
                if baseline_final != 0:
                    improvement = ((ppo_final - baseline_final) / baseline_final) * 100
                else:
                    improvement = 0
                
                stats_dict[metric]['improvement'] = {
                    'absolute': float(ppo_final - baseline_final),
                    'percentage': float(improvement)
                }
            
            # Statistical test (Mann-Whitney U test)
            if len(baseline_values) >= 3 and len(ppo_values) >= 3:
                try:
                    u_stat, p_value = stats.mannwhitneyu(ppo_values, baseline_values, alternative='greater')
                    stats_dict[metric]['statistical_test'] = {
                        'test': 'Mann-Whitney U',
                        'u_statistic': float(u_stat),
                        'p_value': float(p_value),
                        'significant': bool(p_value < 0.05)
                    }
                except Exception as e:
                    logger.warning(f"Could not perform statistical test for {metric}: {e}")
        
        return stats_dict
    
    def generate_comparison_table(self) -> pd.DataFrame:
        """
        Generate comparison table for final metrics.
        
        Returns:
            Pandas DataFrame with comparison
        """
        stats = self.compute_statistics()
        
        rows = []
        for metric, data in stats.items():
            baseline_final = data['baseline']['final']
            ppo_final = data['ppo']['final']
            improvement = data.get('improvement', {}).get('percentage', 0)
            
            rows.append({
                'Metric': metric.replace('_', ' ').title(),
                'Baseline (AFL++)': f"{baseline_final:.2f}",
                'PPO-Enhanced': f"{ppo_final:.2f}",
                'Improvement (%)': f"{improvement:+.2f}%"
            })
        
        df = pd.DataFrame(rows)
        return df
    
    def generate_coverage_analysis(self) -> Dict:
        """
        Detailed analysis of coverage growth over time.
        
        Returns:
            Dictionary with coverage analysis
        """
        baseline_times, baseline_coverage = self.extract_time_series(self.baseline_data, 'coverage')
        ppo_times, ppo_coverage = self.extract_time_series(self.ppo_data, 'coverage')
        
        analysis = {}
        
        if len(baseline_coverage) > 1:
            # Coverage growth rate
            baseline_growth = np.diff(baseline_coverage) / np.diff(baseline_times)
            analysis['baseline_avg_growth_rate'] = float(np.mean(baseline_growth[baseline_growth > 0]))
        
        if len(ppo_coverage) > 1:
            ppo_growth = np.diff(ppo_coverage) / np.diff(ppo_times)
            analysis['ppo_avg_growth_rate'] = float(np.mean(ppo_growth[ppo_growth > 0]))
        
        # Time to reach milestones
        milestones = [10, 20, 30, 40, 50, 60, 70, 80]
        analysis['milestones'] = {}
        
        for milestone in milestones:
            baseline_time = self._time_to_milestone(baseline_times, baseline_coverage, milestone)
            ppo_time = self._time_to_milestone(ppo_times, ppo_coverage, milestone)
            
            if baseline_time is not None or ppo_time is not None:
                analysis['milestones'][f'{milestone}%'] = {
                    'baseline': baseline_time,
                    'ppo': ppo_time
                }
        
        return analysis
    
    def _time_to_milestone(self, times: np.ndarray, values: np.ndarray, milestone: float) -> Optional[float]:
        """Find time when metric first reaches milestone."""
        indices = np.where(values >= milestone)[0]
        if len(indices) > 0:
            return float(times[indices[0]])
        return None
    
    def generate_crash_analysis(self) -> Dict:
        """
        Analyze crash discovery patterns.
        
        Returns:
            Dictionary with crash analysis
        """
        baseline_times, baseline_crashes = self.extract_time_series(self.baseline_data, 'unique_crashes')
        ppo_times, ppo_crashes = self.extract_time_series(self.ppo_data, 'unique_crashes')
        
        analysis = {}
        
        if len(baseline_crashes) > 0:
            analysis['baseline'] = {
                'total_crashes': int(baseline_crashes[-1]) if len(baseline_crashes) > 0 else 0,
                'time_to_first': float(baseline_times[np.where(baseline_crashes > 0)[0][0]]) if np.any(baseline_crashes > 0) else None
            }
        
        if len(ppo_crashes) > 0:
            analysis['ppo'] = {
                'total_crashes': int(ppo_crashes[-1]) if len(ppo_crashes) > 0 else 0,
                'time_to_first': float(ppo_times[np.where(ppo_crashes > 0)[0][0]]) if np.any(ppo_crashes > 0) else None
            }
        
        return analysis
    
    def save_analysis(self, output_file: str):
        """
        Save complete analysis to JSON file.
        
        Args:
            output_file: Path to output file
        """
        analysis = {
            'statistics': self.compute_statistics(),
            'coverage_analysis': self.generate_coverage_analysis(),
            'crash_analysis': self.generate_crash_analysis(),
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"Analysis saved to {output_path}")
        
        return analysis
    
    def print_summary(self):
        """Print summary of analysis to console."""
        logger.info("\n" + "="*60)
        logger.info("EXPERIMENTAL RESULTS SUMMARY")
        logger.info("="*60 + "\n")
        
        stats = self.compute_statistics()
        
        for metric, data in stats.items():
            logger.info(f"{metric.upper()}")
            logger.info("-" * 40)
            logger.info(f"  Baseline Final: {data['baseline']['final']:.2f}")
            logger.info(f"  PPO Final: {data['ppo']['final']:.2f}")
            
            if 'improvement' in data:
                imp = data['improvement']['percentage']
                logger.info(f"  Improvement: {imp:+.2f}%")
            
            if 'statistical_test' in data:
                test = data['statistical_test']
                sig = "YES" if test['significant'] else "NO"
                logger.info(f"  Statistically Significant: {sig} (p={test['p_value']:.4f})")
            
            logger.info("")
        
        logger.info("="*60 + "\n")


def main():
    """Main entry point for data analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze AFL++ Experiment Results')
    parser.add_argument('results_dir', help='Directory containing experimental results')
    parser.add_argument('--output', '-o', help='Output file for analysis (JSON)')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = ExperimentAnalyzer(args.results_dir)
    
    # Print summary
    analyzer.print_summary()
    
    # Generate comparison table
    table = analyzer.generate_comparison_table()
    print("\nComparison Table:")
    print(table.to_string(index=False))
    
    # Save analysis
    if args.output:
        analyzer.save_analysis(args.output)
    else:
        # Default output location
        output_file = Path(args.results_dir) / "data" / "analysis_results.json"
        analyzer.save_analysis(str(output_file))


if __name__ == "__main__":
    main()
