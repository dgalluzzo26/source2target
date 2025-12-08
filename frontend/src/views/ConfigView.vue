<template>
  <div class="config-view">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: flex-start;">
      <div>
        <h1>
          <i class="pi pi-cog"></i>
          Configuration Settings
        </h1>
        <p>Manage enterprise application settings, database connections, and AI model configurations for healthcare data processing.</p>
      </div>
      <HelpButton 
        help-type="admin-config"
        label="Admin Guide"
        severity="info"
        icon="pi pi-book"
        tooltip="Configuration management documentation"
      />
    </div>

    <!-- Admin Authentication Check -->
    <div v-if="!isAuthenticated" class="auth-required">
      <Message severity="warn" :closable="false">
        <strong>Admin Access Required:</strong> Configuration management requires administrator privileges.
        Please contact your system administrator for access.
      </Message>
    </div>

    <!-- Configuration Tabs -->
    <TabView v-else>
      <!-- Database Configuration Tab -->
      <TabPanel>
        <template #header>
          <i class="pi pi-database"></i>
          <span class="tab-label">Database</span>
        </template>
        <div class="config-section">
          <h3>Database Configuration</h3>
          <p>Configure database connections and table references.</p>

          <!-- Connection Help -->
          <Accordion class="connection-help">
            <AccordionTab>
              <template #header>
                <i class="pi pi-info-circle"></i>
                <span class="accordion-label">How to find connection details</span>
              </template>
              <div class="help-content">
                <h4>Server Hostname:</h4>
                <ol>
                  <li>Go to your Databricks workspace</li>
                  <li>Look at the URL: <code>https://your-workspace.cloud.databricks.com</code></li>
                  <li>Copy the part after <code>https://</code>: <code>your-workspace.cloud.databricks.com</code></li>
                </ol>

                <h4>HTTP Path:</h4>
                <ol>
                  <li>Go to SQL Warehouses in your Databricks workspace</li>
                  <li>Click on your warehouse name</li>
                  <li>Go to "Connection details" tab</li>
                  <li>Copy the "HTTP Path" value (e.g., <code>/sql/1.0/warehouses/abc123def456</code>)</li>
                </ol>

                <p><strong>Note:</strong> HTTP Path is optional - the app will auto-detect it if you leave it empty.</p>
              </div>
            </AccordionTab>
          </Accordion>

          <!-- Database Settings Form -->
          <div class="config-form">
            <div class="field">
              <label for="warehouse_name">Warehouse Name</label>
              <InputText 
                id="warehouse_name"
                v-model="config.database.warehouse_name"
                placeholder="Name of the Databricks SQL warehouse to use"
                class="w-full"
              />
              <small>Name of the Databricks SQL warehouse to use</small>
            </div>

            <div class="field-group">
              <div class="field flex-3">
                <label for="server_hostname">Server Hostname</label>
                <InputText 
                  id="server_hostname"
                  v-model="config.database.server_hostname"
                  placeholder="your-workspace.cloud.databricks.com"
                  class="w-full"
                />
                <small>Databricks workspace hostname (e.g., your-workspace.cloud.databricks.com)</small>
              </div>
              <div class="field flex-1">
                <label>&nbsp;</label>
                <Button 
                  icon="pi pi-link" 
                  label="Test Connection"
                  @click="testDatabaseConnection"
                  :loading="loading.testConnection"
                  severity="help"
                  class="w-full"
                />
              </div>
            </div>

            <div class="field">
              <label for="http_path">HTTP Path (Optional)</label>
              <InputText 
                id="http_path"
                v-model="config.database.http_path"
                placeholder="/sql/1.0/warehouses/your-warehouse-id"
                class="w-full"
              />
              <small>SQL warehouse HTTP path - leave empty for auto-detection</small>
            </div>

            <div class="field">
              <label for="catalog">Catalog</label>
              <InputText 
                id="catalog"
                v-model="config.database.catalog"
                placeholder="e.g., oztest_dev"
                class="w-full"
              />
              <small>Databricks catalog name</small>
            </div>

            <div class="field">
              <label for="schema">Schema</label>
              <InputText 
                id="schema"
                v-model="config.database.schema"
                placeholder="e.g., source2target"
                class="w-full"
              />
              <small>Databricks schema name</small>
            </div>

            <Divider />

            <h4>Table Configuration</h4>
            <Message severity="info" :closable="false" class="table-config-note">
              <strong>Note:</strong> Enter table names only. The catalog and schema specified above will be automatically prepended.
              <br />
              Example: Enter <code>semantic_fields</code> instead of <code>catalog.schema.semantic_fields</code>
            </Message>

            <div class="field">
              <label for="semantic_fields_table">Semantic Fields Table</label>
              <InputText 
                id="semantic_fields_table"
                v-model="config.database.semantic_fields_table"
                placeholder="semantic_fields"
                class="w-full"
              />
              <small>Target field definitions for AI mapping (table name only)</small>
            </div>

            <div class="field">
              <label for="unmapped_fields_table">Unmapped Fields Table</label>
              <InputText 
                id="unmapped_fields_table"
                v-model="config.database.unmapped_fields_table"
                placeholder="unmapped_fields"
                class="w-full"
              />
              <small>Source fields awaiting mapping (table name only)</small>
            </div>

            <div class="field">
              <label for="mapped_fields_table">Mapped Fields Table</label>
              <InputText 
                id="mapped_fields_table"
                v-model="config.database.mapped_fields_table"
                placeholder="mapped_fields"
                class="w-full"
              />
              <small>Complete mappings with SQL expressions (table name only)</small>
            </div>

            <div class="field">
              <label for="mapping_feedback_table">Mapping Feedback Table</label>
              <InputText 
                id="mapping_feedback_table"
                v-model="config.database.mapping_feedback_table"
                placeholder="mapping_feedback"
                class="w-full"
              />
              <small>User feedback on AI suggestions (table name only)</small>
            </div>

            <div class="field">
              <label for="transformation_library_table">Transformation Library Table</label>
              <InputText 
                id="transformation_library_table"
                v-model="config.database.transformation_library_table"
                placeholder="transformation_library"
                class="w-full"
              />
              <small>Reusable transformation templates (table name only)</small>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- AI/ML Models Tab -->
      <TabPanel>
        <template #header>
          <i class="pi pi-bolt"></i>
          <span class="tab-label">AI/ML Models</span>
        </template>
        <div class="config-section">
          <h3>AI/ML Model Configuration</h3>
          <p>Configure AI model endpoints and parameters for intelligent field mapping.</p>

          <div class="config-form">
            <div class="field">
              <label for="foundation_model_endpoint">Foundation Model Endpoint</label>
              <InputText 
                id="foundation_model_endpoint"
                v-model="config.ai_model.foundation_model_endpoint"
                placeholder="databricks-meta-llama-3-3-70b-instruct"
                class="w-full"
              />
              <small>Databricks Foundation Model endpoint for AI suggestions</small>
            </div>

            <div class="field">
              <label for="previous_mappings_table">Previous Mappings Table</label>
              <InputText 
                id="previous_mappings_table"
                v-model="config.ai_model.previous_mappings_table_name"
                placeholder="mapped_fields"
                class="w-full"
              />
              <small>Table containing historical mappings for training context (table name only)</small>
            </div>

            <div class="field">
              <label for="default_prompt">Default AI Prompt Template</label>
              <Textarea 
                id="default_prompt"
                v-model="config.ai_model.default_prompt"
                rows="10"
                class="w-full"
                placeholder="Enter the default prompt template for AI mapping suggestions..."
              />
              <small>Template used for generating AI mapping suggestions</small>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- Vector Search Tab -->
      <TabPanel>
        <template #header>
          <i class="pi pi-search"></i>
          <span class="tab-label">Vector Search</span>
        </template>
        <div class="config-section">
          <h3>Vector Search Configuration</h3>
          <p>Configure vector search index for semantic field matching.</p>

          <div class="config-form">
            <div class="field">
              <label for="semantic_fields_index">Semantic Fields VS Index</label>
              <InputText 
                id="semantic_fields_index"
                v-model="config.vector_search.semantic_fields_index"
                placeholder="catalog.schema.semantic_fields_vs"
                class="w-full"
              />
              <small>Vector search index for TARGET field matching (fully qualified: catalog.schema.index_name)</small>
            </div>

            <div class="field">
              <label for="mapped_fields_index">Mapped Fields VS Index</label>
              <InputText 
                id="mapped_fields_index"
                v-model="config.vector_search.mapped_fields_index"
                placeholder="catalog.schema.mapped_fields_vs"
                class="w-full"
              />
              <small>Vector search index for historical MAPPING PATTERNS (fully qualified: catalog.schema.index_name)</small>
            </div>

            <div class="field-group">
              <div class="field flex-3">
                <label for="vector_endpoint_name">Vector Search Endpoint</label>
                <InputText 
                  id="vector_endpoint_name"
                  v-model="config.vector_search.endpoint_name"
                  placeholder="smartmapper_vs_endpoint"
                  class="w-full"
                />
                <small>Name of the Vector Search endpoint</small>
              </div>
              <div class="field flex-1">
                <label>&nbsp;</label>
                <Button 
                  icon="pi pi-search" 
                  label="Test Vector Search"
                  @click="testVectorSearch"
                  :loading="loading.testVectorSearch"
                  severity="info"
                  class="w-full"
                />
              </div>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- UI Settings Tab -->
      <TabPanel>
        <template #header>
          <i class="pi pi-palette"></i>
          <span class="tab-label">UI Settings</span>
        </template>
        <div class="config-section">
          <h3>User Interface Settings</h3>
          <p>Customize the application appearance and behavior.</p>

          <div class="config-form">
            <div class="field">
              <label for="app_title">Application Title</label>
              <InputText 
                id="app_title"
                v-model="config.ui.app_title"
                placeholder="Source-to-Target Mapping Platform"
                class="w-full"
              />
              <small>Title displayed in the application header</small>
            </div>

            <div class="field">
              <label for="theme_color">Theme Color</label>
              <InputText 
                id="theme_color"
                v-model="config.ui.theme_color"
                placeholder="#4a5568"
                class="w-full"
              />
              <small>Primary theme color (hex code)</small>
            </div>

            <div class="field">
              <label class="checkbox-label">
                <Checkbox 
                  v-model="config.ui.sidebar_expanded"
                  :binary="true"
                />
                <span>Sidebar Expanded by Default</span>
              </label>
              <small>Whether the sidebar should be expanded when the app loads</small>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- Support Tab -->
      <TabPanel>
        <template #header>
          <i class="pi pi-question-circle"></i>
          <span class="tab-label">Support</span>
        </template>
        <div class="config-section">
          <h3>Support Configuration</h3>
          <p>Configure support and help resources.</p>

          <div class="config-form">
            <div class="field">
              <label for="support_url">Support URL</label>
              <InputText 
                id="support_url"
                v-model="config.support.support_url"
                placeholder="https://mygainwell.sharepoint.com"
                class="w-full"
              />
              <small>URL for support documentation and resources</small>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- Security Tab -->
      <TabPanel>
        <template #header>
          <i class="pi pi-lock"></i>
          <span class="tab-label">Security</span>
        </template>
        <div class="config-section">
          <h3>Security Configuration</h3>
          <p>Configure authentication and authorization settings.</p>

          <div class="config-form">
            <div class="field">
              <label for="admin_group_name">Admin Group Name</label>
              <InputText 
                id="admin_group_name"
                v-model="config.security.admin_group_name"
                placeholder="gia-oztest-dev-ue1-data-engineers"
                class="w-full"
              />
              <small>Databricks group name for administrator access</small>
            </div>

            <div class="field">
              <label class="checkbox-label">
                <Checkbox 
                  v-model="config.security.enable_password_auth"
                  :binary="true"
                />
                <span>Enable Password Authentication</span>
              </label>
              <small>Allow password-based authentication as fallback</small>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- Actions Tab -->
      <TabPanel>
        <template #header>
          <i class="pi pi-wrench"></i>
          <span class="tab-label">Actions</span>
        </template>
        <div class="config-section">
          <h3>Configuration Actions</h3>
          <p>Import, export, and reset configuration settings.</p>

          <div class="actions-grid">
            <Card class="action-card">
              <template #title>Export Configuration</template>
              <template #content>
                <p>Download current configuration as JSON file for backup or sharing.</p>
                <Button 
                  icon="pi pi-download" 
                  label="Download Config"
                  @click="exportConfiguration"
                  :loading="loading.export"
                  severity="info"
                  class="w-full"
                />
              </template>
            </Card>

            <Card class="action-card">
              <template #title>Import Configuration</template>
              <template #content>
                <p>Upload and apply a configuration file.</p>
                <FileUpload 
                  mode="basic" 
                  accept=".json"
                  :maxFileSize="1000000"
                  @upload="importConfiguration"
                  :auto="true"
                  chooseLabel="Import Config"
                />
              </template>
            </Card>

            <Card class="action-card">
              <template #title>Reset Configuration</template>
              <template #content>
                <p>Reset all settings to default values.</p>
                <Button 
                  icon="pi pi-refresh" 
                  label="Reset to Defaults"
                  @click="resetConfiguration"
                  :loading="loading.reset"
                  severity="danger"
                  class="w-full"
                />
              </template>
            </Card>

            <Card class="action-card">
              <template #title>Save Configuration</template>
              <template #content>
                <p>Save current configuration changes.</p>
                <Button 
                  icon="pi pi-save" 
                  label="Save Changes"
                  @click="saveConfiguration"
                  :loading="loading.save"
                  severity="success"
                  class="w-full"
                />
              </template>
            </Card>
          </div>

          <Divider />

          <div class="current-config">
            <h4>Current Configuration</h4>
            <Accordion>
              <AccordionTab header="📋 View Current Config">
                <pre class="config-json">{{ JSON.stringify(config, null, 2) }}</pre>
              </AccordionTab>
            </Accordion>
          </div>
        </div>
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import HelpButton from '@/components/HelpButton.vue'

