<template>
  <div class="mapping-view">
    <div class="page-header">
      <h1>
        <i class="pi pi-sitemap"></i>
        Source-to-Target Field Mapping
      </h1>
      <p>Map source database fields to target database fields using AI-powered semantic matching</p>
    </div>

    <!-- Main Content Tabs matching original app structure -->
    <TabView>
      <!-- Unmapped Fields Tab (Main view from original) -->
      <TabPanel header="📋 Unmapped Fields">
        <div class="table-controls">
          <div class="search-controls">
            <IconField iconPosition="left">
              <InputIcon class="pi pi-search" />
              <InputText
                v-model="unmappedSearch"
                placeholder="Search by table name, column name, physical name, datatype, nullable status, or description..."
                @input="searchUnmappedFields"
              />
            </IconField>
            <Button 
              icon="pi pi-trash" 
              label="Clear Search"
              @click="clearUnmappedSearch"
              severity="secondary"
            />
          </div>
          <div class="action-controls">
            <Button 
              icon="pi pi-upload" 
              label="Upload Template"
              @click="showTemplateUpload = true"
              severity="info"
            />
            <Button 
              icon="pi pi-download" 
              label="Download Template"
              @click="downloadTemplate"
              severity="success"
              outlined
            />
          </div>
        </div>

        <DataTable 
          :value="filteredUnmappedFields" 
          :loading="loading.unmapped"
          paginator 
          :rows="10"
          :rowsPerPageOptions="[5, 10, 20, 50]"
          tableStyle="min-width: 50rem"
          rowHover
          class="p-datatable-sm"
          selectionMode="single"
          v-model:selection="selectedUnmappedField"
          @rowSelect="onUnmappedFieldSelect"
        >
          <Column field="src_table_name" header="Source Table" sortable>
            <template #body="{ data }">
              <strong>{{ data.src_table_name }}</strong>
            </template>
          </Column>
          
          <Column field="src_column_name" header="Source Column" sortable>
            <template #body="{ data }">
              <strong>{{ data.src_column_name }}</strong>
            </template>
          </Column>
          
          <Column field="src_column_physical_name" header="Physical Name" sortable />
          
          <Column field="src_nullable" header="Nullable" sortable>
            <template #body="{ data }">
              <Tag :value="data.src_nullable" :severity="data.src_nullable === 'YES' ? 'success' : 'danger'" />
            </template>
          </Column>
          
          <Column field="src_physical_datatype" header="Data Type" sortable>
            <template #body="{ data }">
              <Tag :value="data.src_physical_datatype" />
            </template>
          </Column>
          
          <Column field="src_comments" header="Description">
            <template #body="{ data }">
              <div class="description-text">
                {{ data.src_comments || 'No description' }}
              </div>
            </template>
          </Column>
        </DataTable>

        <!-- Field Detail View (when row is selected) -->
        <div v-if="selectedUnmappedField" class="field-detail-section">
          <Card class="field-detail-card">
            <template #title>
              <div class="detail-header">
                <h3>{{ selectedUnmappedField.src_table_name }}.{{ selectedUnmappedField.src_column_name }}</h3>
                <Button 
                  icon="pi pi-times" 
                  @click="clearSelection"
                  severity="secondary"
                  size="small"
                  text
                />
              </div>
            </template>
            
            <template #content>
              <div class="field-metadata">
                <div class="metadata-grid">
                  <div class="metadata-item">
                    <label>Physical Name:</label>
                    <span>{{ selectedUnmappedField.src_column_physical_name }}</span>
                  </div>
                  <div class="metadata-item">
                    <label>Data Type:</label>
                    <Tag :value="selectedUnmappedField.src_physical_datatype" />
                  </div>
                  <div class="metadata-item">
                    <label>Nullable:</label>
                    <Tag :value="selectedUnmappedField.src_nullable" :severity="selectedUnmappedField.src_nullable === 'YES' ? 'success' : 'danger'" />
                  </div>
                  <div class="metadata-item full-width">
                    <label>Description:</label>
                    <span>{{ selectedUnmappedField.src_comments || 'No description available' }}</span>
                  </div>
                </div>
              </div>

              <!-- AI Mapping Section -->
              <div class="ai-mapping-section">
                <div class="section-header">
                  <h4>🤖 AI Mapping Suggestions</h4>
                  <div class="ai-controls">
                    <Button 
                      icon="pi pi-magic-wand" 
                      label="Generate AI Suggestions"
                      @click="generateAISuggestions"
                      :loading="loading.aiSuggestions"
                      severity="primary"
                    />
                  </div>
                </div>

                <!-- AI Configuration -->
                <div class="ai-config">
                  <div class="config-row">
                    <div class="config-item">
                      <label>Vector Results:</label>
                      <InputNumber v-model="aiConfig.numVectorResults" :min="1" :max="100" />
                    </div>
                    <div class="config-item">
                      <label>AI Results:</label>
                      <InputNumber v-model="aiConfig.numAiResults" :min="1" :max="20" />
                    </div>
                  </div>
                  <div class="config-row">
                    <div class="config-item full-width">
                      <label>User Feedback (optional):</label>
                      <Textarea 
                        v-model="aiConfig.userFeedback" 
                        rows="2" 
                        placeholder="Provide additional context or constraints for AI mapping..."
                      />
                    </div>
                  </div>
                </div>

                <!-- AI Results -->
                <div v-if="aiSuggestions.length > 0" class="ai-results">
                  <DataTable 
                    :value="aiSuggestions"
                    tableStyle="min-width: 50rem"
                    rowHover
                    class="p-datatable-sm"
                  >
                    <Column field="target_table" header="Target Table" />
                    <Column field="target_column" header="Target Column" />
                    <Column field="reasoning" header="AI Reasoning">
                      <template #body="{ data }">
                        <div class="reasoning-text">
                          {{ data.reasoning }}
                        </div>
                      </template>
                    </Column>
                    <Column header="Actions">
                      <template #body="{ data }">
                        <Button 
                          icon="pi pi-check" 
                          label="Select"
                          @click="selectAIMapping(data)"
                          severity="success"
                          size="small"
                        />
                      </template>
                    </Column>
                  </DataTable>
                </div>
              </div>

              <!-- Manual Search Section -->
              <div class="manual-search-section">
                <div class="section-header">
                  <h4>🔍 Manual Search</h4>
                </div>
                
                <div class="search-controls">
                  <IconField iconPosition="left">
                    <InputIcon class="pi pi-search" />
                    <InputText
                      v-model="manualSearchTerm"
                      placeholder="Search by table name, column name, or description..."
                    />
                  </IconField>
                  <Button 
                    icon="pi pi-search" 
                    label="Search Semantic Table"
                    @click="searchSemanticTable"
                    :loading="loading.manualSearch"
                    severity="info"
                  />
                </div>

                <!-- Manual Search Results -->
                <div v-if="manualSearchResults.length > 0" class="manual-results">
                  <DataTable 
                    :value="manualSearchResults"
                    tableStyle="min-width: 50rem"
                    rowHover
                    class="p-datatable-sm"
                    selectionMode="single"
                    v-model:selection="selectedManualResult"
                  >
                    <Column field="tgt_table_name" header="Target Table" />
                    <Column field="tgt_column_name" header="Target Column" />
                    <Column field="tgt_physical_datatype" header="Data Type">
                      <template #body="{ data }">
                        <Tag :value="data.tgt_physical_datatype" />
                      </template>
                    </Column>
                    <Column field="tgt_nullable" header="Nullable">
                      <template #body="{ data }">
                        <Tag :value="data.tgt_nullable" :severity="data.tgt_nullable === 'YES' ? 'success' : 'danger'" />
                      </template>
                    </Column>
                    <Column field="tgt_comments" header="Description">
                      <template #body="{ data }">
                        <div class="description-text">
                          {{ data.tgt_comments || 'No description' }}
                        </div>
                      </template>
                    </Column>
                    <Column header="Actions">
                      <template #body="{ data }">
                        <Button 
                          icon="pi pi-check" 
                          label="Select"
                          @click="selectManualMapping(data)"
                          severity="success"
                          size="small"
                        />
                      </template>
                    </Column>
                  </DataTable>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </TabPanel>

      <!-- Mapped Fields Tab -->
      <TabPanel header="✅ Mapped Fields">
        <div class="table-controls">
          <div class="search-controls">
            <IconField iconPosition="left">
              <InputIcon class="pi pi-search" />
              <InputText
                v-model="mappedSearch"
                placeholder="Search mapped fields..."
                @input="searchMappedFields"
              />
            </IconField>
            <Button 
              icon="pi pi-refresh" 
              @click="loadMappedFields"
              :loading="loading.mapped"
              severity="secondary"
            />
          </div>
        </div>

        <DataTable 
          :value="filteredMappedFields" 
          :loading="loading.mapped"
          paginator 
          :rows="10"
          :rowsPerPageOptions="[5, 10, 20, 50]"
          tableStyle="min-width: 50rem"
          rowHover
          class="p-datatable-sm"
        >
          <Column field="src_table_name" header="Source Table" sortable />
          <Column field="src_column_name" header="Source Column" sortable />
          <Column header="→" style="width: 3rem; text-align: center;">
            <template #body>
              <i class="pi pi-arrow-right" style="color: var(--gainwell-secondary);"></i>
            </template>
          </Column>
          <Column field="tgt_table_name" header="Target Table" sortable />
          <Column field="tgt_column_physical" header="Target Column" sortable />
          <Column header="Actions">
            <template #body="{ data }">
              <Button 
                icon="pi pi-trash" 
                @click="unmapField(data)"
                severity="danger"
                size="small"
                v-tooltip="'Remove Mapping'"
              />
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Semantic Table Management Tab (Admin Only) -->
      <TabPanel header="🗂️ Semantic Table" v-if="userStore.isAdmin">
        <div class="semantic-management">
          <div class="table-controls">
            <div class="search-controls">
              <IconField iconPosition="left">
                <InputIcon class="pi pi-search" />
                <InputText
                  v-model="semanticSearch"
                  placeholder="Search by table, column, or description..."
                  @input="searchSemanticTable"
                />
              </IconField>
              <Button 
                icon="pi pi-refresh" 
                @click="loadSemanticTable"
                :loading="loading.semantic"
                severity="secondary"
              />
            </div>
            <div class="action-controls">
              <Button 
                icon="pi pi-upload" 
                label="Bulk Add from CSV"
                disabled
                severity="primary"
                v-tooltip="'Coming soon: Upload CSV to bulk add semantic records'"
              />
            </div>
          </div>

          <DataTable 
            :value="filteredSemanticRecords" 
            :loading="loading.semantic"
            paginator 
            :rows="10"
            :rowsPerPageOptions="[5, 10, 20, 50]"
            tableStyle="min-width: 50rem"
            rowHover
            class="p-datatable-sm"
          >
            <Column field="tgt_table_name" header="Target Table" sortable />
            <Column field="tgt_column_name" header="Target Column" sortable />
            <Column field="tgt_physical_datatype" header="Data Type" sortable>
              <template #body="{ data }">
                <Tag :value="data.tgt_physical_datatype" />
              </template>
            </Column>
            <Column field="tgt_nullable" header="Nullable" sortable>
              <template #body="{ data }">
                <Tag :value="data.tgt_nullable" :severity="data.tgt_nullable === 'YES' ? 'success' : 'danger'" />
              </template>
            </Column>
            <Column field="tgt_comments" header="Description">
              <template #body="{ data }">
                <div class="description-text">
                  {{ data.tgt_comments || 'No description' }}
                </div>
              </template>
            </Column>
            <Column field="semantic_field" header="Semantic Field">
              <template #body="{ data }">
                <div class="semantic-text">
                  {{ data.semantic_field }}
                </div>
              </template>
            </Column>
            <Column header="Actions">
              <template #body="{ data }">
                <div class="action-buttons">
                  <Button 
                    icon="pi pi-pencil" 
                    @click="editSemanticRecord(data)"
                    severity="info"
                    size="small"
                    v-tooltip="'Edit'"
                  />
                  <Button 
                    icon="pi pi-trash" 
                    @click="deleteSemanticRecord(data)"
                    severity="danger"
                    size="small"
                    v-tooltip="'Delete'"
                  />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </TabPanel>
    </TabView>

    <!-- Template Upload Dialog -->
    <Dialog 
      v-model:visible="showTemplateUpload" 
      modal 
      header="Upload Mapping Template"
      :style="{ width: '55rem' }"
    >
      <div class="upload-section">
        <p><strong>Instructions:</strong></p>
        <ol>
          <li>Click "Download Template" button below to get a CSV template with the correct format</li>
          <li>Add rows with your source field information:
            <ul style="margin-top: 0.5rem;">
              <li><strong>src_table_name</strong> - Source table name</li>
              <li><strong>src_column_name</strong> - Source column name</li>
              <li><strong>src_column_physical_name</strong> - Physical column name</li>
              <li><strong>src_nullable</strong> - YES or NO</li>
              <li><strong>src_physical_datatype</strong> - Data type (e.g., STRING, INT, DECIMAL)</li>
              <li><strong>src_comments</strong> - Description of the column</li>
            </ul>
          </li>
          <li>Save the CSV and upload it here</li>
          <li>Fields will appear in the <strong>Unmapped Fields</strong> tab and can be mapped later</li>
        </ol>
        
        <div style="margin-top: 1.5rem;">
          <FileUpload 
            ref="fileUploadRef"
            mode="basic" 
            accept=".csv"
            :maxFileSize="10000000"
            :customUpload="true"
            @uploader="handleFileUpload"
            :auto="true"
            chooseLabel="Select CSV File to Upload"
            :disabled="loading.uploadingTemplate"
          />
          <div v-if="loading.uploadingTemplate" style="margin-top: 1rem; display: flex; align-items: center; gap: 0.5rem; color: var(--gainwell-primary);">
            <i class="pi pi-spin pi-spinner"></i>
            <span>Uploading and processing mappings...</span>
          </div>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="closeUploadDialog" 
          severity="secondary"
          :disabled="loading.uploadingTemplate"
        />
      </template>
    </Dialog>

    <!-- Edit Semantic Record Dialog -->
    <Dialog 
      v-model:visible="showEditSemantic" 
      modal 
      header="Edit Semantic Record"
      :style="{ width: '50rem' }"
    >
      <div class="semantic-form" v-if="editingSemanticRecord">
        <div class="field">
          <label for="edit_tgt_table_name">Target Table Name *</label>
          <InputText 
            id="edit_tgt_table_name"
            v-model="editingSemanticRecord.tgt_table_name"
            class="w-full"
          />
        </div>
        
        <div class="field">
          <label for="edit_tgt_table_physical_name">Target Table Physical Name</label>
          <InputText 
            id="edit_tgt_table_physical_name"
            v-model="editingSemanticRecord.tgt_table_physical_name"
            class="w-full"
          />
        </div>
        
        <div class="field">
          <label for="edit_tgt_column_name">Target Column Name *</label>
          <InputText 
            id="edit_tgt_column_name"
            v-model="editingSemanticRecord.tgt_column_name"
            class="w-full"
          />
        </div>
        
        <div class="field">
          <label for="edit_tgt_column_physical_name">Target Column Physical Name</label>
          <InputText 
            id="edit_tgt_column_physical_name"
            v-model="editingSemanticRecord.tgt_column_physical_name"
            class="w-full"
          />
        </div>
        
        <div class="field">
          <label for="edit_tgt_physical_datatype">Data Type *</label>
          <InputText 
            id="edit_tgt_physical_datatype"
            v-model="editingSemanticRecord.tgt_physical_datatype"
            class="w-full"
          />
        </div>
        
        <div class="field">
          <label for="edit_tgt_nullable">Nullable *</label>
          <Dropdown 
            id="edit_tgt_nullable"
            v-model="editingSemanticRecord.tgt_nullable"
            :options="['YES', 'NO', 'Null', 'Not Null']"
            class="w-full"
          />
        </div>
        
        <div class="field">
          <label for="edit_tgt_comments">Description</label>
          <Textarea 
            id="edit_tgt_comments"
            v-model="editingSemanticRecord.tgt_comments"
            rows="3"
            class="w-full"
          />
        </div>
        
        <div class="help-text">
          <small>* Required fields. The semantic field will be automatically regenerated.</small>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="cancelEditSemantic" 
          severity="secondary"
          :disabled="loading.savingSemantic"
        />
        <Button 
          label="Save Changes" 
          icon="pi pi-check" 
          @click="saveSemanticRecord" 
          severity="primary"
          :loading="loading.savingSemantic"
        />
      </template>
    </Dialog>

    <!-- Add Semantic Record Dialog -->
    <Dialog 
      v-model:visible="showAddSemantic" 
      modal 
      header="Add Semantic Record"
      :style="{ width: '50rem' }"
    >
      <div class="semantic-form">
        <div class="field">
          <label for="tgt_table_name">Target Table Name *</label>
          <InputText 
            id="tgt_table_name"
            v-model="newSemanticRecord.tgt_table_name"
            class="w-full"
            placeholder="e.g., unified_member"
          />
        </div>
        
        <div class="field">
          <label for="tgt_table_physical_name">Target Table Physical Name</label>
          <InputText 
            id="tgt_table_physical_name"
            v-model="newSemanticRecord.tgt_table_physical_name"
            class="w-full"
            placeholder="Optional - defaults to table name"
          />
        </div>
        
        <div class="field">
          <label for="tgt_column_name">Target Column Name *</label>
          <InputText 
            id="tgt_column_name"
            v-model="newSemanticRecord.tgt_column_name"
            class="w-full"
            placeholder="e.g., member_id"
          />
        </div>
        
        <div class="field">
          <label for="tgt_column_physical_name">Target Column Physical Name</label>
          <InputText 
            id="tgt_column_physical_name"
            v-model="newSemanticRecord.tgt_column_physical_name"
            class="w-full"
            placeholder="Optional - defaults to column name"
          />
        </div>
        
        <div class="field">
          <label for="tgt_physical_datatype">Data Type *</label>
          <InputText 
            id="tgt_physical_datatype"
            v-model="newSemanticRecord.tgt_physical_datatype"
            class="w-full"
            placeholder="e.g., VARCHAR(50), INT, DECIMAL(10,2)"
          />
        </div>
        
        <div class="field">
          <label for="tgt_nullable">Nullable *</label>
          <Dropdown 
            id="tgt_nullable"
            v-model="newSemanticRecord.tgt_nullable"
            :options="['YES', 'NO', 'Null', 'Not Null']"
            class="w-full"
          />
        </div>
        
        <div class="field">
          <label for="tgt_comments">Description</label>
          <Textarea 
            id="tgt_comments"
            v-model="newSemanticRecord.tgt_comments"
            rows="3"
            class="w-full"
            placeholder="Description of this field (used in semantic search)"
          />
        </div>
        
        <div class="help-text">
          <small>* Required fields. The semantic field for vector search will be automatically generated.</small>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="cancelAddSemantic" 
          severity="secondary"
        />
        <Button 
          label="Add Record" 
          icon="pi pi-plus" 
          @click="addSemanticRecord" 
          severity="primary"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { SemanticAPI, type SemanticRecord, MappingAPI, type MappedField, type UnmappedField, AIMappingAPI, type AISuggestion } from '@/services/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// Reactive data matching original app structure
