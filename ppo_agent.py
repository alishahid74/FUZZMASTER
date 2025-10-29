"""
PPO Agent for AFL++ Fuzzing Optimization
This module implements the Proximal Policy Optimization agent that learns
to optimize mutation strategies for fuzzing.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.distributions import Categorical
import numpy as np
from typing import List, Tuple, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PPONetwork(nn.Module):
    """
    Neural network for PPO agent with separate actor and critic heads.
    
    Architecture:
    - Input: State representation (coverage, crashes, execution speed, etc.)
    - Hidden: Two fully connected layers with ReLU activation
    - Output: Policy (actor) and value function (critic)
    """
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
        """
        Initialize the PPO network.
        
        Args:
            state_dim: Dimension of the state space
            action_dim: Number of possible mutation strategies
            hidden_dim: Size of hidden layers
        """
        super(PPONetwork, self).__init__()
        
        # Shared feature extraction layers
        self.shared_fc1 = nn.Linear(state_dim, hidden_dim)
        self.shared_fc2 = nn.Linear(hidden_dim, hidden_dim)
        
        # Actor head (policy network)
        self.actor_fc = nn.Linear(hidden_dim, hidden_dim // 2)
        self.actor_out = nn.Linear(hidden_dim // 2, action_dim)
        
        # Critic head (value network)
        self.critic_fc = nn.Linear(hidden_dim, hidden_dim // 2)
        self.critic_out = nn.Linear(hidden_dim // 2, 1)
        
        # Initialize weights
        self._initialize_weights()
        
        logger.info(f"PPO Network initialized: state_dim={state_dim}, "
                   f"action_dim={action_dim}, hidden_dim={hidden_dim}")
    
    def _initialize_weights(self):
        """Initialize network weights using orthogonal initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
                nn.init.constant_(module.bias, 0.0)
    
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the network.
        
        Args:
            state: Input state tensor
            
        Returns:
            Tuple of (action_logits, state_value)
        """
        # Shared feature extraction
        x = F.relu(self.shared_fc1(state))
        x = F.relu(self.shared_fc2(x))
        
        # Actor head - policy distribution
        actor = F.relu(self.actor_fc(x))
        action_logits = self.actor_out(actor)
        
        # Critic head - state value
        critic = F.relu(self.critic_fc(x))
        state_value = self.critic_out(critic)
        
        return action_logits, state_value
    
    def get_action(self, state: torch.Tensor, deterministic: bool = False) -> Tuple[int, torch.Tensor, torch.Tensor]:
        """
        Sample an action from the policy.
        
        Args:
            state: Current state
            deterministic: If True, select the most probable action
            
        Returns:
            Tuple of (action, log_prob, value)
        """
        action_logits, value = self.forward(state)
        action_probs = F.softmax(action_logits, dim=-1)
        
        if deterministic:
            action = torch.argmax(action_probs, dim=-1)
            dist = Categorical(action_probs)
            log_prob = dist.log_prob(action)
        else:
            dist = Categorical(action_probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
        
        return action.item(), log_prob, value
    
    def evaluate_actions(self, states: torch.Tensor, actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Evaluate actions for training.
        
        Args:
            states: Batch of states
            actions: Batch of actions taken
            
        Returns:
            Tuple of (log_probs, state_values, entropy)
        """
        action_logits, state_values = self.forward(states)
        action_probs = F.softmax(action_logits, dim=-1)
        dist = Categorical(action_probs)
        
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()
        
        return log_probs, state_values.squeeze(-1), entropy