const userStore = useUserStore()

// Check if user is authenticated as admin (disabled for testing)
const isAuthenticated = computed(() => true) // userStore.isAdmin

// Configuration data structure based on original app
// NOTE: Table names should be just the table name, catalog.schema is prepended automatically
// V3 Schema: 5 core tables (semantic_fields, unmapped_fields, mapped_fields, mapping_feedback, transformation_library)
const config = ref({
  database: {
    warehouse_name: 'gia-oztest-dev-data-warehouse',
    catalog: 'oztest_dev',
    schema: 'smartmapper',
    semantic_fields_table: 'semantic_fields',
    unmapped_fields_table: 'unmapped_fields',
    mapped_fields_table: 'mapped_fields',
    mapping_feedback_table: 'mapping_feedback',
    transformation_library_table: 'transformation_library',
    server_hostname: 'Acuity-oz-test-ue1.cloud.databricks.com',
    http_path: '/sql/1.0/warehouses/173ea239ed13be7d'
  },
  ai_model: {
    previous_mappings_table_name: 'mapped_fields',
    foundation_model_endpoint: 'databricks-meta-llama-3-3-70b-instruct',
    default_prompt: ''
  },
  ui: {
    app_title: 'Smart Mapper',
    theme_color: '#4a5568',
    sidebar_expanded: true
  },
  support: {
    support_url: 'https://mygainwell.sharepoint.com'
  },
  vector_search: {
    semantic_fields_index: 'oztest_dev.smartmapper.semantic_fields_vs',
    mapped_fields_index: 'oztest_dev.smartmapper.mapped_fields_vs',
    endpoint_name: 'smartmapper_vs_endpoint'
  },
  security: {
    admin_group_name: 'gia-oztest-dev-ue1-data-engineers',
    enable_password_auth: true,
    admin_password_hash: ''
  }
})

