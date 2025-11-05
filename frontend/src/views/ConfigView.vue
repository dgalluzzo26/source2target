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
      <TabPanel header="🗄️ Database">
        <div class="config-section">
          <h3>Database Configuration</h3>
          <p>Configure database connections and table references.</p>

          <!-- Connection Help -->
          <Accordion class="connection-help">
            <AccordionTab header="ℹ️ How to find connection details">
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
              <label for="mapping_table">Mapping Table</label>
              <InputText 
                id="mapping_table"
                v-model="config.database.mapping_table"
                placeholder="catalog.schema.mappings"
                class="w-full"
              />
              <small>Full table name for storing field mappings</small>
            </div>

            <div class="field">
              <label for="semantic_table">Semantic Table</label>
              <InputText 
                id="semantic_table"
                v-model="config.database.semantic_table"
                placeholder="catalog.schema.semantic_table"
                class="w-full"
              />
              <small>Full table name for semantic search data</small>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- AI/ML Models Tab -->
      <TabPanel header="🤖 AI/ML Models">
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
                placeholder="catalog.schema.train_with_comments"
                class="w-full"
              />
              <small>Table containing historical mappings for training context</small>
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
      <TabPanel header="🔍 Vector Search">
        <div class="config-section">
          <h3>Vector Search Configuration</h3>
          <p>Configure vector search index for semantic field matching.</p>

          <div class="config-form">
            <div class="field">
              <label for="vector_index_name">Vector Search Index Name</label>
              <InputText 
                id="vector_index_name"
                v-model="config.vector_search.index_name"
                placeholder="catalog.schema.vector_search_index"
                class="w-full"
              />
              <small>Name of the Databricks Vector Search index</small>
            </div>

            <div class="field-group">
              <div class="field flex-3">
                <label for="vector_endpoint_name">Vector Search Endpoint</label>
                <InputText 
                  id="vector_endpoint_name"
                  v-model="config.vector_search.endpoint_name"
                  placeholder="s2t_vsendpoint"
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
      <TabPanel header="🎨 UI Settings">
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
      <TabPanel header="🤝 Support">
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
      <TabPanel header="🔐 Security">
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
      <TabPanel header="🛠️ Actions">
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
const config = ref({
  database: {
    warehouse_name: 'gia-oztest-dev-data-warehouse',
    mapping_table: 'oztest_dev.source_to_target.mappings',
    semantic_table: 'oztest_dev.source_to_target.silver_semantic_full',
    server_hostname: 'Acuity-oz-test-ue1.cloud.databricks.com',
    http_path: '/sql/1.0/warehouses/173ea239ed13be7d'
  },
  ai_model: {
    previous_mappings_table_name: 'oztest_dev.source_to_target.train_with_comments',
    foundation_model_endpoint: 'databricks-meta-llama-3-3-70b-instruct',
    default_prompt: `You are a ETL engineer and your job is to take in information on an incoming field from a source database and map it to an existing target table in your database.{feedback_section}{previous_section}

The incoming field can be described by its table name, column name, natural language desription, whether or not it is nullable, and its datatype. The same information from semantically similar fields in your target database table field are provided in this prompt, and it is likely that one of these provided columns is the correct match for mapping. As an additional hint, each target field may contain source fields that have been previously mapped to that target field. The semantically similar target fields (and their corresponding previous source field mappings) can be found in this structure:

{retrieved_context_structure}

If no previous data has been mapped to the target_table_field, you will see an [NaN]. Here is the information about the target table and its columns:

{retrieved_context}

Here is the source field you want to map to one of those target columns: {query_text}{no_mapping_guidance}

Please return your top {num_results} guesses for the correct target column mapping, in order. IMPORTANT: Your suggestions must comply with any constraints specified above. Do not include any mappings that violate the user requirements or include excluded columns. Format your response in a json format with a "results" key containing array of the results (i.e. 
\`\`\`{results_structure}\`\`\`
). The "reasoning" field should contain a brief description of why you think this mapping is correct and confirm it meets the specified constraints. You can include references to previously mapped columns or semantic or datatype similiarities.`
  },
  ui: {
    app_title: 'Source-to-Target Mapping Platform',
    theme_color: '#4a5568',
    sidebar_expanded: true
  },
  support: {
    support_url: 'https://mygainwell.sharepoint.com'
  },
  vector_search: {
    index_name: 'oztest_dev.source_to_target.silver_semantic_full_vs',
    endpoint_name: 's2t_vsendpoint'
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
    // Reset to default values
    config.value = {
      database: {
        warehouse_name: 'gia-oztest-dev-data-warehouse',
        mapping_table: 'oztest_dev.source_to_target.mappings',
        semantic_table: 'oztest_dev.source_to_target.silver_semantic_full',
        server_hostname: 'Acuity-oz-test-ue1.cloud.databricks.com',
        http_path: '/sql/1.0/warehouses/173ea239ed13be7d'
      },
      ai_model: {
        previous_mappings_table_name: 'oztest_dev.source_to_target.train_with_comments',
        foundation_model_endpoint: 'databricks-meta-llama-3-3-70b-instruct',
        default_prompt: config.value.ai_model.default_prompt
      },
      ui: {
        app_title: 'Source-to-Target Mapping Platform',
        theme_color: '#4a5568',
        sidebar_expanded: true
      },
      support: {
        support_url: 'https://mygainwell.sharepoint.com'
      },
      vector_search: {
        index_name: 'oztest_dev.source_to_target.silver_semantic_full_vs',
        endpoint_name: 's2t_vsendpoint'
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
