"""
Mutation Strategy Selector
This module maps PPO agent actions to AFL++ mutation strategies
and manages the dynamic selection of mutation techniques.
"""

import numpy as np
from enum import IntEnum
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MutationStrategy(IntEnum):
    """
    AFL++ mutation strategies.
    These correspond to different mutation operations available in AFL++.
    """
    # Deterministic strategies
    BITFLIP = 0          # Bit flipping (deterministic)
    BYTEFLIP = 1         # Byte flipping
    ARITHMETIC = 2       # Arithmetic operations (+/- small values)
    INTERESTING = 3      # Interesting values (boundaries, special values)
    
    # Havoc strategies (stacked random mutations)
    HAVOC_LIGHT = 4      # Light havoc (few mutations)
    HAVOC_MEDIUM = 5     # Medium havoc (moderate mutations)
    HAVOC_HEAVY = 6      # Heavy havoc (many mutations)
    
    # Splicing
    SPLICE = 7           # Splice two test cases


class MutationStrategySelector:
    """
    Selects and applies mutation strategies based on PPO agent decisions.
    """
    
    def __init__(self):
        """Initialize the mutation strategy selector."""
        self.num_strategies = len(MutationStrategy)
        self.strategy_stats = {
            strategy: {
                'times_selected': 0,
                'coverage_gains': 0.0,
                'crashes_found': 0,
                'paths_found': 0
            }
            for strategy in MutationStrategy
        }
        
        self.current_strategy = None
        self.strategy_history = []
        
        logger.info(f"Mutation Strategy Selector initialized with {self.num_strategies} strategies")
    
    def get_num_actions(self) -> int:
        """Get number of available actions (mutation strategies)."""
        return self.num_strategies
    
    def select_strategy(self, action: int) -> MutationStrategy:
        """
        Select a mutation strategy based on agent action.
        
        Args:
            action: Action index from PPO agent
            
        Returns:
            Selected MutationStrategy
        """
        if action < 0 or action >= self.num_strategies:
            logger.warning(f"Invalid action {action}, using HAVOC_MEDIUM")
            action = MutationStrategy.HAVOC_MEDIUM
        
        strategy = MutationStrategy(action)
        self.current_strategy = strategy
        self.strategy_history.append(strategy)
        
        # Update stats
        self.strategy_stats[strategy]['times_selected'] += 1
        
        logger.debug(f"Selected strategy: {strategy.name}")
        
        return strategy
    
    def get_afl_mutation_config(self, strategy: MutationStrategy) -> Dict:
        """
        Generate AFL++ mutation configuration for the selected strategy.
        
        Args:
            strategy: MutationStrategy to configure
            
        Returns:
            Dictionary of AFL++ mutation parameters
        """
        configs = {
            MutationStrategy.BITFLIP: {
                'deterministic_mode': True,
                'skip_deterministic': False,
                'havoc_cycles': 0,
                'splice_cycles': 0,
                'focus_on': 'bitflip'
            },
            MutationStrategy.BYTEFLIP: {
                'deterministic_mode': True,
                'skip_deterministic': False,
                'havoc_cycles': 0,
                'splice_cycles': 0,
                'focus_on': 'byteflip'
            },
            MutationStrategy.ARITHMETIC: {
                'deterministic_mode': True,
                'skip_deterministic': False,
                'havoc_cycles': 0,
                'splice_cycles': 0,
                'focus_on': 'arithmetic'
            },
            MutationStrategy.INTERESTING: {
                'deterministic_mode': True,
                'skip_deterministic': False,
                'havoc_cycles': 0,
                'splice_cycles': 0,
                'focus_on': 'interesting'
            },
            MutationStrategy.HAVOC_LIGHT: {
                'deterministic_mode': False,
                'skip_deterministic': True,
                'havoc_cycles': 64,
                'splice_cycles': 0,
                'havoc_stack_pow': 2
            },
            MutationStrategy.HAVOC_MEDIUM: {
                'deterministic_mode': False,
                'skip_deterministic': True,
                'havoc_cycles': 256,
                'splice_cycles': 32,
                'havoc_stack_pow': 4
            },
            MutationStrategy.HAVOC_HEAVY: {
                'deterministic_mode': False,
                'skip_deterministic': True,
                'havoc_cycles': 1024,
                'splice_cycles': 128,
                'havoc_stack_pow': 7
            },
            MutationStrategy.SPLICE: {
                'deterministic_mode': False,
                'skip_deterministic': True,
                'havoc_cycles': 64,
                'splice_cycles': 512,
                'splice_probability': 0.8
            }
        }
        
        return configs.get(strategy, configs[MutationStrategy.HAVOC_MEDIUM])
    
    def get_strategy_description(self, strategy: MutationStrategy) -> str:
        """
        Get human-readable description of a mutation strategy.
        
        Args:
            strategy: MutationStrategy to describe
            
        Returns:
            Description string
        """
        descriptions = {
            MutationStrategy.BITFLIP: "Flip individual bits in the input (deterministic exploration)",
            MutationStrategy.BYTEFLIP: "Flip entire bytes in the input (faster than bitflip)",
            MutationStrategy.ARITHMETIC: "Add or subtract small values to bytes/words",
            MutationStrategy.INTERESTING: "Replace with known interesting values (0, -1, MAX_INT, etc.)",
            MutationStrategy.HAVOC_LIGHT: "Apply few random mutations (fast, less thorough)",
            MutationStrategy.HAVOC_MEDIUM: "Apply moderate random mutations (balanced)",
            MutationStrategy.HAVOC_HEAVY: "Apply many random mutations (slow, very thorough)",
            MutationStrategy.SPLICE: "Combine parts of different test cases"
        }
        
        return descriptions.get(strategy, "Unknown strategy")
    
    def update_strategy_stats(self, coverage_gain: float, crashes: int, paths: int):
        """
        Update statistics for the current strategy.
        
        Args:
            coverage_gain: Coverage improvement achieved
            crashes: Number of new crashes found
            paths: Number of new paths found
        """
        if self.current_strategy is None:
            return
        
        stats = self.strategy_stats[self.current_strategy]
        stats['coverage_gains'] += coverage_gain
        stats['crashes_found'] += crashes
        stats['paths_found'] += paths
    
    def get_strategy_performance(self) -> Dict:
        """
        Get performance statistics for all strategies.
        
        Returns:
            Dictionary of strategy performance metrics
        """
        performance = {}
        
        for strategy in MutationStrategy:
            stats = self.strategy_stats[strategy]
            times_selected = stats['times_selected']
            
            if times_selected > 0:
                performance[strategy.name] = {
                    'times_selected': times_selected,
                    'avg_coverage_gain': stats['coverage_gains'] / times_selected,
                    'avg_crashes': stats['crashes_found'] / times_selected,
                    'avg_paths': stats['paths_found'] / times_selected,
                }
            else:
                performance[strategy.name] = {
                    'times_selected': 0,
                    'avg_coverage_gain': 0.0,
                    'avg_crashes': 0.0,
                    'avg_paths': 0.0,
                }
        
        return performance
    
    def get_strategy_distribution(self) -> Dict[str, float]:
        """
        Get distribution of strategy selection.
        
        Returns:
            Dictionary mapping strategy names to selection probabilities
        """
        total_selections = sum(
            stats['times_selected'] 
            for stats in self.strategy_stats.values()
        )
        
        if total_selections == 0:
            return {strategy.name: 0.0 for strategy in MutationStrategy}
        
        distribution = {
            strategy.name: stats['times_selected'] / total_selections
            for strategy, stats in self.strategy_stats.items()
        }
        
        return distribution
    
    def get_best_strategy(self) -> MutationStrategy:
        """
        Get the best performing strategy based on historical performance.
        
        Returns:
            Best performing MutationStrategy
        """
        best_strategy = MutationStrategy.HAVOC_MEDIUM  # Default
        best_score = -float('inf')
        
        for strategy in MutationStrategy:
            stats = self.strategy_stats[strategy]
            if stats['times_selected'] == 0:
                continue
            
            # Compute weighted score
            score = (
                stats['coverage_gains'] * 1.0 +
                stats['crashes_found'] * 50.0 +
                stats['paths_found'] * 1.0
            ) / stats['times_selected']
            
            if score > best_score:
                best_score = score
                best_strategy = strategy
        
        return best_strategy
    
    def reset_stats(self):
        """Reset all strategy statistics."""
        for strategy in MutationStrategy:
            self.strategy_stats[strategy] = {
                'times_selected': 0,
                'coverage_gains': 0.0,
                'crashes_found': 0,
                'paths_found': 0
            }
        self.strategy_history.clear()
        logger.info("Strategy statistics reset")
    
    def get_summary(self) -> str:
        """
        Get a summary of strategy selection and performance.
        
        Returns:
            Summary string
        """
        lines = ["Mutation Strategy Performance Summary", "=" * 60]
        
        performance = self.get_strategy_performance()
        distribution = self.get_strategy_distribution()
        
        for strategy in MutationStrategy:
            name = strategy.name
            perf = performance[name]
            dist = distribution[name]
            
            lines.append(f"\n{name}:")
            lines.append(f"  Selected: {perf['times_selected']} times ({dist*100:.1f}%)")
            lines.append(f"  Avg Coverage Gain: {perf['avg_coverage_gain']:.4f}")
            lines.append(f"  Avg Crashes: {perf['avg_crashes']:.2f}")
            lines.append(f"  Avg Paths: {perf['avg_paths']:.2f}")
        
        best = self.get_best_strategy()
        lines.append(f"\nBest Performing Strategy: {best.name}")
        
        return "\n".join(lines)


