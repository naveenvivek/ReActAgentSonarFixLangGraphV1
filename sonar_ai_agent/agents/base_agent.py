"""
Base agent class with common functionality for both Bug Hunter and Code Healer agents.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import ollama
from langfuse import Langfuse, observe
import logging
import json

from ..config import Config
from ..models import AgentMetrics


class BaseAgent(ABC):
    """Base class for all AI agents in the system."""
    
    def __init__(self, config: Config, agent_name: str):
        """Initialize base agent with configuration."""
        self.config = config
        self.agent_name = agent_name
        self.logger = self._setup_logging()
        
        # Initialize Ollama client
        self.ollama_client = self._setup_ollama()
        
        # Initialize Langfuse for observability
        self.langfuse = self._setup_langfuse()
        
        # Metrics tracking
        self.metrics: Optional[AgentMetrics] = None
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the agent."""
        logger = logging.getLogger(f"sonar_ai_agent.{self.agent_name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _setup_ollama(self) -> ollama.Client:
        """Initialize Ollama client connection."""
        try:
            client = ollama.Client(host=self.config.ollama_url)
            # Test connection by listing models
            models = client.list()
            available_models = [model.model for model in models.models]
            
            if self.config.ollama_model not in available_models:
                self.logger.warning(f"Model {self.config.ollama_model} not found. Available: {available_models}")
            
            self.logger.info(f"Connected to Ollama at {self.config.ollama_url} with model {self.config.ollama_model}")
            return client
        except Exception as e:
            self.logger.error(f"Failed to connect to Ollama: {e}")
            raise
    
    def _setup_langfuse(self) -> Langfuse:
        """Initialize Langfuse for observability."""
        try:
            langfuse = Langfuse(
                secret_key=self.config.langfuse_secret_key,
                public_key=self.config.langfuse_public_key,
                host=self.config.langfuse_url
            )
            self.logger.info(f"Connected to Langfuse at {self.config.langfuse_url}")
            return langfuse
        except Exception as e:
            self.logger.error(f"Failed to connect to Langfuse: {e}")
            raise
    
    @observe(name="agent_health_check")
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
            
            # Test Langfuse connection (basic check)
            if not self.langfuse:
                self.logger.error("Langfuse not initialized")
                return False
            

            
            self.logger.info(f"{self.agent_name} health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.agent_name} health check failed: {e}")
            return False
    
    def start_metrics_tracking(self) -> None:
        """Start tracking metrics for this agent run."""
        from datetime import datetime
        self.metrics = AgentMetrics(
            agent_name=self.agent_name,
            start_time=datetime.now()
        )
        self.logger.info(f"Started metrics tracking for {self.agent_name}")
    
    def stop_metrics_tracking(self) -> Optional[AgentMetrics]:
        """Stop tracking metrics and return the results."""
        if self.metrics:
            from datetime import datetime
            self.metrics.end_time = datetime.now()
            self.logger.info(
                f"Stopped metrics tracking for {self.agent_name}. "
                f"Processing time: {self.metrics.processing_time_seconds:.2f}s"
            )
            return self.metrics
        return None
    
    @abstractmethod
    def process(self, *args, **kwargs):
        """Abstract method that each agent must implement."""
        pass
    
    def log_error(self, error: Exception, context: str = "") -> None:
        """Log an error with context and update metrics."""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg)
        
        if self.metrics:
            self.metrics.errors_encountered += 1
    
    @observe(name="ollama_generate")
    def generate_response(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Generate response using Ollama with observability."""
        try:
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
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
                raise ValueError("Empty response from Ollama")
            
            return response['response'].strip()
            
        except Exception as e:
            self.log_error(e, f"Failed to generate response with model {self.config.ollama_model}")
            raise
    
    @observe(name="ollama_chat")
    def chat_completion(self, messages: list, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Chat completion using Ollama with message history."""
        try:
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
                raise ValueError("Empty response from Ollama chat")
            
            return response['message']['content'].strip()
            
        except Exception as e:
            self.log_error(e, f"Failed to complete chat with model {self.config.ollama_model}")
            raise
    
    def create_langfuse_score(self, name: str, value: float, comment: str = "") -> None:
        """Create a score in Langfuse for tracking quality metrics."""
        try:
            self.langfuse.create_score(
                name=name,
                value=value,
                data_type="NUMERIC",
                comment=comment
            )
        except Exception as e:
            self.logger.warning(f"Failed to create Langfuse score {name}: {e}")
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.agent_name}', model='{self.config.ollama_model}')"