const unmappedFields = ref<UnmappedField[]>([])

// Mapped fields - loaded from API
const mappedFields = ref<MappedField[]>([])

// Semantic records - loaded from API
const semanticRecords = ref<SemanticRecord[]>([])

// Search terms
const unmappedSearch = ref('')
const mappedSearch = ref('')
const semanticSearch = ref('')
const manualSearchTerm = ref('')

// Selected items
const selectedUnmappedField = ref(null)
const selectedManualResult = ref(null)

// AI configuration
const aiConfig = ref({
  numVectorResults: 25,
  numAiResults: 10,
  userFeedback: ''
})

// AI and manual search results
const aiSuggestions = ref([])
const manualSearchResults = ref([])

// Dialog states
const showTemplateUpload = ref(false)
const showAddSemantic = ref(false)
const showEditSemantic = ref(false)

// Editing semantic record
const editingSemanticRecord = ref<SemanticRecord | null>(null)

// New semantic record form
const newSemanticRecord = ref({
  tgt_table_name: '',
  tgt_table_physical_name: '',
  tgt_column_name: '',
  tgt_column_physical_name: '',
  tgt_physical_datatype: '',
  tgt_nullable: 'NO',
  tgt_comments: ''
})

// Loading states
const loading = ref({
  unmapped: false,
  mapped: false,
  semantic: false,
  aiSuggestions: false,
  manualSearch: false,
  savingSemantic: false,
  uploadingTemplate: false
})

