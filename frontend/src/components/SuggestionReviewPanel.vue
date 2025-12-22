<template>
  <div class="suggestion-review-panel">
    <!-- Summary Bar -->
    <div class="summary-bar">
      <div class="summary-stats">
        <div class="summary-stat">
          <span class="stat-num">{{ suggestions.length }}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="summary-stat pending">
          <span class="stat-num">{{ pendingCount }}</span>
          <span class="stat-label">Pending</span>
        </div>
        <div class="summary-stat approved">
          <span class="stat-num">{{ approvedCount }}</span>
          <span class="stat-label">Approved</span>
        </div>
        <div class="summary-stat rejected">
          <span class="stat-num">{{ noMatchCount }}</span>
          <span class="stat-label">No Match</span>
        </div>
      </div>
      <div class="summary-actions">
        <Button 
          icon="pi pi-refresh"
          size="small"
          severity="secondary"
          @click="loadSuggestions"
          :loading="loading"
          v-tooltip.top="'Refresh'"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && suggestions.length === 0" class="loading-container">
      <ProgressSpinner />
      <p>Loading suggestions...</p>
    </div>

    <!-- Suggestions List -->
    <div v-else class="suggestions-list">
      <div 
        v-for="suggestion in suggestions" 
        :key="suggestion.suggestion_id"
        class="suggestion-card"
        :class="{ 
          'approved': suggestion.suggestion_status === 'APPROVED' || suggestion.suggestion_status === 'EDITED',
          'rejected': suggestion.suggestion_status === 'REJECTED',
          'skipped': suggestion.suggestion_status === 'SKIPPED',
          'no-match': suggestion.suggestion_status === 'NO_MATCH' || suggestion.suggestion_status === 'NO_PATTERN'
        }"
      >
        <div class="suggestion-header">
          <div class="column-info">
            <i class="pi pi-arrow-circle-right"></i>
            <div class="column-names">
              <strong>{{ suggestion.tgt_column_name }}</strong>
              <span class="physical">{{ suggestion.tgt_column_physical_name }}</span>
            </div>
          </div>
          <div class="suggestion-meta">
            <Tag 
              :value="formatStatus(suggestion.suggestion_status)" 
              :severity="getStatusSeverity(suggestion.suggestion_status)"
              size="small"
            />
            <div v-if="suggestion.confidence_score" class="confidence-badge" :class="getConfidenceClass(suggestion.confidence_score)">
              {{ (suggestion.confidence_score * 100).toFixed(0) }}%
            </div>
          </div>
        </div>

        <div class="suggestion-description" v-if="suggestion.tgt_comments">
          {{ suggestion.tgt_comments }}
        </div>

        <!-- Pattern Info -->
        <div v-if="suggestion.pattern_type" class="pattern-info">
          <Tag :value="suggestion.pattern_type" severity="secondary" size="small" />
          <span class="pattern-label">{{ suggestion.pattern_description || 'Pattern from historical mapping' }}</span>
          <Button 
            v-if="suggestion.alternative_patterns_count > 0"
            :label="`${suggestion.alternative_patterns_count} alternative${suggestion.alternative_patterns_count > 1 ? 's' : ''}`"
            icon="pi pi-clone"
            size="small"
            text
            severity="info"
            @click="showAlternatives(suggestion)"
            v-tooltip.top="'View alternative pattern types'"
          />
        </div>

        <!-- Matched Source Fields -->
        <div v-if="getMatchedFields(suggestion).length > 0" class="matched-sources">
          <h4>Matched Source Fields:</h4>
          <div class="source-tags">
            <Tag 
              v-for="(field, idx) in getMatchedFields(suggestion).slice(0, 3)" 
              :key="idx"
              :value="`${field.src_table_physical_name}.${field.src_column_physical_name}`"
              severity="info"
              size="small"
            />
            <Badge 
              v-if="getMatchedFields(suggestion).length > 3"
              :value="`+${getMatchedFields(suggestion).length - 3}`"
              severity="secondary"
            />
          </div>
        </div>

        <!-- SQL Preview -->
        <div v-if="suggestion.suggested_sql" class="sql-preview">
          <div class="sql-header">
            <h4>SQL Expression:</h4>
            <Button 
              icon="pi pi-copy"
              text
              size="small"
              @click="copySQL(suggestion.suggested_sql)"
              v-tooltip.top="'Copy SQL'"
            />
          </div>
          <pre class="sql-code">{{ suggestion.suggested_sql }}</pre>
        </div>

        <!-- No Match Message -->
        <div v-if="suggestion.suggestion_status === 'NO_MATCH'" class="no-match-message">
          <i class="pi pi-exclamation-triangle"></i>
          <span>No matching source fields found. Manual mapping may be required.</span>
        </div>

        <!-- No Pattern Message -->
        <div v-if="suggestion.suggestion_status === 'NO_PATTERN'" class="no-pattern-message">
          <i class="pi pi-info-circle"></i>
          <span>No historical pattern found for this column. This will be the first mapping.</span>
        </div>

        <!-- Warnings -->
        <div v-if="getWarnings(suggestion).length > 0" class="warnings">
          <div v-for="(warning, idx) in getWarnings(suggestion)" :key="idx" class="warning-item">
            <i class="pi pi-exclamation-circle"></i>
            {{ warning }}
          </div>
        </div>

        <!-- Actions -->
        <div class="suggestion-actions" v-if="suggestion.suggestion_status === 'PENDING'">
          <!-- Has issues: Must review/edit first, no direct approve -->
          <template v-if="hasWarningsOrIssues(suggestion)">
            <Button 
              label="Review & Edit"
              icon="pi pi-pencil"
              size="small"
              severity="warning"
              @click="openEditDialog(suggestion)"
            />
          </template>
          <!-- Clean: Can approve directly or edit -->
          <template v-else>
          <Button 
            label="Approve"
            icon="pi pi-check"
            size="small"
            severity="success"
            @click="handleApprove(suggestion)"
          />
          <Button 
              label="Edit"
            icon="pi pi-pencil"
            size="small"
            severity="info"
            outlined
            @click="openEditDialog(suggestion)"
          />
          </template>
          <Button 
            label="Reject"
            icon="pi pi-times"
            size="small"
            severity="danger"
            outlined
            @click="openRejectDialog(suggestion)"
          />
          <Button 
            icon="pi pi-refresh"
            size="small"
            severity="secondary"
            text
            :loading="regeneratingId === suggestion.suggestion_id"
            @click="handleRegenerate(suggestion)"
            v-tooltip.top="'Regenerate this suggestion'"
          />
          <Button 
            label="Skip"
            icon="pi pi-forward"
            size="small"
            severity="secondary"
            text
            @click="handleSkip(suggestion)"
          />
        </div>

        <!-- Manual Mapping Action for No Match -->
        <div class="suggestion-actions" v-if="suggestion.suggestion_status === 'NO_MATCH' || suggestion.suggestion_status === 'NO_PATTERN'">
          <Button 
            label="Regenerate"
            icon="pi pi-refresh"
            size="small"
            severity="info"
            :loading="regeneratingId === suggestion.suggestion_id"
            @click="handleRegenerate(suggestion)"
            v-tooltip.top="'Re-run AI discovery for this column'"
          />
          <Button 
            label="Create Manual Mapping"
            icon="pi pi-plus"
            size="small"
            severity="secondary"
            outlined
            @click="$emit('manual-mapping', suggestion)"
          />
          <Button 
            label="Skip"
            icon="pi pi-forward"
            size="small"
            severity="secondary"
            text
            @click="handleSkip(suggestion)"
          />
        </div>

        <!-- Reviewed Info -->
        <div v-if="suggestion.reviewed_by" class="reviewed-info">
          <i class="pi pi-user"></i>
          Reviewed by {{ suggestion.reviewed_by }} on {{ formatDate(suggestion.reviewed_ts) }}
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="suggestions.length === 0 && !loading" class="empty-state">
        <i class="pi pi-check-circle" style="font-size: 3rem; color: var(--green-500);"></i>
        <h3>All Caught Up!</h3>
        <p>No suggestions to review for this table.</p>
      </div>
    </div>

    <!-- Enhanced Edit Dialog -->
    <Dialog 
      v-model:visible="showEditDialog" 
      modal 
      header="Edit Mapping" 
      :style="{ width: '95vw', maxWidth: '1400px' }"
      maximizable
    >
      <div v-if="editingSuggestion" class="edit-dialog-content">
        <!-- Target Info Header -->
        <div class="edit-header">
          <div class="target-info">
            <Tag value="TARGET" severity="info" />
            <strong>{{ editingSuggestion.tgt_table_name }}.{{ editingSuggestion.tgt_column_name }}</strong>
            <span class="datatype">({{ editingSuggestion.tgt_physical_datatype || 'STRING' }})</span>
          </div>
          <div class="target-description" v-if="editingSuggestion.tgt_comments">
            {{ editingSuggestion.tgt_comments }}
          </div>
        </div>

        <!-- Three Column Layout -->
        <div class="edit-columns-v2">
          <!-- Left: Collapsible Source & Changes Panel -->
          <div class="left-panel" :class="{ 'collapsed': leftPanelCollapsed }">
            <div class="panel-toggle" @click="leftPanelCollapsed = !leftPanelCollapsed">
              <i :class="leftPanelCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-left'"></i>
              <span v-if="!leftPanelCollapsed">Sources & Notes</span>
            </div>
            
            <div v-if="!leftPanelCollapsed" class="left-panel-content">
              <!-- AI Changes Section - Collapsible -->
              <div v-if="getChanges(editingSuggestion).length > 0 || getWarnings(editingSuggestion).length > 0" class="changes-section">
                <div class="section-header" @click="aiChangesCollapsed = !aiChangesCollapsed">
                  <i :class="aiChangesCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-down'"></i>
                  <h4><i class="pi pi-lightbulb"></i> AI Changes</h4>
                  <Badge 
                    :value="getChanges(editingSuggestion).length + getWarnings(editingSuggestion).length" 
                    :severity="getWarnings(editingSuggestion).length > 0 ? 'warning' : 'info'"
                  />
                </div>
                <div v-if="!aiChangesCollapsed" class="change-list">
                  <div 
                    v-for="(change, idx) in getChanges(editingSuggestion)" 
                    :key="'c'+idx"
                    class="change-item"
                    :class="{ 'is-problem': isProblemChange(change) }"
                    @click="highlightInSQL(change)"
                  >
                    <i :class="getChangeIcon(change)"></i>
                    <div class="change-detail">
                      <span class="change-original">{{ change.original }}</span>
                      <i class="pi pi-arrow-right"></i>
                      <span class="change-new">{{ change.new || change.replacement || '?' }}</span>
                    </div>
                  </div>
                  <div 
                    v-for="(warning, idx) in getWarnings(editingSuggestion)" 
                    :key="'w'+idx"
                    class="change-item is-warning"
                    @click="highlightWarningField(warning)"
                  >
                    <i class="pi pi-exclamation-triangle"></i>
                    <span>{{ warning }}</span>
                  </div>
                </div>
              </div>

              <!-- Source Fields Section -->
              <div class="source-section">
                <h4><i class="pi pi-table"></i> Source Fields</h4>
                <InputText 
                  v-model="sourceFilter" 
                  placeholder="Filter..." 
                  size="small"
                  class="source-filter"
                />
                
                <div class="source-tables">
                  <div v-for="table in groupedSourceFields" :key="table.tableName" class="source-table-group">
                    <div class="table-header" @click="toggleTableExpand(table.tableName)">
                      <i :class="expandedTables.includes(table.tableName) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
                      <strong>{{ table.tableName }}</strong>
                      <Badge :value="table.columns.length" severity="secondary" />
                    </div>
                    <div v-if="expandedTables.includes(table.tableName)" class="table-columns">
                      <div 
                        v-for="col in filteredColumns(table.columns)" 
                        :key="col.unmapped_field_id"
                        class="column-item"
                        :class="{ 'matched': isMatchedColumn(col) }"
                        @click="insertColumnToSQL(col)"
                        v-tooltip.right="col.src_comments || 'Click to insert'"
                      >
                        <span class="col-name">{{ col.src_column_physical_name }}</span>
                        <span class="col-type">{{ col.src_physical_datatype || 'STRING' }}</span>
                        <i v-if="isMatchedColumn(col)" class="pi pi-check matched-icon"></i>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: SQL Editor (takes remaining space) -->
          <div class="sql-panel-v2">
            <!-- SQL Editor Header -->
            <div class="sql-header">
              <label><i class="pi pi-code"></i> SQL Expression</label>
              <div class="sql-actions">
                <Button 
                  label="AI Assist" 
                  icon="pi pi-bolt" 
                  size="small"
                  severity="help"
                  @click="showAIAssist = true"
                  v-tooltip.top="'Get AI help with this expression'"
                  class="ai-assist-btn"
                />
                <Button 
                  icon="pi pi-copy" 
                  size="small"
                  severity="secondary"
                  outlined
                  @click="copySQL(editedSQL)"
                  v-tooltip.top="'Copy SQL'"
                />
              </div>
            </div>

            <!-- SQL Preview with Syntax Highlighting - Collapsible -->
            <div class="sql-preview-highlighted" :class="{ 'has-problems': problemFieldsInSQL.length > 0, 'collapsed': sqlPreviewCollapsed }">
              <div 
                class="preview-label clickable" 
                :class="{ 'warning': problemFieldsInSQL.length > 0, 'info': problemFieldsInSQL.length === 0 }"
                @click="sqlPreviewCollapsed = !sqlPreviewCollapsed"
              >
                <i :class="sqlPreviewCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-down'" class="toggle-icon"></i>
                <i :class="problemFieldsInSQL.length > 0 ? 'pi pi-exclamation-circle' : 'pi pi-eye'"></i>
                <span v-if="problemFieldsInSQL.length > 0">
                  {{ problemFieldsInSQL.length }} field(s) need attention
                </span>
                <span v-else-if="getChanges(editingSuggestion).length > 0">
                  Preview ({{ getChanges(editingSuggestion).length }} AI changes)
                </span>
                <span v-else>SQL Preview</span>
              </div>
              <pre v-if="!sqlPreviewCollapsed" class="sql-highlighted" v-html="highlightedSQL"></pre>
            </div>

            <!-- Editable SQL -->
            <div class="sql-editor-container">
          <Textarea 
                ref="sqlTextarea"
            v-model="editedSQL" 
                :rows="18"
                class="sql-editor-v2 w-full"
            placeholder="Enter the SQL expression..."
                spellcheck="false"
          />
        </div>

            <!-- Matched Source Summary (compact) -->
            <div class="matched-summary-compact" v-if="getMatchedFields(editingSuggestion).length > 0">
              <span class="matched-label"><i class="pi pi-check-circle"></i> Matched:</span>
              <div class="matched-tags">
                <Tag 
                  v-for="field in getMatchedFields(editingSuggestion).slice(0, 5)" 
                  :key="field.unmapped_field_id"
                  :value="`${field.src_column_physical_name}`"
                  severity="success"
                  size="small"
                />
                <Badge 
                  v-if="getMatchedFields(editingSuggestion).length > 5"
                  :value="`+${getMatchedFields(editingSuggestion).length - 5}`"
                  severity="secondary"
                />
              </div>
            </div>

            <!-- Edit Notes (compact) -->
            <div class="notes-row">
          <InputText 
            v-model="editNotes" 
            class="w-full"
                placeholder="Notes (optional): Explain your changes..."
          />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showEditDialog = false" severity="secondary" />
        <Button label="Save & Approve" icon="pi pi-check" @click="handleEditApprove" :loading="saving" severity="success" />
      </template>
    </Dialog>

    <!-- AI Assist Dialog -->
    <Dialog 
      v-model:visible="showAIAssist" 
      modal 
      header="AI SQL Assistant" 
      :style="{ width: '600px' }"
    >
      <div class="ai-assist-content">
        <p>Describe what you need help with:</p>
        <Textarea 
          v-model="aiPrompt" 
          :rows="3"
          class="w-full"
          placeholder="e.g., Join recipient_master to member table on SAK_RECIP..."
        />
      </div>
      <template #footer>
        <Button label="Cancel" @click="showAIAssist = false" severity="secondary" />
        <Button label="Generate SQL" icon="pi pi-bolt" @click="handleAIAssist" :loading="aiGenerating" />
      </template>
    </Dialog>

    <!-- Reject Dialog -->
    <Dialog 
      v-model:visible="showRejectDialog" 
      modal 
      header="Reject Suggestion" 
      :style="{ width: '500px' }"
    >
      <div class="reject-dialog-content">
        <p>Why is this suggestion being rejected? This feedback helps improve future AI suggestions.</p>
        <Textarea 
          v-model="rejectReason" 
          :rows="4"
          class="w-full"
          placeholder="e.g., Wrong source table, incorrect transformation, missing join condition..."
        />
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showRejectDialog = false" severity="secondary" />
        <Button label="Reject" icon="pi pi-times" @click="handleReject" severity="danger" :loading="saving" :disabled="!rejectReason" />
      </template>
    </Dialog>

    <!-- Pattern Alternatives Dialog -->
    <Dialog 
      v-model:visible="showAlternativesDialog" 
      modal 
      header="Pattern Alternatives" 
      :style="{ width: '700px' }"
    >
      <div v-if="loadingAlternatives" class="loading-alternatives">
        <ProgressSpinner />
        <p>Loading alternatives...</p>
      </div>
      
      <div v-else class="alternatives-content">
        <p class="alternatives-intro">
          Multiple teams have mapped <strong>{{ alternativesSuggestion?.tgt_column_physical_name }}</strong> differently.
          Choose the pattern that best fits your source data.
        </p>
        
        <div 
          v-for="variant in patternVariants" 
          :key="variant.signature"
          class="variant-card"
          :class="{ 'is-current': variant.is_current }"
        >
          <div class="variant-header">
            <Tag :value="variant.description.split(' + ')[0]" />
            <span class="variant-transforms">
              {{ variant.description.includes(' + ') ? variant.description.split(' + ').slice(1).join(' + ') : '' }}
            </span>
            <Badge :value="variant.usage_count" severity="info" v-tooltip.top="'Times used'" />
            <Tag v-if="variant.is_current" value="Current" severity="success" size="small" />
          </div>
          
          <div class="variant-meta">
            <span><i class="pi pi-calendar"></i> Last used: {{ formatDate(variant.latest_mapped_ts) }}</span>
            <span><i class="pi pi-user"></i> {{ variant.latest_pattern.created_by || 'Unknown' }}</span>
          </div>
          
          <div class="variant-sql-preview">
            <code>{{ truncateSql(variant.latest_pattern.source_expression, 120) }}</code>
          </div>
          
          <Button 
            :label="variant.is_current ? 'Currently Selected' : 'Use This Pattern'"
            :icon="variant.is_current ? 'pi pi-check' : 'pi pi-arrow-right'"
            size="small"
            :disabled="variant.is_current"
            :severity="variant.is_current ? 'success' : 'info'"
            @click="useAlternativePattern(variant)"
            :loading="regeneratingWithPattern === variant.latest_pattern.mapped_field_id"
          />
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useProjectsStore, type MappingSuggestion, type MatchedSourceField } from '@/stores/projectsStore'
import { useUserStore } from '@/stores/user'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import ProgressSpinner from 'primevue/progressspinner'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import InputText from 'primevue/inputtext'

