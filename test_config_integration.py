#!/usr/bin/env python3
"""
Test script to verify configuration integration with the logging system.
"""

import sys
import os
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar_ai_agent.config import Config
from sonar_ai_agent.utils.logger import get_logger


def test_config_integration():
    """Test that the logger properly uses configuration parameters."""
    print("Testing Configuration Integration with Logging System...")
    print("=" * 60)
    
    # Test with custom configuration
    custom_env = {
        'SONAR_TOKEN': 'test_token',
        'TARGET_REPO_URL': 'https://github.com/test/repo',
        'TARGET_REPO_PATH': '/tmp/test_repo',
        'GITHUB_TOKEN': 'test_github_token',
        
        # Custom structured logging configuration
        'CONSOLE_COLOR_ENABLED': 'false',
        'METADATA_MAX_DEPTH': '2',
        'METADATA_MAX_LENGTH': '500',
        'SLOW_OPERATION_THRESHOLD_MS': '2000',
        'HIGH_ERROR_RATE_THRESHOLD': '0.05'
    }
    
    with patch.dict(os.environ, custom_env):
        config = Config()
        logger = get_logger(config, "test_config_integration")
        
        print("\n1. Testing configuration values are applied:")
        print(f"   Console color enabled: {config.console_color_enabled}")
        print(f"   Metadata max depth: {config.metadata_max_depth}")
        print(f"   Metadata max length: {config.metadata_max_length}")
        print(f"   Slow operation threshold: {config.slow_operation_threshold_ms}ms")
        print(f"   High error rate threshold: {config.high_error_rate_threshold}")
        
        print("\n2. Testing logger with custom configuration:")
        
        # Test metadata truncation with custom length
        long_data = "x" * 600  # Exceeds custom limit of 500
        logger.info("Testing metadata truncation",
                   long_field=long_data,
                   short_field="normal_data")
        
        # Test nested metadata with custom depth
        deep_nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "should_be_truncated"
                    }
                }
            }
        }
        logger.info("Testing nested metadata depth",
                   nested_data=deep_nested)
        
        # Test performance threshold with custom values
        logger.log_performance("custom_threshold_test", 2.5,  # Should trigger warning with 2000ms threshold
                              items_processed=10)
        
        # Test error rate threshold
        logger.log_performance("error_rate_test", 1.0,
                              items_processed=100,
                              errors_encountered=6,  # 6% error rate, should trigger with 5% threshold
                              error_rate=0.06)
        
        print("\n3. Testing performance context with custom thresholds:")
        with logger.performance_context("threshold_test_operation") as ctx:
            import time
            time.sleep(0.1)  # Should be fast enough to not trigger thresholds
            ctx['items_processed'] = 5
        
        print("\n✅ Configuration integration test completed successfully!")
        print("Check the console output above to verify custom settings are applied.")


if __name__ == "__main__":
    test_config_integration()