// Computed filtered data
const filteredUnmappedFields = computed(() => {
  if (!unmappedSearch.value) return unmappedFields.value
  const search = unmappedSearch.value.toLowerCase()
  return unmappedFields.value.filter(field => 
    field.src_table_name?.toLowerCase().includes(search) ||
    field.src_column_name?.toLowerCase().includes(search) ||
    field.src_column_physical_name?.toLowerCase().includes(search) ||
    field.src_physical_datatype?.toLowerCase().includes(search) ||
    field.src_nullable?.toLowerCase().includes(search) ||
    (field.src_comments && field.src_comments.toLowerCase().includes(search))
  )
})

const filteredMappedFields = computed(() => {
  if (!mappedSearch.value) return mappedFields.value
  const search = mappedSearch.value.toLowerCase()
  return mappedFields.value.filter(field => 
    field.src_table_name?.toLowerCase().includes(search) ||
    field.src_column_name?.toLowerCase().includes(search) ||
    (field.tgt_table_name && field.tgt_table_name.toLowerCase().includes(search)) ||
    (field.tgt_column_physical && field.tgt_column_physical.toLowerCase().includes(search))
  )
})

const filteredSemanticRecords = computed(() => {
  if (!semanticSearch.value) return semanticRecords.value
  const search = semanticSearch.value.toLowerCase()
  return semanticRecords.value.filter(record => 
    record.tgt_table_name?.toLowerCase().includes(search) ||
    record.tgt_column_name?.toLowerCase().includes(search) ||
    record.tgt_physical_datatype?.toLowerCase().includes(search) ||
    (record.tgt_comments && record.tgt_comments.toLowerCase().includes(search)) ||
    (record.semantic_field && record.semantic_field.toLowerCase().includes(search))
  )
})