const props = defineProps<{
  projectId: number
  tableId: number
  tableName: string
}>()

const emit = defineEmits(['suggestion-updated', 'manual-mapping'])

const toast = useToast()
const projectsStore = useProjectsStore()
const userStore = useUserStore()

// State
const showEditDialog = ref(false)
const showRejectDialog = ref(false)
const showAIAssist = ref(false)
const showAlternativesDialog = ref(false)
const editingSuggestion = ref<MappingSuggestion | null>(null)
const rejectingSuggestion = ref<MappingSuggestion | null>(null)
const alternativesSuggestion = ref<MappingSuggestion | null>(null)
const patternVariants = ref<any[]>([])
const loadingAlternatives = ref(false)
const regeneratingWithPattern = ref<number | null>(null)
const editedSQL = ref('')
const editNotes = ref('')
const rejectReason = ref('')
const saving = ref(false)
const aiGenerating = ref(false)
const aiPrompt = ref('')
const sourceFilter = ref('')
const expandedTables = ref<string[]>([])
const sourceFields = ref<any[]>([])
const regeneratingId = ref<number | null>(null)
const leftPanelCollapsed = ref(false)
const aiChangesCollapsed = ref(false)
const sqlPreviewCollapsed = ref(false)
const sqlTextarea = ref<any>(null)

