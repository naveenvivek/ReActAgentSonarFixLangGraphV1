#!/usr/bin/env python3
"""
Test script for the new structured logging functionality.
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar_ai_agent.config import Config
from sonar_ai_agent.utils.logger import get_logger


def test_structured_logging():
    """Test the new structured logging features."""
    print("Testing Structured Logging Enhancement...")
    print("=" * 50)
    
    # Create a test config
    config = Config()
    
    # Get logger instance
    logger = get_logger(config, "test_structured_logging")
    
    print("\n1. Testing basic logging with metadata:")
    logger.info("Agent initialization started", 
                agent_name="TestAgent",
                session_id="test_20241112_153045",
                ollama_model="llama3.1:8b")
    
    print("\n2. Testing nested metadata:")
    logger.info("Processing configuration", 
                config_data={
                    "database": {
                        "host": "localhost",
                        "port": 5432,
                        "name": "sonar_db"
                    },
                    "features": ["bug_hunter", "code_healer"],
                    "enabled": True
                })
    
    print("\n3. Testing performance data:")
    logger.info("Operation completed successfully",
                operation="sonar_analysis",
                duration_ms=1234.5,
                items_processed=15,
                throughput_per_second=12.1,
                success_rate=0.87)
    
    print("\n4. Testing warning with context:")
    logger.warning("Low confidence fix detected",
                   issue_key="java:S2095",
                   confidence_score=0.65,
                   threshold=0.8,
                   file_path="src/main/java/UserController.java")
    
    print("\n5. Testing error logging:")
    try:
        # Simulate an error
        raise ValueError("Test error for logging demonstration")
    except Exception as e:
        logger.log_error_with_context(e, "test_operation",
                                    operation_id="test_123",
                                    retry_count=2,
                                    max_retries=3)
    
    print("\n6. Testing large metadata truncation:")
    large_data = "x" * 1500  # Exceeds default max_metadata_length
    logger.info("Processing large dataset",
                large_field=large_data,
                dataset_size=len(large_data),
                processing_mode="batch")
    
    print("\n7. Testing list formatting:")
    logger.info("Available models detected",
                models=["llama3.1:8b", "codellama:7b", "mistral:7b", "qwen:4b"],
                total_count=4,
                default_model="llama3.1:8b")
    
    print("\n8. Testing workflow step logging:")
    logger.log_workflow_step("fetch_sonar_issues", "success",
                           project_key="SpringBootAppSonarAI",
                           issues_fetched=19,
                           severities=["BLOCKER", "CRITICAL"],
                           processing_time_ms=456.7)
    
    print("\n9. Testing operation correlation:")
    correlation_id = logger.log_operation_start("data_processing",
                                              dataset="user_data",
                                              batch_size=100)
    
    # Simulate some work
    import time
    time.sleep(0.1)
    
    logger.log_operation_end(correlation_id,
                           records_processed=250,
                           success_rate=0.96)
    
    print("\n10. Testing performance context manager:")
    try:
        with logger.performance_context("llm_generation", 
                                      model="llama3.1:8b",
                                      prompt_length=1500) as ctx:
            # Simulate LLM processing
            time.sleep(0.05)
            ctx['tokens_generated'] = 342
            ctx['temperature'] = 0.7
    except Exception as e:
        print(f"Context manager error: {e}")
    
    print("\n11. Testing performance context with error:")
    try:
        with logger.performance_context("file_processing",
                                      file_path="test.java") as ctx:
            # Simulate an error during processing
            time.sleep(0.02)
            raise FileNotFoundError("Test file not found")
    except FileNotFoundError:
        print("Expected error caught and logged")
    
    print("\n12. Testing enhanced context logging:")
    logger.log_with_context(logging.INFO, "Enhanced logging with auto-context",
                          custom_field="test_value",
                          processing_stage="validation")
    
    print("\n13. Testing sensitive data masking:")
    logger.info("User authentication attempt",
                username="john_doe",
                password="secret123456",
                api_token="abc123def456ghi789",
                auth_key="super_secret_key_value",
                user_id=12345)
    
    print("\n14. Testing complex nested objects:")
    complex_data = {
        "user": {
            "profile": {
                "name": "John Doe",
                "email": "john@example.com",
                "settings": {
                    "theme": "dark",
                    "notifications": True,
                    "privacy": {
                        "show_email": False,
                        "api_keys": ["key1", "key2", "key3"]
                    }
                }
            }
        },
        "session": {
            "id": "sess_123456789",
            "created": "2024-11-12T15:30:00Z",
            "expires": "2024-11-12T16:30:00Z"
        }
    }
    
    logger.info("Complex user session data",
                session_data=complex_data,
                processing_depth=4,
                data_size=len(str(complex_data)))
    
    print("\n15. Testing large list handling:")
    large_list = [f"item_{i}" for i in range(20)]
    logger.info("Processing large dataset",
                items=large_list,
                total_count=len(large_list),
                batch_size=5)
    
    print("\n16. Testing object type detection:")
    class CustomObject:
        def __init__(self):
            self.name = "test_object"
            self.value = 42
            self.data = {"nested": "value"}
    
    custom_obj = CustomObject()
    logger.info("Custom object processing",
                custom_object=custom_obj,
                object_type=type(custom_obj).__name__)
    
    print("\n17. Testing circular reference detection:")
    circular_dict = {"name": "parent"}
    circular_dict["self_ref"] = circular_dict  # Create circular reference
    
    logger.info("Testing circular reference handling",
                circular_data=circular_dict,
                warning="This should handle circular references safely")
    
    print("\n18. Testing performance threshold monitoring:")
    # Test normal performance
    logger.log_performance("fast_operation", 0.1, items_processed=100)
    
    # Test slow operation (should trigger WARNING)
    logger.log_performance("slow_operation", 6.0, items_processed=50)
    
    # Test very slow operation (should trigger ERROR)
    logger.log_performance("very_slow_operation", 12.0, items_processed=10)
    
    # Test low throughput (should trigger WARNING)
    logger.log_performance("low_throughput_operation", 2.0, items_processed=1)
    
    # Test high error rate (should trigger ERROR)
    logger.log_performance("error_prone_operation", 1.0, 
                          items_processed=100, 
                          errors_encountered=15,
                          error_rate=0.15)
    
    print("\n19. Testing enhanced performance context:")
    with logger.performance_context("batch_processing", 
                                   batch_id="batch_001") as ctx:
        # Simulate processing multiple items
        for i in range(10):
            time.sleep(0.01)  # Simulate work
            ctx['items_processed'] += 1
            if i == 7:  # Simulate some errors
                ctx['errors_encountered'] += 1
        
        ctx['batch_status'] = 'completed'
        ctx['quality_score'] = 0.92
    
    print("\n20. Testing performance tracker:")
    tracker = logger.create_performance_tracker("data_analysis")
    
    # Simulate multiple operations
    for i in range(5):
        duration = 0.5 + (i * 0.2)  # Varying durations
        success = i != 2  # One failure
        items = 20 + (i * 5)  # Varying item counts
        errors = 0 if success else 2
        
        tracker.record_operation(duration * 1000, success, items, errors)
    
    # Log the summary
    tracker.log_summary()
    
    print("\n21. Testing enhanced error logging:")
    
    def problematic_function():
        def nested_function():
            raise ValueError("This is a test error with stack trace")
        nested_function()
    
    try:
        problematic_function()
    except Exception as e:
        error_id = logger.log_error_with_context(e, "test_error_handling",
                                                operation_id="op_123",
                                                retry_count=1,
                                                user_id="user_456")
        
        # Test error recovery logging
        logger.log_error_recovery(error_id, "retry_with_fallback", True,
                                recovery_method="fallback_strategy")
    
    print("\n22. Testing different error types and escalation:")
    
    # Test critical error
    try:
        raise MemoryError("Simulated memory error")
    except Exception as e:
        logger.log_error_with_context(e, "memory_management",
                                    system_memory_mb=8192,
                                    process_memory_mb=4096)
    
    # Test warning-level error with low retry count
    try:
        raise TypeError("Type mismatch in data processing")
    except Exception as e:
        logger.log_error_with_context(e, "data_validation",
                                    retry_count=1,
                                    data_type="user_input")
    
    # Test escalated error with high retry count
    try:
        raise ConnectionError("Database connection failed")
    except Exception as e:
        logger.log_error_with_context(e, "database_connection",
                                    retry_count=4,
                                    database_host="localhost",
                                    connection_timeout=30)
    
    print("\n23. Testing error pattern detection:")
    logger.log_error_pattern("connection_timeout", 5, "last_10_minutes",
                           affected_services=["database", "cache"],
                           severity="high")
    
    print("\nStructured logging test completed!")
    print("Check the log file for JSON-formatted file output.")


if __name__ == "__main__":
    test_structured_logging()