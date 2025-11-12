#!/usr/bin/env python3
"""
Test script for the enhanced configuration system validation.
"""

import sys
import os
import tempfile
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar_ai_agent.config import Config


def test_default_configuration():
    """Test default configuration values."""
    print("Testing default configuration values...")
    
    # Mock required environment variables
    with patch.dict(os.environ, {
        'SONAR_TOKEN': 'test_token',
        'TARGET_REPO_URL': 'https://github.com/test/repo',
        'TARGET_REPO_PATH': '/tmp/test_repo',
        'GITHUB_TOKEN': 'test_github_token'
    }):
        config = Config()
        
        # Test structured logging defaults
        assert config.structured_logging_enabled == True
        assert config.console_color_enabled == True
        assert config.metadata_max_depth == 3
        assert config.metadata_max_length == 1000
        assert config.performance_logging_enabled == True
        assert config.error_stack_trace_enabled == True
        assert config.correlation_tracking_enabled == True
        
        # Test performance threshold defaults
        assert config.slow_operation_threshold_ms == 5000
        assert config.very_slow_operation_threshold_ms == 10000
        assert config.low_throughput_threshold == 1.0
        assert config.high_error_rate_threshold == 0.1
        
        print("✅ Default configuration values are correct")


def test_custom_configuration():
    """Test custom configuration values from environment."""
    print("Testing custom configuration values...")
    
    custom_env = {
        'SONAR_TOKEN': 'test_token',
        'TARGET_REPO_URL': 'https://github.com/test/repo',
        'TARGET_REPO_PATH': '/tmp/test_repo',
        'GITHUB_TOKEN': 'test_github_token',
        
        # Custom structured logging values
        'STRUCTURED_LOGGING_ENABLED': 'false',
        'CONSOLE_COLOR_ENABLED': 'false',
        'METADATA_MAX_DEPTH': '5',
        'METADATA_MAX_LENGTH': '2000',
        'PERFORMANCE_LOGGING_ENABLED': 'false',
        'ERROR_STACK_TRACE_ENABLED': 'false',
        'CORRELATION_TRACKING_ENABLED': 'false',
        
        # Custom performance thresholds
        'SLOW_OPERATION_THRESHOLD_MS': '3000',
        'VERY_SLOW_OPERATION_THRESHOLD_MS': '8000',
        'LOW_THROUGHPUT_THRESHOLD': '2.5',
        'HIGH_ERROR_RATE_THRESHOLD': '0.05'
    }
    
    with patch.dict(os.environ, custom_env):
        config = Config()
        
        # Test custom structured logging values
        assert config.structured_logging_enabled == False
        assert config.console_color_enabled == False
        assert config.metadata_max_depth == 5
        assert config.metadata_max_length == 2000
        assert config.performance_logging_enabled == False
        assert config.error_stack_trace_enabled == False
        assert config.correlation_tracking_enabled == False
        
        # Test custom performance thresholds
        assert config.slow_operation_threshold_ms == 3000
        assert config.very_slow_operation_threshold_ms == 8000
        assert config.low_throughput_threshold == 2.5
        assert config.high_error_rate_threshold == 0.05
        
        print("✅ Custom configuration values are correct")