// Methods
const searchUnmappedFields = () => {
  console.log('Searching unmapped fields:', unmappedSearch.value)
}

const clearUnmappedSearch = () => {
  unmappedSearch.value = ''
}

const searchMappedFields = () => {
  console.log('Searching mapped fields:', mappedSearch.value)
}

const onUnmappedFieldSelect = (event: any) => {
  selectedUnmappedField.value = event.data
  // Clear previous results when selecting new field
  aiSuggestions.value = []
  manualSearchResults.value = []
}

const clearSelection = () => {
  selectedUnmappedField.value = null
  aiSuggestions.value = []
  manualSearchResults.value = []
}

const generateAISuggestions = async () => {
  if (!selectedUnmappedField.value) return
  
  loading.value.aiSuggestions = true
  
  try {
    console.log('Generating AI suggestions for:', selectedUnmappedField.value)
    
    const result = await AIMappingAPI.generateSuggestions(
      selectedUnmappedField.value.src_table_name,
      selectedUnmappedField.value.src_column_name,
      selectedUnmappedField.value.src_physical_datatype,
      selectedUnmappedField.value.src_nullable,
      selectedUnmappedField.value.src_comments || '',
      aiConfig.value.numVectorResults,
      aiConfig.value.numAiResults,
      aiConfig.value.userFeedback
    )
    
    if (result.error) {
      console.error('Error generating AI suggestions:', result.error)
      alert(`Failed to generate AI suggestions: ${result.error}`)
      aiSuggestions.value = []
    } else if (result.data) {
      console.log(`Generated ${result.data.length} AI suggestions with confidence scores`)
      aiSuggestions.value = result.data
    }
  } catch (error) {
    console.error('Error generating AI suggestions:', error)
    alert('Failed to generate AI suggestions. Please try again.')
    aiSuggestions.value = []
  } finally {
    loading.value.aiSuggestions = false
  }
}

