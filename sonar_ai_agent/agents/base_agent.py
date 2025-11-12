"""
Base agent class with common functionality for both Bug Hunter and Code Healer agents.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import ollama
import json
from datetime import datetime

from ..config import Config
from ..models import AgentMetrics
from ..utils.logger import get_logger


class BaseAgent(ABC):
    """Base class for all AI agents in the system."""
    
    def __init__(self, config: Config, agent_name: str):
        """Initialize base agent with configuration."""
        self.config = config
        self.agent_name = agent_name
        
        # Initialize file-based logger
        self.logger = get_logger(config, f"sonar_ai_agent.{agent_name}")
        
        # Initialize Ollama client
        self.ollama_client = self._setup_ollama()
        
        # Metrics tracking
        self.metrics: Optional[AgentMetrics] = None
        
        # Session tracking
        self.session_id = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.log_session_start(self.session_id, agent_name=agent_name)
    

    
    def _setup_ollama(self) -> ollama.Client:
        """Initialize Ollama client connection."""
        try:
            client = ollama.Client(host=self.config.ollama_url)
            # Test connection by listing models
            models = client.list()
            available_models = [model.model for model in models.models]
            
            if self.config.ollama_model not in available_models:
                self.logger.warning(f"Model {self.config.ollama_model} not found. Available: {available_models}")
            
            self.logger.info(f"Connected to Ollama", 
                           ollama_url=self.config.ollama_url, 
                           model=self.config.ollama_model,
                           available_models=available_models)
            return client
        except Exception as e:
            self.logger.log_error_with_context(e, "Ollama connection setup")
            raise
    

    
    def health_check(self) -> bool:
        """Check if all agent dependencies are healthy."""
        try:
            # Test Ollama connection
            response = self.ollama_client.generate(
                model=self.config.ollama_model,
                prompt="Hello",
                options={"num_predict": 10}
            )
            if not response or not response.get('response'):
                self.logger.error("Ollama health check failed")
                return False
            
            self.logger.info(f"{self.agent_name} health check passed", 
                           agent_name=self.agent_name,
                           ollama_response_length=len(response.get('response', '')))
            return True
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"{self.agent_name} health check")
            return False
    
    def start_metrics_tracking(self) -> None:
        """Start tracking metrics for this agent run."""
        self.metrics = AgentMetrics(
            agent_name=self.agent_name,
            start_time=datetime.now()
        )
        self.logger.log_workflow_step("metrics_tracking_started", "success", 
                                    agent_name=self.agent_name)
    
    def stop_metrics_tracking(self) -> Optional[AgentMetrics]:
        """Stop tracking metrics and return the results."""
        if self.metrics:
            self.metrics.end_time = datetime.now()
            
            # Log metrics
            metrics_data = {
                "processing_time_seconds": self.metrics.processing_time_seconds,
                "issues_processed": self.metrics.issues_processed,
                "fixes_generated": self.metrics.fixes_generated,
                "fixes_validated": self.metrics.fixes_validated,
                "errors_encountered": self.metrics.errors_encountered,
                "success_rate": self.metrics.success_rate
            }
            
            self.logger.log_metrics(f"{self.agent_name}_session_metrics", metrics_data)
            self.logger.log_session_end(self.session_id, **metrics_data)
            
            return self.metrics
        return None
    
    @abstractmethod
    def process(self, *args, **kwargs):
        """Abstract method that each agent must implement."""
        pass
    
    def log_error(self, error: Exception, context: str = "", **metadata) -> str:
        """Log an error with enhanced context and update metrics."""
        # Add agent-specific metadata
        agent_metadata = {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            **metadata
        }
        
        error_id = self.logger.log_error_with_context(error, context or "general_error", **agent_metadata)
        
        if self.metrics:
            self.metrics.errors_encountered += 1
        
        return error_id
    
    def generate_response(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Generate response using Ollama with enhanced performance tracking."""
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        # Use performance context manager for automatic timing
        with self.logger.performance_context("ollama_generation",
                                           model=self.config.ollama_model,
                                           prompt_length=len(full_prompt),
                                           system_prompt_length=len(system_prompt) if system_prompt else 0,
                                           temperature=temperature,
                                           max_tokens=max_tokens) as ctx:
            
            # Log the request details
            self.logger.debug("Ollama LLM Request initiated",
                            prompt_preview=full_prompt[:200] + "..." if len(full_prompt) > 200 else full_prompt)
            
            response = self.ollama_client.generate(
                model=self.config.ollama_model,
                prompt=full_prompt,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "top_k": 40
                }
            )
            
            if not response or not response.get('response'):
                ctx['errors_encountered'] += 1
                raise ValueError("Empty response from Ollama")
            
            response_text = response['response'].strip()
            
            # Update context with response metrics
            ctx['tokens_generated'] = len(response_text.split())
            ctx['response_length'] = len(response_text)
            ctx['items_processed'] = 1  # One successful generation
            
            # Log response summary
            self.logger.debug("Ollama LLM Response generated",
                            response_length=len(response_text),
                            tokens_generated=ctx['tokens_generated'],
                            response_preview=response_text[:300] + "..." if len(response_text) > 300 else response_text)
            
            return response_text
    
    def chat_completion(self, messages: list, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Chat completion using Ollama with enhanced performance tracking."""
        with self.logger.performance_context("ollama_chat_completion",
                                           model=self.config.ollama_model,
                                           message_count=len(messages),
                                           temperature=temperature,
                                           max_tokens=max_tokens) as ctx:
            
            response = self.ollama_client.chat(
                model=self.config.ollama_model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "top_k": 40
                }
            )
            
            if not response or not response.get('message', {}).get('content'):
                ctx['errors_encountered'] += 1
                raise ValueError("Empty response from Ollama chat")
            
            response_text = response['message']['content'].strip()
            
            # Update context with metrics
            ctx['tokens_generated'] = len(response_text.split())
            ctx['response_length'] = len(response_text)
            ctx['items_processed'] = 1
            
            self.logger.debug("Ollama chat completion generated", 
                            response_length=len(response_text),
                            tokens_generated=ctx['tokens_generated'])
            
            return response_text
    
    def log_quality_score(self, name: str, value: float, comment: str = "") -> None:
        """Log quality metrics to file."""
        self.logger.log_metrics(f"quality_score_{name}", {
            "score_name": name,
            "score_value": value,
            "comment": comment,
            "agent_name": self.agent_name,
            "session_id": self.session_id
        })
    
    def log_operation_start(self, operation: str, **metadata) -> str:
        """Start logging an operation with agent context."""
        agent_metadata = {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            **metadata
        }
        return self.logger.log_operation_start(operation, **agent_metadata)
    
    def log_operation_end(self, correlation_id: str, **metadata) -> None:
        """End logging an operation."""
        self.logger.log_operation_end(correlation_id, **metadata)
    
    def performance_context(self, operation: str, **metadata):
        """Create a performance context manager with agent metadata."""
        agent_metadata = {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            **metadata
        }
        return self.logger.performance_context(operation, **agent_metadata)
    
    def log_agent_step(self, step_name: str, status: str, **metadata) -> None:
        """Log an agent processing step."""
        self.logger.log_workflow_step(f"{self.agent_name}_{step_name}", status,
                                    agent_name=self.agent_name,
                                    session_id=self.session_id,
                                    **metadata)
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.agent_name}', model='{self.config.ollama_model}')"