// Loading states
const loading = ref({
  testConnection: false,
  testVectorSearch: false,
  save: false,
  export: false,
  reset: false
})

// Methods (Frontend-only mode with dummy data)
const loadConfiguration = async () => {
  console.log('Configuration loaded from dummy data')
}

const testDatabaseConnection = async () => {
  loading.value.testConnection = true
  setTimeout(() => {
    console.log('Database connection test simulated - SUCCESS')
    loading.value.testConnection = false
  }, 2000)
}

const testVectorSearch = async () => {
  loading.value.testVectorSearch = true
  setTimeout(() => {
    console.log('Vector search test simulated - SUCCESS')
    loading.value.testVectorSearch = false
  }, 2000)
}

const saveConfiguration = async () => {
  loading.value.save = true
  setTimeout(() => {
    console.log('Configuration saved (simulated)')
    loading.value.save = false
  }, 1000)
}

const exportConfiguration = async () => {
  loading.value.export = true
  try {
    const configJson = JSON.stringify(config.value, null, 2)
    const blob = new Blob([configJson], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'app_config.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    console.log('Configuration exported')
  } catch (error) {
    console.error('Failed to export configuration:', error)
  } finally {
    loading.value.export = false
  }
}

const importConfiguration = (event: any) => {
  const file = event.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedConfig = JSON.parse(e.target?.result as string)
        config.value = { ...config.value, ...importedConfig }
        console.log('Configuration imported')
      } catch (error) {
        console.error('Failed to import configuration:', error)
      }
    }
    reader.readAsText(file)
  }
}