# AFL++ Custom Mutator Interface (for integration)
class AFLCustomMutator:
    """
    Custom mutator interface for AFL++.
    This would be loaded as a shared library by AFL++.
    """
    
    def __init__(self):
        """Initialize the custom mutator."""
        self.selector = MutationStrategySelector()
        self.current_config = None
        logger.info("AFL++ Custom Mutator initialized")
    
    def set_strategy(self, action: int):
        """
        Set mutation strategy based on RL agent action.
        
        Args:
            action: Action from PPO agent
        """
        strategy = self.selector.select_strategy(action)
        self.current_config = self.selector.get_afl_mutation_config(strategy)
        logger.info(f"Mutation strategy set to: {strategy.name}")
    
    def mutate(self, data: bytes, max_size: int) -> bytes:
        """
        Mutate input data according to current strategy.
        
        Args:
            data: Input data to mutate
            max_size: Maximum size of mutated data
            
        Returns:
            Mutated data
        """
        # This is a simplified example - actual implementation would
        # interface with AFL++'s mutation functions
        
        if self.current_config is None:
            return data
        
        mutated = bytearray(data)
        
        # Apply mutations based on strategy
        # (This is placeholder logic - actual mutations would use AFL++ internals)
        if self.current_config.get('deterministic_mode'):
            # Deterministic mutations
            for i in range(min(len(mutated), max_size)):
                if np.random.random() < 0.1:
                    mutated[i] ^= (1 << np.random.randint(0, 8))
        else:
            # Havoc mutations
            num_mutations = self.current_config.get('havoc_cycles', 256)
            for _ in range(num_mutations):
                if len(mutated) == 0:
                    break
                idx = np.random.randint(0, len(mutated))
                mutated[idx] = np.random.randint(0, 256)
        
        return bytes(mutated[:max_size])


if __name__ == "__main__":
    # Test the mutation strategy selector
    print("Testing Mutation Strategy Selector...")
    
    selector = MutationStrategySelector()
    
    # Test strategy selection
    for action in range(selector.get_num_actions()):
        strategy = selector.select_strategy(action)
        config = selector.get_afl_mutation_config(strategy)
        description = selector.get_strategy_description(strategy)
        
        print(f"\nAction {action}: {strategy.name}")
        print(f"Description: {description}")
        print(f"Config: {config}")
        
        # Simulate some results
        selector.update_strategy_stats(
            coverage_gain=np.random.random(),
            crashes=np.random.randint(0, 3),
            paths=np.random.randint(1, 10)
        )
    
    # Print summary
    print("\n" + selector.get_summary())
    
    # Test distribution
    print("\nStrategy Distribution:")
    distribution = selector.get_strategy_distribution()
    for name, prob in distribution.items():
        print(f"  {name}: {prob*100:.1f}%")
    
    print("\nMutation Strategy Selector test completed!")