const selectAIMapping = (mapping: any) => {
  console.log('Selected AI mapping:', mapping)
  // Move from unmapped to mapped
  const newMapping = {
    src_table_name: selectedUnmappedField.value.src_table_name,
    src_column_name: selectedUnmappedField.value.src_column_name,
    tgt_table_name: mapping.target_table,
    tgt_column_physical: mapping.target_column
  }
  mappedFields.value.push(newMapping)
  
  // Remove from unmapped
  const index = unmappedFields.value.findIndex(f => 
    f.src_table_name === selectedUnmappedField.value.src_table_name &&
    f.src_column_name === selectedUnmappedField.value.src_column_name
  )
  if (index > -1) {
    unmappedFields.value.splice(index, 1)
  }
  
  clearSelection()
}

const searchSemanticTable = async () => {
  if (!manualSearchTerm.value.trim()) {
    return
  }
  
  loading.value.manualSearch = true
  
  try {
    const result = await MappingAPI.searchSemanticTable(manualSearchTerm.value.trim())
    if (result.data) {
      manualSearchResults.value = result.data
      console.log(`Found ${result.data.length} manual search results`)
    } else if (result.error) {
      console.error('Error searching semantic table:', result.error)
    }
  } catch (error) {
    console.error('Error searching semantic table:', error)
  } finally {
    loading.value.manualSearch = false
  }
}