const resetConfiguration = async () => {
  loading.value.reset = true
  setTimeout(() => {
    // Reset to V3 default values (table names only, catalog.schema prepended automatically)
    config.value = {
      database: {
        warehouse_name: 'gia-oztest-dev-data-warehouse',
        catalog: 'oztest_dev',
        schema: 'smartmapper',
        semantic_fields_table: 'semantic_fields',
        unmapped_fields_table: 'unmapped_fields',
        mapped_fields_table: 'mapped_fields',
        mapping_feedback_table: 'mapping_feedback',
        transformation_library_table: 'transformation_library',
        server_hostname: 'Acuity-oz-test-ue1.cloud.databricks.com',
        http_path: '/sql/1.0/warehouses/173ea239ed13be7d'
      },
      ai_model: {
        previous_mappings_table_name: 'mapped_fields',
        foundation_model_endpoint: 'databricks-meta-llama-3-3-70b-instruct',
        default_prompt: ''
      },
      ui: {
        app_title: 'Smart Mapper',
        theme_color: '#4a5568',
        sidebar_expanded: true
      },
      support: {
        support_url: 'https://mygainwell.sharepoint.com'
      },
      vector_search: {
        semantic_fields_index: 'oztest_dev.smartmapper.semantic_fields_vs',
        mapped_fields_index: 'oztest_dev.smartmapper.mapped_fields_vs',
        endpoint_name: 'smartmapper_vs_endpoint'
      },
      security: {
        admin_group_name: 'gia-oztest-dev-ue1-data-engineers',
        enable_password_auth: true,
        admin_password_hash: ''
      }
    }
    console.log('Configuration reset to defaults')
    loading.value.reset = false
  }, 1000)
}

