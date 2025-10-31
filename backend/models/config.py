"""
Configuration models for the application.
Based on the Streamlit app's configuration structure.
"""
from pydantic import BaseModel, Field
from typing import Optional


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    warehouse_name: str = Field(default="gia-oztest-dev-data-warehouse")
    mapping_table: str = Field(default="oztest_dev.source_to_target.mappings")
    semantic_table: str = Field(default="oztest_dev.source_to_target.silver_semantic_full")
    server_hostname: str = Field(default="Acuity-oz-test-ue1.cloud.databricks.com")
    http_path: str = Field(default="/sql/1.0/warehouses/173ea239ed13be7d")


class AIModelConfig(BaseModel):
    """AI model configuration."""
    previous_mappings_table_name: str = Field(default="oztest_dev.source_to_target.train_with_comments")
    foundation_model_endpoint: str = Field(default="databricks-meta-llama-3-3-70b-instruct")
    default_prompt: str = Field(default="")


class VectorSearchConfig(BaseModel):
    """Vector search configuration."""
    index_name: str = Field(default="oztest_dev.source_to_target.silver_semantic_full_vs")
    endpoint_name: str = Field(default="s2t_vsendpoint")


class UIConfig(BaseModel):
    """UI settings configuration."""
    app_title: str = Field(default="Source-to-Target Mapping Platform")
    theme_color: str = Field(default="#4a5568")
    sidebar_expanded: bool = Field(default=True)


class SupportConfig(BaseModel):
    """Support configuration."""
    support_url: str = Field(default="https://mygainwell.sharepoint.com")


class SecurityConfig(BaseModel):
    """Security configuration."""
    admin_group_name: str = Field(default="gia-oztest-dev-ue1-data-engineers")
    enable_password_auth: bool = Field(default=True)
    admin_password_hash: str = Field(default="")


class AppConfig(BaseModel):
    """Complete application configuration."""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ai_model: AIModelConfig = Field(default_factory=AIModelConfig)
    vector_search: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    support: SupportConfig = Field(default_factory=SupportConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

