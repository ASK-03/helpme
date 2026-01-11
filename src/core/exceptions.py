class HelpMeError(Exception):
    """Base exception for HelpMe application."""
    pass

class LLMConfigurationError(HelpMeError):
    """Exception raised for configuration errors in LLM providers"""
    pass

class LLMResponseError(HelpMeError):
    """Exception raised for API response errors"""
    pass