// Computed
const suggestions = computed(() => projectsStore.suggestions)
const loading = computed(() => projectsStore.loading)

const pendingCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'PENDING').length
)
const approvedCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'APPROVED' || s.suggestion_status === 'EDITED').length
)
const noMatchCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'NO_MATCH' || s.suggestion_status === 'NO_PATTERN').length
)

// Problem fields from AI warnings that need user attention
// NOTE: We only highlight fields from WARNINGS (missing/not found), 
// NOT from successful changes (those are already fixed)
const problemFieldsInSQL = computed(() => {
  if (!editingSuggestion.value) return []
  
  const warnings = getWarnings(editingSuggestion.value)
  const problems: string[] = []
  
  // Extract field names from warnings about missing/unknown fields
  for (const warning of warnings) {
    // Common warning patterns we need to match:
    // - "Column CURR_REC_IND was found in multiple tables..."
    // - "Column ADDR_USAGE was used for filtering..."
    // - "No matching source column found for CDE_COUNTY"
    // - "Column 'XYZ' not found"
    // - "Missing: ABC_FIELD"
    
    // Match "Column FIELD_NAME was..." or "Column FIELD_NAME is..."
    const columnMatch = warning.match(/Column\s+([A-Z][A-Z0-9_]+)\s+(?:was|is|has)/i)
    if (columnMatch) {
      problems.push(columnMatch[1])
    }
    
    // Match field names in quotes
    const quotedMatches = warning.match(/['"`]([A-Za-z_][A-Za-z0-9_]*)['"`]/g)
    if (quotedMatches) {
      problems.push(...quotedMatches.map((m: string) => m.replace(/['"`]/g, '')))
    }
    
    // Match "for FIELD_NAME" or "found for FIELD_NAME" 
    const forMatch = warning.match(/for\s+([A-Z][A-Z0-9_]+)/i)
    if (forMatch) {
      problems.push(forMatch[1])
    }
    
    // Match "Missing: FIELD_NAME" or "Missing FIELD_NAME"
    const missingMatch = warning.match(/missing[:\s]+([A-Z][A-Z0-9_]+)/i)
    if (missingMatch) {
      problems.push(missingMatch[1])
    }
    
    // Match any ALL_CAPS_FIELD_NAME that looks like a column (fallback)
    const allCapsMatches = warning.match(/\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b/g)
    if (allCapsMatches) {
      problems.push(...allCapsMatches)
    }
  }
  
  // Filter out SQL keywords
  const sqlKeywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'AND', 'OR', 'ON', 'AS', 'IN', 'NOT', 'NULL',
                       'LEFT', 'RIGHT', 'INNER', 'OUTER', 'UNION', 'DISTINCT', 'GROUP', 'BY', 'ORDER',
                       'HAVING', 'LIMIT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'TRIM', 'INITCAP', 'CONCAT']
  
  // Extract silver table aliases from the SQL (tables with "silver" in the path)
  // Matches patterns like: FROM silver.xxx AS alias, JOIN silver.xxx alias, silver.xxx.yyy mf
  const sql = editedSQL.value || editingSuggestion.value?.suggested_sql || ''
  const silverAliases = new Set<string>()
  
  // Match: silver.anything AS/followed by alias (1-3 chars typically)
  const silverPatterns = [
    /silver[._][^\s]+\s+(?:AS\s+)?(\w{1,4})\b/gi,  // silver.table AS mf or silver.table mf
    /FROM\s+(\w+)\.[^.]+\.(\w+)\s+(?:AS\s+)?(\w{1,4})\b/gi  // FROM catalog.silver.table mf
  ]
  
  for (const pattern of silverPatterns) {
    let match
    while ((match = pattern.exec(sql)) !== null) {
      // Check if "silver" appears before the alias
      const fullMatch = match[0].toLowerCase()
      if (fullMatch.includes('silver')) {
        const alias = match[match.length - 1] || match[1]
        if (alias && alias.length <= 4) {
          silverAliases.add(alias.toLowerCase())
        }
      }
    }
  }
  
  // Also check for direct "silver" in table references
  const directSilverMatch = sql.match(/\bsilver\.\w+/gi)
  if (directSilverMatch) {
    // Mark 'mf' as silver alias if we see silver.mbr_fndtn or similar
    silverAliases.add('mf')
  }
  
  const filtered = problems.filter(p => {
    const upper = p.toUpperCase()
    const lower = p.toLowerCase()
    
    // Exclude SQL keywords
    if (sqlKeywords.includes(upper)) return false
    
    // Exclude if this looks like an alias.column from a silver table
    // Check if any warning mentions this column with a silver table alias
    for (const alias of silverAliases) {
      // If the SQL contains alias.COLUMN_NAME, exclude this column
      const aliasPattern = new RegExp(`\\b${alias}\\.${p}\\b`, 'i')
      if (aliasPattern.test(sql)) {
        return false
      }
    }
    
    return true
  })
  
  return [...new Set(filtered)] // unique values
})

// Highlighted SQL with syntax highlighting and problem fields marked
const highlightedSQL = computed(() => {
  if (!editedSQL.value) {
    return ''
  }
  
  let html = escapeHtml(editedSQL.value)
  
  // First, highlight problem fields (from warnings) in yellow
  if (problemFieldsInSQL.value.length > 0) {
    const sortedProblems = [...problemFieldsInSQL.value].sort((a, b) => b.length - a.length)
    
    for (const field of sortedProblems) {
      const regex = new RegExp(`\\b(${escapeRegExp(field)})\\b`, 'gi')
      html = html.replace(regex, '<mark class="problem-field">$1</mark>')
    }
  }
  
  // Highlight SQL keywords for readability
  const keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 
                    'ON', 'AND', 'OR', 'AS', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 
                    'ELSE', 'END', 'TRIM', 'CONCAT', 'COALESCE', 'NULL', 'IS', 'NOT',
                    'DISTINCT', 'INITCAP', 'IN', 'LIKE', 'BETWEEN', 'GROUP', 'BY', 
                    'ORDER', 'HAVING', 'LIMIT', 'OFFSET']
  
  for (const kw of keywords) {
    const regex = new RegExp(`\\b(${kw})\\b`, 'gi')
    html = html.replace(regex, '<span class="sql-keyword">$1</span>')
  }
  
  // Highlight string literals
  html = html.replace(/('(?:[^'\\]|\\.)*')/g, '<span class="sql-string">$1</span>')
  
  // Highlight placeholders like ${USER_BRONZE_CATALOG}
  html = html.replace(/(\$\{[A-Z_]+\})/g, '<span class="sql-placeholder">$1</span>')
  
  // Highlight table aliases (single letters followed by .)
  html = html.replace(/\b([a-z])\.([A-Za-z_][A-Za-z0-9_]*)/g, '<span class="sql-alias">$1</span>.<span class="sql-column">$2</span>')
  
  return html
})

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Group source fields by table
const groupedSourceFields = computed(() => {
  const groups: { tableName: string; columns: any[] }[] = []
  const tableMap = new Map<string, any[]>()
  
  for (const field of sourceFields.value) {
    const tableName = field.src_table_physical_name || 'Unknown'
    if (!tableMap.has(tableName)) {
      tableMap.set(tableName, [])
    }
    tableMap.get(tableName)!.push(field)
  }
  
  tableMap.forEach((columns, tableName) => {
    groups.push({ tableName, columns })
  })
  
  return groups.sort((a, b) => a.tableName.localeCompare(b.tableName))
})

// Lifecycle
onMounted(() => {
  loadSuggestions()
})

watch(() => props.tableId, () => {
  loadSuggestions()
})

// Methods
async function loadSuggestions() {
  await projectsStore.fetchSuggestions(props.projectId, props.tableId)
}

function getMatchedFields(suggestion: MappingSuggestion): MatchedSourceField[] {
  return projectsStore.parseMatchedSourceFields(suggestion.matched_source_fields)
}

function getWarnings(suggestion: MappingSuggestion): string[] {
  if (!suggestion.warnings) return []
  try {
    return JSON.parse(suggestion.warnings)
  } catch {
    return []
  }
}

async function handleApprove(suggestion: MappingSuggestion) {
  try {
    await projectsStore.approveSuggestion(suggestion.suggestion_id, userStore.userEmail || 'unknown')
    toast.add({ severity: 'success', summary: 'Approved', detail: 'Mapping created', life: 2000 })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  }
}

function openEditDialog(suggestion: MappingSuggestion) {
  editingSuggestion.value = suggestion
  editedSQL.value = suggestion.suggested_sql || ''
  editNotes.value = ''
  sourceFilter.value = ''
  expandedTables.value = []
  showEditDialog.value = true
  
  // Load source fields for the project
  loadSourceFields()
}

async function loadSourceFields() {
  try {
    const response = await fetch(`/api/v4/projects/${props.projectId}/source-fields`)
    if (response.ok) {
      sourceFields.value = await response.json()
      // Auto-expand first table
      if (groupedSourceFields.value.length > 0) {
        expandedTables.value = [groupedSourceFields.value[0].tableName]
      }
    }
  } catch (e) {
    console.error('Error loading source fields:', e)
  }
}

function toggleTableExpand(tableName: string) {
  if (expandedTables.value.includes(tableName)) {
    expandedTables.value = expandedTables.value.filter(t => t !== tableName)
  } else {
    expandedTables.value.push(tableName)
  }
}

function filteredColumns(columns: any[]) {
  if (!sourceFilter.value) return columns
  const filter = sourceFilter.value.toLowerCase()
  return columns.filter(c => 
    c.src_column_physical_name?.toLowerCase().includes(filter) ||
    c.src_comments?.toLowerCase().includes(filter)
  )
}

function isMatchedColumn(col: any): boolean {
  if (!editingSuggestion.value) return false
  const matched = getMatchedFields(editingSuggestion.value)
  return matched.some(m => m.unmapped_field_id === col.unmapped_field_id)
}

function insertColumnToSQL(col: any) {
  const insertion = `${col.src_table_physical_name}.${col.src_column_physical_name}`
  editedSQL.value += (editedSQL.value ? ' ' : '') + insertion
}

function getChanges(suggestion: MappingSuggestion): any[] {
  if (!suggestion.sql_changes) return []
  try {
    return JSON.parse(suggestion.sql_changes)
  } catch {
    return []
  }
}

function formatChange(change: any): string {
  // Handle different change formats from LLM
  if (change.original && change.new) {
    return `${change.original} → ${change.new}`
  }
  if (change.original && change.replacement) {
    return `${change.original} → ${change.replacement}`
  }
  if (change.type && change.original) {
    return `${change.type}: ${change.original}`
  }
  if (change.description) {
    return change.description
  }
  return String(change)
}

function isProblemChange(change: any): boolean {
  // Determine if this change indicates a problem that needs fixing
  const newVal = change.new || change.replacement || ''
  // Problem if: no replacement provided, or replacement contains placeholder/unknown
  return !newVal || 
         newVal.includes('?') || 
         newVal.toLowerCase().includes('unknown') ||
         newVal.toLowerCase().includes('user_') ||
         change.type === 'missing' ||
         change.type === 'not_found'
}

function getChangeIcon(change: any): string {
  if (isProblemChange(change)) {
    return 'pi pi-exclamation-circle'
  }
  if (change.type === 'replaced' || change.new || change.replacement) {
    return 'pi pi-arrow-right-arrow-left'
  }
  return 'pi pi-info-circle'
}

function highlightInSQL(change: any) {
  if (!change.original || !sqlTextarea.value) return
  
  const sql = editedSQL.value
  const searchTerm = change.original
  const index = sql.toUpperCase().indexOf(searchTerm.toUpperCase())
  
  if (index >= 0) {
    // Select the text in the textarea
    const textarea = sqlTextarea.value.$el?.querySelector('textarea') || sqlTextarea.value
    if (textarea && textarea.setSelectionRange) {
      textarea.focus()
      textarea.setSelectionRange(index, index + searchTerm.length)
    }
  }
}

function highlightWarningField(warning: string) {
  if (!sqlTextarea.value) return
  
  // Extract field name from warning
  let searchTerm = ''
  
  // Try "for FIELD_NAME" pattern
  const forMatch = warning.match(/for\s+([A-Z][A-Z0-9_]+)/i)
  if (forMatch) {
    searchTerm = forMatch[1]
  }
  
  // Try quoted field name
  if (!searchTerm) {
    const quotedMatch = warning.match(/['"`]([A-Za-z_][A-Za-z0-9_]*)['"`]/)
    if (quotedMatch) {
      searchTerm = quotedMatch[1]
    }
  }
  
  if (!searchTerm) return
  
  const sql = editedSQL.value
  const index = sql.toUpperCase().indexOf(searchTerm.toUpperCase())
  
  if (index >= 0) {
    const textarea = sqlTextarea.value.$el?.querySelector('textarea') || sqlTextarea.value
    if (textarea && textarea.setSelectionRange) {
      textarea.focus()
      textarea.setSelectionRange(index, index + searchTerm.length)
    }
  }
}

function hasWarningsOrIssues(suggestion: MappingSuggestion): boolean {
  const warnings = getWarnings(suggestion)
  const confidence = suggestion.confidence_score || 0
  // Has issues if: warnings exist, low confidence, or no matched sources
  return warnings.length > 0 || confidence < 0.9 || !suggestion.matched_source_fields || suggestion.matched_source_fields === '[]'
}

async function handleAIAssist() {
  if (!aiPrompt.value) return
  
  aiGenerating.value = true
  try {
    // Get available column names for context
    const availableColumns = sourceFields.value.map(f => f.src_column_physical_name)
    
    const response = await fetch('/api/v4/suggestions/ai/assist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: aiPrompt.value,
        current_sql: editedSQL.value,
        target_column: editingSuggestion.value?.tgt_column_name,
        target_table: editingSuggestion.value?.tgt_table_name,
        available_columns: availableColumns
      })
    })
    
    if (response.ok) {
      const result = await response.json()
      if (result.success && result.sql) {
        editedSQL.value = result.sql
        toast.add({ 
          severity: 'success', 
          summary: 'SQL Updated', 
          detail: result.explanation || 'AI modified the SQL expression', 
          life: 3000 
        })
      } else {
        toast.add({ 
          severity: 'warn', 
          summary: 'AI Response', 
          detail: result.explanation || 'Could not modify SQL', 
          life: 4000 
        })
      }
    } else {
      const error = await response.json().catch(() => ({}))
      toast.add({ severity: 'error', summary: 'Error', detail: error.detail || 'Failed to call AI', life: 3000 })
    }
  } catch (e) {
    console.error('AI Assist error:', e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'AI service unavailable', life: 3000 })
  } finally {
    aiGenerating.value = false
    showAIAssist.value = false
    aiPrompt.value = ''
  }
}

async function handleEditApprove() {
  if (!editingSuggestion.value || !editedSQL.value) return
  
  saving.value = true
  try {
    await projectsStore.editAndApproveSuggestion(
      editingSuggestion.value.suggestion_id,
      userStore.userEmail || 'unknown',
      editedSQL.value,
      editNotes.value || undefined
    )
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Edited mapping created', life: 2000 })
    showEditDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    saving.value = false
  }
}

function openRejectDialog(suggestion: MappingSuggestion) {
  rejectingSuggestion.value = suggestion
  rejectReason.value = ''
  showRejectDialog.value = true
}

async function handleReject() {
  if (!rejectingSuggestion.value || !rejectReason.value) return
  
  saving.value = true
  try {
    await projectsStore.rejectSuggestion(
      rejectingSuggestion.value.suggestion_id,
      userStore.userEmail || 'unknown',
      rejectReason.value
    )
    toast.add({ severity: 'info', summary: 'Rejected', detail: 'Feedback recorded', life: 2000 })
    showRejectDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    saving.value = false
  }
}

async function handleSkip(suggestion: MappingSuggestion) {
  try {
    await projectsStore.skipSuggestion(suggestion.suggestion_id, userStore.userEmail || 'unknown')
    toast.add({ severity: 'info', summary: 'Skipped', detail: 'Column skipped', life: 2000 })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  }
}

async function handleRegenerate(suggestion: MappingSuggestion) {
  try {
    regeneratingId.value = suggestion.suggestion_id
    await projectsStore.regenerateSuggestion(suggestion.suggestion_id)
    toast.add({ 
      severity: 'success', 
      summary: 'Regenerated', 
      detail: `AI rediscovery complete for ${suggestion.tgt_column_physical_name}`, 
      life: 3000 
    })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Regeneration Failed', detail: e.message, life: 5000 })
  } finally {
    regeneratingId.value = null
  }
}

// Pattern Alternatives
async function showAlternatives(suggestion: MappingSuggestion) {
  alternativesSuggestion.value = suggestion
  showAlternativesDialog.value = true
  loadingAlternatives.value = true
  patternVariants.value = []
  
  try {
    const response = await fetch(`/api/v4/suggestions/${suggestion.suggestion_id}/alternatives`)
    if (!response.ok) throw new Error('Failed to load alternatives')
    const data = await response.json()
    patternVariants.value = data.variants || []
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
    showAlternativesDialog.value = false
  } finally {
    loadingAlternatives.value = false
  }
}

async function useAlternativePattern(variant: any) {
  if (!alternativesSuggestion.value) return
  
  const patternId = variant.latest_pattern.mapped_field_id
  regeneratingWithPattern.value = patternId
  
  try {
    await projectsStore.regenerateSuggestion(
      alternativesSuggestion.value.suggestion_id,
      patternId
    )
    
    toast.add({ 
      severity: 'success', 
      summary: 'Pattern Applied', 
      detail: `Using ${variant.description} pattern`, 
      life: 3000 
    })
    
    showAlternativesDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    regeneratingWithPattern.value = null
  }
}

function truncateSql(sql: string, maxLen: number): string {
  if (!sql) return ''
  return sql.length > maxLen ? sql.substring(0, maxLen) + '...' : sql
}

function copySQL(sql: string) {
  navigator.clipboard.writeText(sql)
  toast.add({ severity: 'info', summary: 'Copied', detail: 'SQL copied to clipboard', life: 2000 })
}

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ')
}

function getStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
  switch (status) {
    case 'APPROVED':
    case 'EDITED': return 'success'
    case 'PENDING': return 'warning'
    case 'REJECTED': return 'danger'
    case 'SKIPPED': return 'secondary'
    case 'NO_MATCH':
    case 'NO_PATTERN': return 'info'
    default: return 'secondary'
  }
}

function getConfidenceClass(score: number): string {
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.suggestion-review-panel {
  max-height: 70vh;
  overflow-y: auto;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  margin-bottom: 1rem;
  position: sticky;
  top: 0;
  z-index: 10;
}

.summary-stats {
  display: flex;
  gap: 2rem;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 1.5rem;
  font-weight: 600;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.summary-stat.pending .stat-num { color: var(--orange-500); }
.summary-stat.approved .stat-num { color: var(--green-500); }
.summary-stat.rejected .stat-num { color: var(--red-500); }

.summary-actions {
  display: flex;
  gap: 0.5rem;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 1rem;
}

/* Suggestions List */
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.suggestion-card {
  border: 1px solid var(--surface-border);
  border-radius: 10px;
  padding: 1.25rem;
  background: white;
  transition: all 0.2s;
}

.suggestion-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.suggestion-card.approved {
  border-left: 4px solid var(--green-500);
  background: #f1f8e9;
}

.suggestion-card.rejected {
  border-left: 4px solid var(--red-500);
  opacity: 0.7;
}

.suggestion-card.skipped {
  border-left: 4px solid var(--surface-400);
  opacity: 0.6;
}

.suggestion-card.no-match {
  border-left: 4px solid var(--orange-500);
  background: #fff8e1;
}

/* Card Header */
.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.column-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.column-info i {
  color: var(--gainwell-secondary);
  font-size: 1.25rem;
}

.column-names {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.column-names strong {
  color: var(--text-color);
}

.column-names .physical {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  font-family: monospace;
}

.suggestion-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.confidence-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.confidence-badge.high {
  background: #c8e6c9;
  color: #2e7d32;
}

.confidence-badge.medium {
  background: #ffe0b2;
  color: #e65100;
}

.confidence-badge.low {
  background: #ffcdd2;
  color: #c62828;
}

.suggestion-description {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

/* Pattern Info */
.pattern-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.pattern-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Matched Sources */
.matched-sources {
  margin-bottom: 0.75rem;
}

.matched-sources h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

/* SQL Preview */
.sql-preview {
  margin-bottom: 0.75rem;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sql-header h4 {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.sql-code {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.75rem;
  font-family: monospace;
  font-size: 0.85rem;
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 150px;
  overflow-y: auto;
}

/* Messages */
.no-match-message,
.no-pattern-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.no-match-message {
  background: #fff3e0;
  color: #e65100;
}

.no-pattern-message {
  background: #e3f2fd;
  color: #1565c0;
}

/* Warnings */
.warnings {
  margin-bottom: 0.75rem;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #fff3e0;
  color: #e65100;
  border-radius: 4px;
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}

/* Actions */
.suggestion-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
}

/* Reviewed Info */
.reviewed-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 0.75rem;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  color: var(--text-color);
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
}

/* Enhanced Edit Dialog */
.edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-header {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border-left: 4px solid var(--primary-color);
}

.target-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.target-info .datatype {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.target-description {
  margin-top: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

/* NEW: Three-column layout v2 */
.edit-columns-v2 {
  display: flex;
  gap: 1rem;
  min-height: 500px;
}

/* Left Panel - Collapsible */
.left-panel {
  width: 300px;
  min-width: 300px;
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  background: var(--surface-50);
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  overflow: hidden;
}

.left-panel.collapsed {
  width: 40px;
  min-width: 40px;
}

.panel-toggle {
  padding: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-border);
  font-weight: 500;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.panel-toggle:hover {
  background: var(--surface-200);
}

.left-panel.collapsed .panel-toggle {
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  padding: 1rem 0.5rem;
  height: 100%;
}

.left-panel-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* Changes Section */
.changes-section {
  border-bottom: 1px solid var(--surface-border);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  cursor: pointer;
  background: var(--surface-100);
  transition: background 0.15s;
}

.section-header:hover {
  background: var(--surface-200);
}

.section-header > i:first-child {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.section-header h4 {
  margin: 0;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary-color);
  flex: 1;
}

.changes-section h4 {
  margin: 0;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary-color);
}

.change-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.5rem 0.75rem 0.75rem;
}

.change-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid var(--surface-200);
}

.change-item:hover {
  background: var(--primary-50);
  border-color: var(--primary-200);
}

.change-item.is-problem {
  background: #fff3e0;
  border-color: var(--orange-200);
}

.change-item.is-problem i {
  color: var(--orange-500);
}

.change-item.is-warning {
  background: #fff8e1;
  border-color: var(--yellow-300);
}

.change-item.is-warning i {
  color: var(--yellow-700);
}

.change-item i {
  color: var(--primary-color);
  margin-top: 2px;
}

.change-detail {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.change-original {
  font-family: monospace;
  background: #ffcdd2;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  color: #c62828;
  text-decoration: line-through;
}

.change-detail .pi-arrow-right {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.change-new {
  font-family: monospace;
  background: #c8e6c9;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  color: #2e7d32;
}

/* Source Section */
.source-section {
  flex: 1;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.source-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.source-filter {
  width: 100%;
  margin-bottom: 0.5rem;
}

.source-tables {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: white;
}

.source-table-group {
  border-bottom: 1px solid var(--surface-100);
}

.source-table-group:last-child {
  border-bottom: none;
}

.table-header {
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: background 0.15s;
}

.table-header:hover {
  background: var(--surface-50);
}

.table-header i {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.table-header strong {
  flex: 1;
  font-size: 0.8rem;
}

.table-columns {
  padding: 0 0.25rem 0.25rem;
}

.column-item {
  padding: 0.35rem 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
  font-size: 0.8rem;
}

.column-item:hover {
  background: var(--primary-50);
}

.column-item.matched {
  background: var(--green-50);
  border-left: 3px solid var(--green-500);
}

.col-name {
  flex: 1;
  font-family: monospace;
  font-size: 0.8rem;
}

.col-type {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.matched-icon {
  color: var(--green-500);
  font-size: 0.75rem;
}

/* SQL Panel V2 */
.sql-panel-v2 {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sql-header label {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sql-actions {
  display: flex;
  gap: 0.35rem;
}

.ai-assist-btn {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: white !important;
  border: none !important;
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.3) !important;
}

.ai-assist-btn:hover {
  background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.4) !important;
}

:deep(.ai-assist-btn) {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: white !important;
  border: none !important;
}

:deep(.ai-assist-btn:hover) {
  background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
}

/* Highlighted SQL Preview */
.sql-preview-highlighted {
  border: 1px solid var(--surface-300);
  border-radius: 8px;
  background: var(--surface-50);
  overflow: hidden;
}

.sql-preview-highlighted.has-problems {
  border: 2px solid var(--orange-300);
  background: #fffbf5;
}

.preview-label {
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.preview-label.warning {
  background: var(--orange-100);
  color: var(--orange-700);
}

.preview-label.info {
  background: var(--blue-50);
  color: var(--blue-700);
}

.preview-label.clickable {
  cursor: pointer;
  transition: background 0.15s;
}

.preview-label.clickable:hover {
  filter: brightness(0.95);
}

.preview-label .toggle-icon {
  font-size: 0.7rem;
  margin-right: 0.25rem;
}

.sql-preview-highlighted.collapsed {
  border-radius: 8px;
}

.sql-highlighted {
  padding: 0.75rem;
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 150px;
  overflow-y: auto;
  background: white;
}

.sql-highlighted :deep(.problem-field) {
  background: #ffeb3b;
  color: #c62828;
  padding: 0.1rem 0.25rem;
  border-radius: 3px;
  font-weight: 600;
  border: 1px solid #ff9800;
  animation: pulse-highlight 2s infinite;
}

@keyframes pulse-highlight {
  0%, 100% { background: #ffeb3b; }
  50% { background: #ffc107; }
}

.sql-highlighted :deep(.sql-keyword) {
  color: #1565c0;
  font-weight: 600;
}

.sql-highlighted :deep(.sql-string) {
  color: #2e7d32;
}

.sql-highlighted :deep(.sql-placeholder) {
  color: #7b1fa2;
  font-weight: 500;
  background: #f3e5f5;
  padding: 0.1rem 0.2rem;
  border-radius: 3px;
}

.sql-highlighted :deep(.sql-alias) {
  color: #0097a7;
  font-weight: 500;
}

.sql-highlighted :deep(.sql-column) {
  color: #455a64;
}

/* SQL Editor Container */
.sql-editor-container {
  flex: 1;
  min-height: 300px;
}

.sql-editor-v2 {
  font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
  font-size: 0.9rem;
  background: #1e1e1e !important;
  color: #d4d4d4 !important;
  border-radius: 8px;
  height: 100%;
  resize: vertical;
}

/* Matched Summary Compact */
.matched-summary-compact {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--green-50);
  border-radius: 6px;
  border: 1px solid var(--green-200);
}

.matched-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--green-700);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}

.matched-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

/* Notes Row */
.notes-row {
  margin-top: auto;
}

/* Legacy compatibility */
.edit-columns {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
  min-height: 400px;
}

.source-panel {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 0.75rem;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-border);
}

.panel-header h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sql-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pattern-changes {
  padding: 0.5rem 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
  border: 1px solid var(--surface-border);
}

.changes-inline {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.changes-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}

.changes-label i {
  font-size: 0.9rem;
}

.changes-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.sql-editor-section {
  flex: 1;
}

.sql-editor {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.9rem;
  background: var(--surface-900);
  color: var(--surface-50);
  border-radius: 8px;
}

.matched-summary {
  padding: 0.75rem;
  background: var(--green-50);
  border-radius: 6px;
  border: 1px solid var(--green-200);
}

.matched-summary h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: var(--green-700);
}

/* AI Assist Dialog */
.ai-assist-content p {
  margin: 0 0 1rem 0;
  color: var(--text-color-secondary);
}

/* Reject Dialog */
.reject-dialog-content p {
  margin: 0 0 1rem 0;
  color: var(--text-color-secondary);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
}

.w-full {
  width: 100%;
}

/* Pattern Alternatives Dialog */
.loading-alternatives {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 1rem;
}

.alternatives-intro {
  margin: 0 0 1.5rem 0;
  color: var(--text-color-secondary);
}

.variant-card {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  transition: border-color 0.2s;
}

.variant-card:hover {
  border-color: var(--primary-color);
}

.variant-card.is-current {
  border-color: var(--green-500);
  background: var(--green-50);
}

.variant-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.variant-transforms {
  flex: 1;
  font-weight: 500;
  color: var(--text-color);
}

.variant-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.75rem;
}

.variant-meta i {
  margin-right: 0.25rem;
}

.variant-sql-preview {
  background: var(--surface-100);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
  overflow-x: auto;
}

.variant-sql-preview code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.8rem;
  color: var(--primary-700);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>