onMounted(() => {
  loadConfiguration()
})
</script>

<style scoped>
.config-view {
  padding: 0;
  max-width: 100%;
  margin: 0;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-primary);
}

.auth-required {
  margin: 2rem 0;
}

.config-section {
  padding: 1.5rem;
}

.config-section h3 {
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-primary);
}

.config-section p {
  margin: 0 0 1.5rem 0;
  color: var(--gainwell-text-secondary);
}

.table-config-note {
  margin-bottom: 1.5rem;
}

.table-config-note code {
  background: var(--surface-100);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.connection-help {
  margin-bottom: 2rem;
}

.help-content h4 {
  margin: 1rem 0 0.5rem 0;
  color: var(--gainwell-primary);
}

.help-content code {
  background: var(--gainwell-bg-light);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-group {
  display: flex;
  gap: 1rem;
  align-items: end;
}

.flex-1 { flex: 1; }
.flex-3 { flex: 3; }

.field label {
  font-weight: 600;
  color: var(--gainwell-text-primary);
}

.field small {
  color: var(--gainwell-text-secondary);
  font-size: 0.875rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

/* Tab header icons - consistent styling */
:deep(.p-tabview-nav-link) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

:deep(.p-tabview-nav-link i) {
  color: var(--text-color);
  font-size: 1rem;
}

:deep(.p-tabview-nav-link.p-highlight i) {
  color: var(--gainwell-primary);
}

.tab-label {
  font-weight: 500;
}

/* Accordion header icons */
:deep(.p-accordion-header-link) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

:deep(.p-accordion-header-link i.pi-info-circle) {
  color: var(--text-color-secondary);
  font-size: 1rem;
}

.accordion-label {
  font-weight: 500;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.action-card {
  text-align: center;
}

.current-config h4 {
  margin: 0 0 1rem 0;
  color: var(--gainwell-primary);
}

.config-json {
  background: var(--gainwell-bg-light);
  padding: 1rem;
  border-radius: 8px;
  font-family: monospace;
  font-size: 0.875rem;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}
</style>