class PPOAgent:
    """
    PPO Agent for fuzzing optimization.
    Implements the PPO algorithm with clipped objective.
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dim: int = 128,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        device: str = None
    ):
        """
        Initialize PPO agent.
        
        Args:
            state_dim: Dimension of state space
            action_dim: Number of actions (mutation strategies)
            hidden_dim: Hidden layer size
            learning_rate: Learning rate for optimizer
            gamma: Discount factor
            gae_lambda: GAE lambda parameter
            clip_epsilon: PPO clipping parameter
            value_coef: Value loss coefficient
            entropy_coef: Entropy bonus coefficient
            max_grad_norm: Maximum gradient norm for clipping
            device: Device to run on ('cpu' or 'cuda')
        """
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Hyperparameters
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        
        # Initialize network
        self.network = PPONetwork(state_dim, action_dim, hidden_dim).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate)
        
        # Storage for experience
        self.states = []
        self.actions = []
        self.log_probs = []
        self.rewards = []
        self.values = []
        self.dones = []
        
        # Statistics
        self.episode_rewards = []
        self.episode_lengths = []
        
        logger.info(f"PPO Agent initialized on device: {self.device}")
        logger.info(f"Hyperparameters: γ={gamma}, λ={gae_lambda}, ε={clip_epsilon}")
    
    def select_action(self, state: np.ndarray, deterministic: bool = False) -> int:
        """
        Select an action based on the current state.
        
        Args:
            state: Current state observation
            deterministic: Whether to act deterministically
            
        Returns:
            Selected action index
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action, log_prob, value = self.network.get_action(state_tensor, deterministic)
        
        # Store experience
        self.states.append(state)
        self.actions.append(action)
        self.log_probs.append(log_prob.item())
        self.values.append(value.item())
        
        return action
    
    def store_transition(self, reward: float, done: bool):
        """
        Store the reward and done flag for the last action.
        
        Args:
            reward: Reward received
            done: Whether episode is done
        """
        self.rewards.append(reward)
        self.dones.append(done)
    
    def compute_gae(self, next_value: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Generalized Advantage Estimation.
        
        Args:
            next_value: Value of the next state
            
        Returns:
            Tuple of (advantages, returns)
        """
        values = np.array(self.values + [next_value])
        rewards = np.array(self.rewards)
        dones = np.array(self.dones)
        
        advantages = np.zeros_like(rewards)
        last_gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_non_terminal = 1.0 - dones[t]
                next_value_t = next_value
            else:
                next_non_terminal = 1.0 - dones[t]
                next_value_t = values[t + 1]
            
            delta = rewards[t] + self.gamma * next_value_t * next_non_terminal - values[t]
            advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * next_non_terminal * last_gae
        
        returns = advantages + values[:-1]
        
        return advantages, returns
    
    def update(self, n_epochs: int = 10, batch_size: int = 64) -> Dict[str, float]:
        """
        Update the policy using PPO algorithm.
        
        Args:
            n_epochs: Number of optimization epochs
            batch_size: Mini-batch size
            
        Returns:
            Dictionary of training statistics
        """
        if len(self.states) == 0:
            return {}
        
        # Compute advantages and returns
        with torch.no_grad():
            last_state = torch.FloatTensor(self.states[-1]).unsqueeze(0).to(self.device)
            _, last_value = self.network.forward(last_state)
            last_value = last_value.item()
        
        advantages, returns = self.compute_gae(last_value)
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Convert to tensors
        states = torch.FloatTensor(np.array(self.states)).to(self.device)
        actions = torch.LongTensor(self.actions).to(self.device)
        old_log_probs = torch.FloatTensor(self.log_probs).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)
        
        # Training metrics
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        n_updates = 0
        
        # Multiple epochs of optimization
        for epoch in range(n_epochs):
            # Generate random mini-batches
            indices = np.random.permutation(len(states))
            
            for start_idx in range(0, len(states), batch_size):
                end_idx = min(start_idx + batch_size, len(states))
                batch_indices = indices[start_idx:end_idx]
                
                # Get batch data
                batch_states = states[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_advantages = advantages_t[batch_indices]
                batch_returns = returns_t[batch_indices]
                
                # Evaluate current policy
                log_probs, values, entropy = self.network.evaluate_actions(batch_states, batch_actions)
                
                # Compute ratio and clipped objective
                ratio = torch.exp(log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(ratio, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon) * batch_advantages
                
                # Policy loss (negative because we want to maximize)
                policy_loss = -torch.min(surr1, surr2).mean()
                
                # Value loss
                value_loss = F.mse_loss(values, batch_returns)
                
                # Entropy bonus (for exploration)
                entropy_loss = -entropy.mean()
                
                # Total loss
                loss = policy_loss + self.value_coef * value_loss + self.entropy_coef * entropy_loss
                
                # Optimization step
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self.optimizer.step()
                
                # Track metrics
                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.mean().item()
                n_updates += 1
        
        # Clear experience buffer
        self.clear_buffer()
        
        # Return training statistics
        stats = {
            'policy_loss': total_policy_loss / n_updates,
            'value_loss': total_value_loss / n_updates,
            'entropy': total_entropy / n_updates,
            'mean_return': returns.mean(),
            'mean_advantage': advantages.mean()
        }
        
        return stats
    
    def clear_buffer(self):
        """Clear the experience buffer."""
        self.states.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()
    
    def save(self, filepath: str):
        """Save the agent's network."""
        torch.save({
            'network_state_dict': self.network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load the agent's network."""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.network.load_state_dict(checkpoint['network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        logger.info(f"Model loaded from {filepath}")


if __name__ == "__main__":
    # Test the PPO agent
    print("Testing PPO Agent...")
    
    state_dim = 10  # Example: coverage, crashes, speed, etc.
    action_dim = 8  # Example: 8 different mutation strategies
    
    agent = PPOAgent(state_dim=state_dim, action_dim=action_dim)
    
    # Test action selection
    test_state = np.random.randn(state_dim)
    action = agent.select_action(test_state)
    print(f"Selected action: {action}")
    
    # Test storing transitions
    agent.store_transition(reward=1.0, done=False)
    
    # Test update (with minimal data)
    for _ in range(10):
        state = np.random.randn(state_dim)
        action = agent.select_action(state)
        agent.store_transition(reward=np.random.randn(), done=False)
    
    stats = agent.update(n_epochs=2, batch_size=5)
    print(f"Training stats: {stats}")
    
    print("PPO Agent test completed!")
