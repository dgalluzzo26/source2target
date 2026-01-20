"""
Configuration management service.
Stores and retrieves application configuration from a LOCAL JSON file.
Based on the Streamlit app's configuration manager.
"""
import os
import json
from pathlib import Path
from typing import Optional
from backend.models.config import AppConfig


class ConfigService:
    """Service for managing application configuration with local file storage."""
    
    def __init__(self):
        """Initialize the configuration service."""
        # Store config in the project root
        self.config_file = Path(__file__).parent.parent.parent / "app_config.json"
        self._config: Optional[AppConfig] = None
    
    def get_config(self) -> AppConfig:
        """
        Get the current application configuration.
        Loads from file if not cached, otherwise returns cached config.
        """
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def load_config(self) -> AppConfig:
        """
        Load configuration from the local JSON file.
        Falls back to default configuration if file doesn't exist.
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_dict = json.load(f)
                    self._config = AppConfig(**config_dict)
                    print(f"Configuration loaded from {self.config_file}")
                    return self._config
            else:
                print(f"Config file not found at {self.config_file}, using defaults")
                # Create default config file
                default_config = AppConfig()
                self.save_config(default_config)
                return default_config
                
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            return AppConfig()
    
    def save_config(self, config: AppConfig) -> bool:
        """
        Save configuration to the local JSON file.
        
        Args:
            config: The configuration to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize configuration to JSON
            config_dict = config.model_dump()
            
            # Write to file with pretty formatting
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            print(f"Configuration saved to {self.config_file}")
            
            # Update cache
            self._config = config
            
            return True
            
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
            return False
    
    def clear_cache(self):
        """Clear the cached configuration, forcing a reload on next access."""
        self._config = None
    
    def get_vector_search_config(self) -> dict:
        """
        Get vector search configuration.
        Convenience method for system status checks.
        V4 only uses unmapped_fields_index for source field matching.
        """
        config = self.get_config()
        return {
            "endpoint_name": config.vector_search.endpoint_name,
            "index_name": config.vector_search.unmapped_fields_index
        }
    
    def get_ai_model_endpoint(self) -> str:
        """
        Get AI model endpoint name.
        Convenience method for system status checks.
        """
        config = self.get_config()
        return config.ai_model.foundation_model_endpoint
    
    def get_admin_group(self) -> str:
        """
        Get admin group name.
        Convenience method for auth checks.
        """
        config = self.get_config()
        return config.security.admin_group_name
    
    def get_database_config(self) -> dict:
        """
        Get database configuration.
        Convenience method for system status checks.
        """
        config = self.get_config()
        return {
            "warehouse_name": config.database.warehouse_name,
            "catalog": config.database.catalog,
            "schema": config.database.schema,
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path
        }


# Global instance
config_service = ConfigService()