const selectManualMapping = async (mapping: any) => {
  if (!selectedUnmappedField.value) {
    console.error('No unmapped field selected')
    return
  }
  
  console.log('Saving manual mapping:', mapping)
  loading.value.manualSearch = true
  
  try {
    const result = await MappingAPI.saveManualMapping(
      selectedUnmappedField.value.src_table_name,
      selectedUnmappedField.value.src_column_name,
      mapping.tgt_table_name,
      mapping.tgt_column_name,
      mapping.tgt_table_physical_name || mapping.tgt_table_name,
      mapping.tgt_column_physical_name || mapping.tgt_column_name
    )
    
    if (result.error) {
      console.error('Error saving manual mapping:', result.error)
    } else {
      console.log('Manual mapping saved successfully')
      // Refresh both tables
      await Promise.all([loadUnmappedFields(), loadMappedFields()])
      // Clear search results and selection
      manualSearchResults.value = []
      manualSearchTerm.value = ''
      clearSelection()
    }
  } catch (error) {
    console.error('Error saving manual mapping:', error)
  } finally {
    loading.value.manualSearch = false
  }
}

const loadUnmappedFields = async () => {
  loading.value.unmapped = true
  try {
    const result = await MappingAPI.getUnmappedFields()
    if (result.data) {
      unmappedFields.value = result.data
      console.log(`Loaded ${result.data.length} unmapped fields`)
    } else if (result.error) {
      console.error('Error loading unmapped fields:', result.error)
    }
  } catch (error) {
    console.error('Error loading unmapped fields:', error)
  } finally {
    loading.value.unmapped = false
  }
}

const loadMappedFields = async () => {
  loading.value.mapped = true
  try {
    const result = await MappingAPI.getMappedFields()
    if (result.data) {
      mappedFields.value = result.data
      console.log(`Loaded ${result.data.length} mapped fields`)
    } else if (result.error) {
      console.error('Error loading mapped fields:', result.error)
    }
  } catch (error) {
    console.error('Error loading mapped fields:', error)
  } finally {
    loading.value.mapped = false
  }
}

