#!/usr/bin/env python3
"""
Test script for the enhanced BaseAgent logging integration.
"""

import sys
import os
import time
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar_ai_agent.config import Config
from sonar_ai_agent.agents.base_agent import BaseAgent


class TestAgent(BaseAgent):
    """Test agent implementation for logging verification."""
    
    def process(self, data_items: list = None):
        """Test process method with enhanced logging."""
        if data_items is None:
            data_items = [f"item_{i}" for i in range(5)]
        
        self.log_agent_step("process_start", "success", 
                          items_count=len(data_items),
                          processing_mode="test")
        
        # Use performance context for the main processing
        with self.performance_context("data_processing",
                                    batch_size=len(data_items),
                                    processing_type="test_simulation") as ctx:
            
            processed_items = []
            
            for i, item in enumerate(data_items):
                try:
                    # Simulate processing work
                    time.sleep(0.01)
                    
                    # Simulate occasional errors
                    if i == 2:
                        raise ValueError(f"Simulated processing error for {item}")
                    
                    processed_items.append(f"processed_{item}")
                    ctx['items_processed'] += 1
                    
                    self.logger.debug(f"Processed item: {item}",
                                    item_index=i,
                                    item_name=item,
                                    processing_stage="individual_item")
                    
                except Exception as e:
                    ctx['errors_encountered'] += 1
                    error_id = self.log_error(e, "item_processing",
                                            item_index=i,
                                            item_name=item,
                                            retry_count=0)
                    
                    # Simulate error recovery
                    self.logger.log_error_recovery(error_id, "skip_and_continue", True,
                                                 recovery_strategy="graceful_skip")
            
            ctx['processed_items'] = len(processed_items)
            ctx['success_rate'] = len(processed_items) / len(data_items)
        
        self.log_agent_step("process_complete", "success",
                          items_processed=len(processed_items),
                          success_rate=len(processed_items) / len(data_items))
        
        return processed_items


def test_base_agent_logging():
    """Test the enhanced BaseAgent logging capabilities."""
    print("Testing Enhanced BaseAgent Logging Integration...")
    print("=" * 60)
    
    # Create test config
    config = Config()
    
    # Create test agent
    agent = TestAgent(config, "TestAgent")
    
    print("\n1. Testing agent initialization and health check:")
    health_status = agent.health_check()
    print(f"Health check result: {health_status}")
    
    print("\n2. Testing metrics tracking:")
    agent.start_metrics_tracking()
    
    print("\n3. Testing LLM operations with performance tracking:")
    try:
        # Test generate_response with performance tracking
        response = agent.generate_response(
            prompt="What is the capital of France?",
            system_prompt="You are a helpful assistant.",
            temperature=0.3,
            max_tokens=50
        )
        print(f"LLM Response: {response[:100]}...")
        
        # Test chat completion
        messages = [
            {"role": "user", "content": "Hello, how are you?"}
        ]
        chat_response = agent.chat_completion(messages, temperature=0.5)
        print(f"Chat Response: {chat_response[:100]}...")
        
    except Exception as e:
        print(f"LLM operations failed (expected if Ollama not running): {e}")
    
    print("\n4. Testing agent processing with performance context:")
    test_data = [f"data_item_{i}" for i in range(8)]
    processed_results = agent.process(test_data)
    print(f"Processed {len(processed_results)} items successfully")
    
    print("\n5. Testing quality score logging:")
    agent.log_quality_score("processing_accuracy", 0.875, "Good processing accuracy achieved")
    agent.log_quality_score("response_time", 0.92, "Response time within acceptable limits")
    
    print("\n6. Testing manual operation tracking:")
    correlation_id = agent.log_operation_start("manual_analysis",
                                             analysis_type="code_quality",
                                             target_files=["file1.java", "file2.java"])
    
    # Simulate some work
    time.sleep(0.05)
    
    agent.log_operation_end(correlation_id,
                          files_analyzed=2,
                          issues_found=3,
                          analysis_result="completed")
    
    print("\n7. Testing error scenarios:")
    try:
        # Test different error types
        raise ConnectionError("Simulated connection failure")
    except Exception as e:
        error_id = agent.log_error(e, "external_service_connection",
                                 service_name="test_service",
                                 retry_count=2,
                                 timeout_seconds=30)
        
        # Test error recovery
        agent.logger.log_error_recovery(error_id, "fallback_to_cache", True,
                                      fallback_method="local_cache")
    
    print("\n8. Testing metrics completion:")
    final_metrics = agent.stop_metrics_tracking()
    if final_metrics:
        print(f"Final metrics - Processing time: {final_metrics.processing_time_seconds:.2f}s")
        print(f"Errors encountered: {final_metrics.errors_encountered}")
        print(f"Success rate: {final_metrics.success_rate:.2%}")
    
    print("\nEnhanced BaseAgent logging test completed!")
    print("Check the log file for detailed structured output.")


if __name__ == "__main__":
    test_base_agent_logging()