def test_configuration_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")
    
    base_env = {
        'SONAR_TOKEN': 'test_token',
        'TARGET_REPO_URL': 'https://github.com/test/repo',
        'TARGET_REPO_PATH': '/tmp/test_repo',
        'GITHUB_TOKEN': 'test_github_token'
    }
    
    # Test invalid metadata depth
    print("  Testing invalid metadata depth...")
    with patch.dict(os.environ, {**base_env, 'METADATA_MAX_DEPTH': '0'}):
        try:
            Config()
            assert False, "Should have raised ValueError for invalid metadata depth"
        except ValueError as e:
            assert "METADATA_MAX_DEPTH must be between 1 and 10" in str(e)
            print("    ✅ Invalid metadata depth validation works")
    
    # Test invalid metadata length
    print("  Testing invalid metadata length...")
    with patch.dict(os.environ, {**base_env, 'METADATA_MAX_LENGTH': '50'}):
        try:
            Config()
            assert False, "Should have raised ValueError for invalid metadata length"
        except ValueError as e:
            assert "METADATA_MAX_LENGTH must be between 100 and 10000" in str(e)
            print("    ✅ Invalid metadata length validation works")
    
    # Test invalid slow operation threshold
    print("  Testing invalid slow operation threshold...")
    with patch.dict(os.environ, {**base_env, 'SLOW_OPERATION_THRESHOLD_MS': '50'}):
        try:
            Config()
            assert False, "Should have raised ValueError for invalid slow operation threshold"
        except ValueError as e:
            assert "SLOW_OPERATION_THRESHOLD_MS must be at least 100ms" in str(e)
            print("    ✅ Invalid slow operation threshold validation works")
    
    # Test invalid very slow operation threshold
    print("  Testing invalid very slow operation threshold...")
    with patch.dict(os.environ, {**base_env, 
                                'SLOW_OPERATION_THRESHOLD_MS': '5000',
                                'VERY_SLOW_OPERATION_THRESHOLD_MS': '3000'}):
        try:
            Config()
            assert False, "Should have raised ValueError for invalid very slow operation threshold"
        except ValueError as e:
            assert "VERY_SLOW_OPERATION_THRESHOLD_MS must be greater than SLOW_OPERATION_THRESHOLD_MS" in str(e)
            print("    ✅ Invalid very slow operation threshold validation works")
    
    # Test invalid error rate threshold
    print("  Testing invalid error rate threshold...")
    with patch.dict(os.environ, {**base_env, 'HIGH_ERROR_RATE_THRESHOLD': '1.5'}):
        try:
            Config()
            assert False, "Should have raised ValueError for invalid error rate threshold"
        except ValueError as e:
            assert "HIGH_ERROR_RATE_THRESHOLD must be between 0 and 1" in str(e)
            print("    ✅ Invalid error rate threshold validation works")
    
    print("✅ Configuration validation works correctly")


def test_config_representation():
    """Test configuration string representation."""
    print("Testing configuration string representation...")
    
    with patch.dict(os.environ, {
        'SONAR_TOKEN': 'test_token',
        'TARGET_REPO_URL': 'https://github.com/test/repo',
        'TARGET_REPO_PATH': '/tmp/test_repo',
        'GITHUB_TOKEN': 'test_github_token'
    }):
        config = Config()
        config_str = str(config)
        
        # Check that structured logging info is included
        assert "structured_logging=True" in config_str
        assert "performance_logging=True" in config_str
        
        # Check that sensitive data is not included
        assert "test_token" not in config_str
        assert "test_github_token" not in config_str
        
        print("✅ Configuration string representation is correct")


def test_backward_compatibility():
    """Test that existing configurations still work."""
    print("Testing backward compatibility...")
    
    # Test with only old environment variables (no new structured logging vars)
    old_env = {
        'SONAR_TOKEN': 'test_token',
        'TARGET_REPO_URL': 'https://github.com/test/repo',
        'TARGET_REPO_PATH': '/tmp/test_repo',
        'GITHUB_TOKEN': 'test_github_token',
        'LOG_LEVEL': 'DEBUG',
        'LOG_FILE': 'custom.log'
    }
    
    with patch.dict(os.environ, old_env, clear=True):
        config = Config()
        
        # Old settings should still work
        assert config.log_level == 'DEBUG'
        assert config.log_file == 'custom.log'
        
        # New settings should have defaults
        assert config.structured_logging_enabled == True
        assert config.performance_logging_enabled == True
        
        print("✅ Backward compatibility maintained")


def main():
    """Run all configuration tests."""
    print("Testing Enhanced Configuration System...")
    print("=" * 50)
    
    try:
        test_default_configuration()
        test_custom_configuration()
        test_configuration_validation()
        test_config_representation()
        test_backward_compatibility()
        
        print("\n🎉 All configuration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()