const unmapField = async (field: any) => {
  // Confirm before deleting
  const confirmed = confirm(
    `Are you sure you want to remove the mapping for ${field.src_table_name}.${field.src_column_name}?\n\n` +
    `This will remove the target mapping: ${field.tgt_table_name}.${field.tgt_column_physical}`
  )
  
  if (!confirmed) {
    return
  }
  
  console.log('Unmapping field:', field)
  loading.value.mapped = true
  
  try {
    const result = await MappingAPI.unmapField(field.src_table_name, field.src_column_name)
    
    if (result.error) {
      console.error('Error unmapping field:', result.error)
      alert(`Failed to remove mapping: ${result.error}`)
    } else {
      console.log('Unmap successful:', result.data)
      
      // Refresh both tables to reflect the change
      console.log('Refreshing unmapped and mapped fields...')
      await Promise.all([
        loadUnmappedFields(),
        loadMappedFields()
      ])
      console.log('Data refreshed successfully')
    }
  } catch (error) {
    console.error('Error unmapping field:', error)
    alert('Failed to remove mapping. Please try again.')
  } finally {
    loading.value.mapped = false
  }
}

const loadSemanticTable = async () => {
  loading.value.semantic = true
  try {
    const result = await SemanticAPI.getAllRecords()
    if (result.data) {
      semanticRecords.value = result.data
      console.log(`Loaded ${result.data.length} semantic records`)
    } else if (result.error) {
      console.error('Error loading semantic records:', result.error)
    }
  } catch (error) {
    console.error('Error loading semantic records:', error)
  } finally {
    loading.value.semantic = false
  }
}

const addSemanticRecord = async () => {
  // Validate required fields
  if (!newSemanticRecord.value.tgt_table_name || 
      !newSemanticRecord.value.tgt_column_name || 
      !newSemanticRecord.value.tgt_physical_datatype) {
    console.error('Missing required fields')
    return
  }
  
  // If physical names are empty, default to logical names
  if (!newSemanticRecord.value.tgt_table_physical_name) {
    newSemanticRecord.value.tgt_table_physical_name = newSemanticRecord.value.tgt_table_name
  }
  if (!newSemanticRecord.value.tgt_column_physical_name) {
    newSemanticRecord.value.tgt_column_physical_name = newSemanticRecord.value.tgt_column_name
  }
  
  try {
    const result = await SemanticAPI.createRecord(newSemanticRecord.value)
    if (result.data) {
      semanticRecords.value.push(result.data)
      console.log('Successfully added semantic record')
      cancelAddSemantic()
    } else if (result.error) {
      console.error('Error adding semantic record:', result.error)
    }
  } catch (error) {
    console.error('Error adding semantic record:', error)
  }
}

const cancelAddSemantic = () => {
  showAddSemantic.value = false
  newSemanticRecord.value = {
    tgt_table_name: '',
    tgt_table_physical_name: '',
    tgt_column_name: '',
    tgt_column_physical_name: '',
    tgt_physical_datatype: '',
    tgt_nullable: 'NO',
    tgt_comments: ''
  }
}

const editSemanticRecord = (record: SemanticRecord) => {
  // Clone the record for editing
  editingSemanticRecord.value = { ...record }
  showEditSemantic.value = true
}

const cancelEditSemantic = () => {
  showEditSemantic.value = false
  editingSemanticRecord.value = null
}

const saveSemanticRecord = async () => {
  if (!editingSemanticRecord.value || !editingSemanticRecord.value.id) {
    console.error('No record to save')
    return
  }
  
  // Validate required fields
  if (!editingSemanticRecord.value.tgt_table_name || 
      !editingSemanticRecord.value.tgt_column_name || 
      !editingSemanticRecord.value.tgt_physical_datatype) {
    console.error('Missing required fields')
    return
  }
  
  loading.value.savingSemantic = true
  
  try {
    const updateData = {
      tgt_table_name: editingSemanticRecord.value.tgt_table_name,
      tgt_table_physical_name: editingSemanticRecord.value.tgt_table_physical_name,
      tgt_column_name: editingSemanticRecord.value.tgt_column_name,
      tgt_column_physical_name: editingSemanticRecord.value.tgt_column_physical_name,
      tgt_nullable: editingSemanticRecord.value.tgt_nullable,
      tgt_physical_datatype: editingSemanticRecord.value.tgt_physical_datatype,
      tgt_comments: editingSemanticRecord.value.tgt_comments
    }
    
    const result = await SemanticAPI.updateRecord(editingSemanticRecord.value.id, updateData)
    if (result.data) {
      // Update the record in the local array
      const index = semanticRecords.value.findIndex(r => r.id === editingSemanticRecord.value!.id)
      if (index > -1) {
        semanticRecords.value[index] = result.data
      }
      console.log('Successfully updated semantic record')
      cancelEditSemantic()
    } else if (result.error) {
      console.error('Error updating semantic record:', result.error)
    }
  } catch (error) {
    console.error('Error updating semantic record:', error)
  } finally {
    loading.value.savingSemantic = false
  }
}

