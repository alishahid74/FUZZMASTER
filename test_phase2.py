#!/usr/bin/env python3
"""
Test script for Phase 2 implementation
Verifies that all components work correctly
"""

import sys
import numpy as np
from pathlib import Path

print("="*60)
print("Phase 2 Implementation Test Suite")
print("="*60)
print()

# Test 1: PPO Agent
print("[1/4] Testing PPO Agent...")
try:
    from ppo_agent import PPOAgent, PPONetwork
    
    # Create agent
    agent = PPOAgent(state_dim=10, action_dim=8, hidden_dim=64)
    print("  ✓ Agent created successfully")
    
    # Test action selection
    test_state = np.random.randn(10)
    action = agent.select_action(test_state)
    print(f"  ✓ Action selection works (action={action})")
    
    # Test transition storage
    agent.store_transition(reward=1.0, done=False)
    print("  ✓ Transition storage works")
    
    # Test update (with minimal data)
    for _ in range(35):
        state = np.random.randn(10)
        action = agent.select_action(state)
        agent.store_transition(reward=np.random.randn(), done=False)
    
    stats = agent.update(n_epochs=2, batch_size=16)
    print(f"  ✓ Policy update works")
    print(f"    - Policy loss: {stats.get('policy_loss', 0):.4f}")
    print(f"    - Value loss: {stats.get('value_loss', 0):.4f}")
    
    # Test save/load
    agent.save("/tmp/test_agent.pt")
    agent.load("/tmp/test_agent.pt")
    print("  ✓ Save/load works")
    
    print("✓ PPO Agent: PASS\n")
    
except Exception as e:
    print(f"✗ PPO Agent: FAIL - {e}\n")
    sys.exit(1)


# Test 2: Feedback Analyzer
print("[2/4] Testing Feedback Analyzer...")
try:
    from feedback_analyzer import FeedbackAnalyzer, FuzzingMetrics
    import tempfile
    import shutil
    
    # Create mock AFL++ output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()
        (output_dir / "default").mkdir()
        
        # Create mock fuzzer_stats
        stats_file = output_dir / "default" / "fuzzer_stats"
        stats_content = """
start_time        : 1234567890
last_update       : 1234567900
fuzzer_pid        : 12345
cycles_done       : 5
execs_done        : 100000
execs_per_sec     : 2500.50
paths_total       : 150
saved_crashes     : 3
saved_hangs       : 1
bitmap_cvg        : 45.67%
stability         : 98.50%
pending_favs      : 10
pending_total     : 25
"""
        with open(stats_file, 'w') as f:
            f.write(stats_content)
        
        # Test analyzer
        analyzer = FeedbackAnalyzer(str(output_dir))
        print("  ✓ Analyzer created")
        
        # Test parsing
        metrics = analyzer.get_current_metrics()
        assert metrics is not None
        assert metrics.coverage > 0
        print(f"  ✓ Metrics parsing works (coverage={metrics.coverage:.2f}%)")
        
        # Test state generation
        analyzer.update()
        state, reward = analyzer.get_state_and_reward()
        assert state.shape == (10,)
        print(f"  ✓ State generation works (shape={state.shape})")
        
        # Test summary
        summary = analyzer.get_summary()
        assert 'current_metrics' in summary
        print("  ✓ Summary generation works")
        
    print("✓ Feedback Analyzer: PASS\n")
    
except Exception as e:
    print(f"✗ Feedback Analyzer: FAIL - {e}\n")
    sys.exit(1)


# Test 3: Mutation Selector
print("[3/4] Testing Mutation Selector...")
try:
    from mutation_selector import MutationStrategySelector, MutationStrategy
    
    selector = MutationStrategySelector()
    print(f"  ✓ Selector created ({selector.get_num_actions()} strategies)")
    
    # Test strategy selection
    for action in range(selector.get_num_actions()):
        strategy = selector.select_strategy(action)
        config = selector.get_afl_mutation_config(strategy)
        description = selector.get_strategy_description(strategy)
        
        assert config is not None
        assert len(description) > 0
    
    print("  ✓ All strategies can be selected")
    
    # Test stats update
    selector.update_strategy_stats(
        coverage_gain=0.5,
        crashes=2,
        paths=10
    )
    print("  ✓ Stats update works")
    
    # Test performance tracking
    performance = selector.get_strategy_performance()
    assert len(performance) == selector.get_num_actions()
    print("  ✓ Performance tracking works")
    
    # Test distribution
    distribution = selector.get_strategy_distribution()
    assert abs(sum(distribution.values()) - 1.0) < 0.01
    print("  ✓ Distribution calculation works")
    
    print("✓ Mutation Selector: PASS\n")
    
except Exception as e:
    print(f"✗ Mutation Selector: FAIL - {e}\n")
    sys.exit(1)


# Test 4: Integration Test
print("[4/4] Testing Component Integration...")
try:
    from ppo_agent import PPOAgent
    from feedback_analyzer import FeedbackAnalyzer
    from mutation_selector import MutationStrategySelector
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()
        (output_dir / "default").mkdir()
        
        # Create mock stats
        stats_file = output_dir / "default" / "fuzzer_stats"
        with open(stats_file, 'w') as f:
            f.write("""
cycles_done       : 1
execs_done        : 10000
execs_per_sec     : 500.0
paths_total       : 50
saved_crashes     : 0
bitmap_cvg        : 20.0%
stability         : 95.0%
pending_favs      : 5
""")
        
        # Initialize components
        agent = PPOAgent(state_dim=10, action_dim=8)
        analyzer = FeedbackAnalyzer(str(output_dir))
        selector = MutationStrategySelector()
        
        print("  ✓ All components initialized")
        
        # Simulate training loop
        for step in range(5):
            # Get state
            analyzer.update()
            state, reward = analyzer.get_state_and_reward()
            
            # Select action
            action = agent.select_action(state)
            
            # Apply strategy
            strategy = selector.select_strategy(action)
            
            # Store transition
            agent.store_transition(reward, done=False)
            
            # Update metrics (with random improvements)
            with open(stats_file, 'a') as f:
                f.write(f"execs_done        : {10000 + step * 5000}\n")
                f.write(f"bitmap_cvg        : {20.0 + step * 2.0}%\n")
        
        print(f"  ✓ Training loop simulation completed ({step+1} steps)")
        
        # Perform update
        if len(agent.states) >= 4:
            stats = agent.update(n_epochs=1, batch_size=4)
            print("  ✓ Agent update completed")
        
    print("✓ Integration Test: PASS\n")
    
except Exception as e:
    print(f"✗ Integration Test: FAIL - {e}\n")
    sys.exit(1)


# Final summary
print("="*60)
print("All Tests Passed! ✓")
print("="*60)
print()
print("Phase 2 implementation is working correctly.")
print("You can now proceed to run experiments.")
print()
print("Next steps:")
print("  1. Configure config.yaml for your target")
print("  2. Run fuzzing_controller.py")
print("  3. Monitor progress and collect data")
print()
