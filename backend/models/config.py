"""
Pydantic models for application configuration.

These models define the complete configuration structure for the Source-to-Target
Mapping Platform. Configuration is stored in a local JSON file (app_config.json)
and can be modified through the Admin Configuration page.

Based on the original Streamlit app's configuration structure.

Models:
- DatabaseConfig: Databricks database and table connections
- AIModelConfig: AI/LLM model settings
- VectorSearchConfig: Vector search endpoint and index
- UIConfig: User interface preferences
- SupportConfig: Support and help links
- SecurityConfig: Admin access and authentication
- AppConfig: Root configuration containing all sections
"""
from pydantic import BaseModel, Field
from typing import Optional


class DatabaseConfig(BaseModel):
    """
    Database connection configuration for Databricks SQL Warehouse.
    
    V4 uses standard table names derived from catalog.schema:
    - semantic_fields: Target field definitions
    - unmapped_fields: Source fields awaiting mapping  
    - mapped_fields: Complete mappings with SQL expressions
    - mapping_projects: User projects
    - target_table_status: Table-level mapping status
    - mapping_suggestions: AI-generated suggestions
    - mapping_feedback: Rejected suggestions for AI learning
    
    Just configure catalog and schema - table names are standard.
    
    Attributes:
        catalog: Databricks catalog name
        schema: Databricks schema name  
        server_hostname: Databricks workspace hostname
        http_path: SQL warehouse HTTP path for connections
    """
    catalog: str = Field(default="oztest_dev", description="Databricks catalog name")
    schema: str = Field(default="smartmapper", description="Databricks schema name")
    server_hostname: str = Field(default="Acuity-oz-test-ue1.cloud.databricks.com", description="Databricks workspace hostname")
    http_path: str = Field(default="/sql/1.0/warehouses/173ea239ed13be7d", description="SQL warehouse HTTP path")
    
    # Computed table names - not configurable, derived from catalog.schema
    @property
    def semantic_fields_table(self) -> str:
        return f"{self.catalog}.{self.schema}.semantic_fields"
    
    @property
    def unmapped_fields_table(self) -> str:
        return f"{self.catalog}.{self.schema}.unmapped_fields"
    
    @property
    def mapped_fields_table(self) -> str:
        return f"{self.catalog}.{self.schema}.mapped_fields"
    
    @property
    def mapping_projects_table(self) -> str:
        return f"{self.catalog}.{self.schema}.mapping_projects"
    
    @property
    def target_table_status_table(self) -> str:
        return f"{self.catalog}.{self.schema}.target_table_status"
    
    @property
    def mapping_suggestions_table(self) -> str:
        return f"{self.catalog}.{self.schema}.mapping_suggestions"
    
    @property
    def mapping_feedback_table(self) -> str:
        return f"{self.catalog}.{self.schema}.mapping_feedback"


class AIModelConfig(BaseModel):
    """
    AI model configuration for LLM-powered mapping suggestions (V2).
    
    Defines the foundation model endpoint used for generating intelligent
    mapping suggestions with reasoning. V2 uses historical mappings from
    mapped_fields table for pattern learning.
    
    Attributes:
        previous_mappings_table_name: Historical mappings table name (just table, catalog.schema from DatabaseConfig)
        foundation_model_endpoint: Name of the Databricks foundation model endpoint
        default_prompt: Default system prompt for the LLM (currently unused)
    """
    previous_mappings_table_name: str = Field(default="mapped_fields", description="Historical mappings table (V2)")
    foundation_model_endpoint: str = Field(default="databricks-meta-llama-3-3-70b-instruct", description="Foundation model endpoint name")
    default_prompt: str = Field(default="", description="Default LLM system prompt")


class VectorSearchConfig(BaseModel):
    """
    Vector search configuration for semantic similarity matching (V3).
    
    Defines the Databricks Vector Search configuration for V4 AI mapping.
    
    V4 uses only the unmapped_fields index for source field matching during discovery.
    Pattern lookup uses SQL exact match on table/column names.
    
    NOTE: Vector search index names must be fully qualified (catalog.schema.index_name)
    because they are managed separately from SQL tables.
    
    Attributes:
        unmapped_fields_index: Vector search index for source field matching (catalog.schema.index_name)
        endpoint_name: Name of the vector search endpoint
    """
    unmapped_fields_index: str = Field(default="oztest_dev.smartmapper.unmapped_fields_vs", description="Vector search index for source field matching (fully qualified)")
    endpoint_name: str = Field(default="s2t_vsendpoint", description="Vector search endpoint name")


class UIConfig(BaseModel):
    """
    User interface settings and preferences.
    
    Controls the appearance and behavior of the Vue.js frontend.
    
    Attributes:
        app_title: Application title shown in browser tab and header
        theme_color: Primary theme color (hex code)
        sidebar_expanded: Whether sidebar starts expanded (not currently used)
    """
    app_title: str = Field(default="Source-to-Target Mapping Platform", description="Application title")
    theme_color: str = Field(default="#4a5568", description="Primary theme color (hex)")
    sidebar_expanded: bool = Field(default=True, description="Initial sidebar state")


class SupportConfig(BaseModel):
    """
    Support and help resources configuration.
    
    Defines links to external support resources.
    
    Attributes:
        support_url: URL for user support documentation or help desk
    """
    support_url: str = Field(default="https://mygainwell.sharepoint.com", description="Support/help URL")


class SecurityConfig(BaseModel):
    """
    Security and authorization configuration.
    
    Defines admin access control through Databricks workspace groups.
    Users in the admin_group_name have access to configuration management.
    
    Attributes:
        admin_group_name: Databricks workspace group name for admin users
        enable_password_auth: Whether to enable password authentication (not currently used)
        admin_password_hash: Hashed admin password (not currently used)
    """
    admin_group_name: str = Field(default="gia-oztest-dev-ue1-data-engineers", description="Admin group name in Databricks workspace")
    enable_password_auth: bool = Field(default=True, description="Enable password auth (unused)")
    admin_password_hash: str = Field(default="", description="Admin password hash (unused)")


class AppConfig(BaseModel):
    """
    Complete application configuration.
    
    Root configuration object containing all configuration sections. This is
    the top-level model that gets serialized to/from app_config.json.
    
    Attributes:
        database: Database connection settings
        ai_model: AI/LLM model configuration
        vector_search: Vector search settings
        ui: User interface preferences
        support: Support resource links
        security: Admin access control
    """
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database configuration")
    ai_model: AIModelConfig = Field(default_factory=AIModelConfig, description="AI model configuration")
    vector_search: VectorSearchConfig = Field(default_factory=VectorSearchConfig, description="Vector search configuration")
    ui: UIConfig = Field(default_factory=UIConfig, description="UI configuration")
    support: SupportConfig = Field(default_factory=SupportConfig, description="Support configuration")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")