const deleteSemanticRecord = async (record: any) => {
  if (!record.id) {
    console.error('Record has no ID')
    return
  }
  
  // Confirm deletion
  if (!confirm(`Are you sure you want to delete ${record.tgt_table_name}.${record.tgt_column_name}?`)) {
    return
  }
  
  try {
    const result = await SemanticAPI.deleteRecord(record.id)
    if (result.data) {
      // Remove from local array
      const index = semanticRecords.value.findIndex(r => r.id === record.id)
      if (index > -1) {
        semanticRecords.value.splice(index, 1)
      }
      console.log('Successfully deleted semantic record')
    } else if (result.error) {
      console.error('Error deleting semantic record:', result.error)
    }
  } catch (error) {
    console.error('Error deleting semantic record:', error)
  }
}

const downloadTemplate = async () => {
  console.log('Download template')
  loading.value.unmapped = true
  
  try {
    const blob = await MappingAPI.downloadTemplate()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'unmapped_fields_template.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    console.log('Template downloaded successfully')
  } catch (error) {
    console.error('Error downloading template:', error)
    alert('Failed to download template. Please try again.')
  } finally {
    loading.value.unmapped = false
  }
}

const handleFileUpload = async (event: any) => {
  console.log('Upload template:', event)
  
  // Get the file from the event
  const file = event.files[0]
  if (!file) {
    console.error('No file selected')
    return
  }
  
  loading.value.uploadingTemplate = true
  
  try {
    console.log('Uploading file:', file.name)
    const result = await MappingAPI.uploadTemplate(file)
    
    if (result.error) {
      console.error('Upload error:', result.error)
      alert(`Upload failed: ${result.error}`)
    } else {
      console.log('Upload successful:', result.data)
      const details = result.data.details
      let message = `Upload complete!\n\n`
      message += `✓ ${details.successful} new mappings inserted\n`
      if (details.skipped > 0) {
        message += `⊘ ${details.skipped} duplicates skipped\n`
      }
      if (details.failed > 0) {
        message += `✗ ${details.failed} failed\n`
      }
      alert(message)
      
      // Refresh the data - very important!
      console.log('Refreshing unmapped and mapped fields...')
      await Promise.all([
        loadUnmappedFields(),
        loadMappedFields()
      ])
      console.log('Data refreshed successfully')
      
      showTemplateUpload.value = false
    }
  } catch (error) {
    console.error('Error uploading template:', error)
    alert('Failed to upload template. Please check the file format and try again.')
  } finally {
    loading.value.uploadingTemplate = false
  }
}

const closeUploadDialog = () => {
  showTemplateUpload.value = false
}

onMounted(() => {
  console.log('Source-to-Target Mapping view loaded')
  // Load data from the database
  loadUnmappedFields()
  loadMappedFields()
  loadSemanticTable()
})
</script>

<style scoped>
.mapping-view {
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

/* Table Controls */
.table-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--gainwell-bg-light);
  border-radius: 8px;
  flex-wrap: wrap;
  gap: 1rem;
}

.search-controls, .action-controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

/* Field Detail Section */
.field-detail-section {
  margin-top: 2rem;
}

.field-detail-card {
  background: var(--gainwell-bg-primary);
  border: 1px solid var(--gainwell-border);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-header h3 {
  margin: 0;
  color: var(--gainwell-primary);
}

.field-metadata {
  margin-bottom: 2rem;
}

.metadata-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metadata-item.full-width {
  grid-column: 1 / -1;
}

.metadata-item label {
  font-weight: 600;
  color: var(--gainwell-text-primary);
  font-size: 0.9rem;
}

/* AI Mapping Section */
.ai-mapping-section, .manual-search-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: var(--gainwell-bg-light);
  border-radius: 8px;
  border: 1px solid var(--gainwell-border);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h4 {
  margin: 0;
  color: var(--gainwell-primary);
}

.ai-config {
  margin-bottom: 1.5rem;
}

.config-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  align-items: end;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-item.full-width {
  flex: 1;
}

.config-item label {
  font-weight: 600;
  color: var(--gainwell-text-primary);
  font-size: 0.9rem;
}

/* Results styling */
.description-text, .reasoning-text, .semantic-text {
  max-width: 300px;
  white-space: normal;
  word-wrap: break-word;
  font-size: 0.875rem;
  color: var(--gainwell-text-secondary);
  line-height: 1.4;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

/* Dialog styling */
.upload-section ul {
  margin: 1rem 0;
  padding-left: 1.5rem;
}

.upload-section li {
  margin-bottom: 0.5rem;
}

.semantic-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.semantic-form .field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.semantic-form label {
  font-weight: 600;
  color: var(--gainwell-text-primary);
}

/* Semantic Management */
.semantic-management {
  /* Additional styling for semantic table management */
}
</style>
