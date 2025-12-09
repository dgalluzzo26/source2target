/**
 * AI Suggestions Store
 * 
 * Manages AI-powered mapping suggestions for source fields.
 * Uses V3 API with dual vector search (semantic + historical patterns).
 * 
 * Enhanced with pattern template detection for multi-field mappings.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UnmappedField } from './unmappedFieldsStore'

export interface AISuggestion {
  semantic_field_id: number  // FK to semantic_fields table (REQUIRED for mapping creation)
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_comments?: string  // Target field description/comments
  search_score: number
  match_quality: 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown'
  ai_reasoning: string
  rank?: number  // UI-only: 1, 2, 3...
  fromPattern?: boolean  // True if this suggestion comes from a pattern match
  patternId?: number  // ID of the matching pattern if applicable
}

export interface HistoricalPattern {
  mapped_field_id: number
  tgt_table_name: string
  tgt_column_name: string
  tgt_table_physical_name?: string
  tgt_column_physical_name?: string
  source_expression?: string
  source_tables?: string
  source_columns?: string
  source_descriptions?: string
  source_relationship_type?: string
  transformations_applied?: string
  confidence_score?: number
  search_score?: number
  ai_reasoning?: string
  // Enhanced properties for template matching
  isMultiColumn?: boolean
  columnCount?: number
  matchedToCurrentSelection?: boolean
  templateRelevance?: number  // 0-1 score of how well this pattern matches user's selection
}

export interface PatternTemplate {
  pattern: HistoricalPattern
  relevanceScore: number
  missingFields: string[]  // Column names that user hasn't selected yet
  selectedFields: string[]  // Column names user has selected
  isComplete: boolean
  suggestedSQL?: string
}

export const useAISuggestionsStore = defineStore('aiSuggestions', () => {
  // State
  const suggestions = ref<AISuggestion[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const sourceFieldsUsed = ref<UnmappedField[]>([])
  const selectedSuggestion = ref<AISuggestion | null>(null)
  const historicalPatterns = ref<HistoricalPattern[]>([])
  const patternTemplates = ref<PatternTemplate[]>([])  // Templates that need additional fields
  const recommendedExpression = ref<string>('')
  const detectedPatternType = ref<string>('SINGLE')

  // Computed
  const hasSuggestions = computed(() => suggestions.value.length > 0)
  const topSuggestion = computed(() => suggestions.value[0] || null)
  
  // Pattern templates that suggest the user should add more fields
  const hasRelevantTemplates = computed(() => patternTemplates.value.length > 0)
  const topTemplate = computed(() => patternTemplates.value[0] || null)
  
  // Multi-column patterns from historical data
  const multiColumnPatterns = computed(() => {
    return historicalPatterns.value.filter(p => p.isMultiColumn)
  })
  
  // Actions
  async function generateSuggestions(sourceFields: UnmappedField[], allAvailableFields?: UnmappedField[]) {
    // IMPORTANT: Clear ALL previous state first
    console.log('[AI Suggestions] === Starting new suggestion request ===')
    console.log('[AI Suggestions] Clearing previous state...')
    
    loading.value = true
    error.value = null
    suggestions.value = []
    historicalPatterns.value = []
    patternTemplates.value = []
    recommendedExpression.value = ''
    detectedPatternType.value = 'SINGLE'
    sourceFieldsUsed.value = [...sourceFields]
    
    console.log('[AI Suggestions] State cleared. Historical patterns:', historicalPatterns.value.length)
    console.log('[AI Suggestions] Source fields for this query:', sourceFields.map(f => f.src_column_name))

    try {
      console.log('[AI Suggestions] Calling V3 API for', sourceFields.length, 'source fields')
      
      const response = await fetch('/api/v3/ai/suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_fields: sourceFields.map(f => ({
            src_table_name: f.src_table_name,
            src_table_physical_name: f.src_table_physical_name,
            src_column_name: f.src_column_name,
            src_column_physical_name: f.src_column_physical_name,
            src_physical_datatype: f.src_physical_datatype,
            src_comments: f.src_comments || ''
          })),
          num_results: 10
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`API error: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('[AI Suggestions] V3 API response:', JSON.stringify(data, null, 2))
      
      // V3 API returns target_candidates, historical_patterns, best_target, etc.
      const targetCandidates = data.target_candidates || []
      const bestTarget = data.best_target || {}
      const llmReasoning = bestTarget.reasoning || data.recommended_expression || ''
      
      console.log('[AI Suggestions] Best target from LLM:', bestTarget)
      console.log('[AI Suggestions] Target candidates count:', targetCandidates.length)
      
      // Transform target candidates into suggestion format
      suggestions.value = targetCandidates.map((candidate: any, idx: number) => {
        // Parse score - might be number, string, or undefined
        // Databricks vector search returns raw cosine similarity scores (typically 0.001-0.01 range)
        // Multiply by 100 to get a more intuitive 0-1 scale (e.g., 0.00576 -> 0.576)
        let score = 0
        if (candidate.search_score !== undefined && candidate.search_score !== null) {
          const rawScore = typeof candidate.search_score === 'string' 
            ? parseFloat(candidate.search_score) 
            : Number(candidate.search_score)
          
          // If score is very small (< 0.1), multiply by 100 to normalize
          // This handles Databricks vector search raw scores
          score = rawScore < 0.1 ? rawScore * 100 : rawScore
        }
        
        // Check if this is the LLM's best target (case-insensitive comparison)
        const candidateCol = (candidate.tgt_column_name || '').toLowerCase().trim()
        const bestTargetCol = (bestTarget.tgt_column_name || '').toLowerCase().trim()
        const isBestTarget = candidateCol === bestTargetCol && candidateCol !== ''
        
        // Also check table name match if available
        const candidateTable = (candidate.tgt_table_name || '').toLowerCase().trim()
        const bestTargetTable = (bestTarget.tgt_table_name || '').toLowerCase().trim()
        const isExactMatch = isBestTarget && (bestTargetTable === '' || candidateTable === bestTargetTable)
        
        // Debug first few candidates
        if (idx < 5) {
          const rawScore = candidate.search_score
          console.log(`[AI Suggestions] Candidate ${idx + 1}:`, {
            column: candidate.tgt_column_name,
            rawScore: rawScore,
            normalizedScore: score,
            wasNormalized: rawScore < 0.02,
            matchQuality: matchQuality,
            isBestTarget: isExactMatch
          })
        }
        
        // Determine match quality
        const matchQuality = getMatchQuality(score, isExactMatch)
        
        // Build reasoning
        let reasoning = ''
        if (isExactMatch && llmReasoning) {
          reasoning = llmReasoning
        } else if (candidate.tgt_comments) {
          reasoning = candidate.tgt_comments
        } else {
          // Score is 0-1 similarity, display as decimal (e.g., 0.85) not percentage
          reasoning = `Vector search similarity: ${score.toFixed(4)}`
        }
        
        return {
          semantic_field_id: candidate.semantic_field_id || 0,
          tgt_table_name: candidate.tgt_table_name || '',
          tgt_table_physical_name: candidate.tgt_table_physical_name || candidate.tgt_table_name || '',
          tgt_column_name: candidate.tgt_column_name || '',
          tgt_column_physical_name: candidate.tgt_column_physical_name || candidate.tgt_column_name || '',
          tgt_comments: candidate.tgt_comments || '',
          search_score: score,
          match_quality: matchQuality,
          ai_reasoning: reasoning,
          rank: idx + 1
        } as AISuggestion
      })
      
      // If we have a best target but it's not in top candidates, move it to top
      if (bestTarget.tgt_column_name && suggestions.value.length > 0) {
        const bestIdx = suggestions.value.findIndex(
          s => s.tgt_column_name.toLowerCase() === bestTarget.tgt_column_name?.toLowerCase()
        )
        if (bestIdx > 0) {
          // Move best target to position 0
          const best = suggestions.value.splice(bestIdx, 1)[0]
          best.match_quality = 'Excellent'
          best.ai_reasoning = llmReasoning || best.ai_reasoning
          suggestions.value.unshift(best)
          // Re-rank
          suggestions.value.forEach((s, i) => { s.rank = i + 1 })
        }
      }
      
      // Store recommended expression and pattern type from LLM
      recommendedExpression.value = data.recommended_expression || ''
      detectedPatternType.value = data.detected_pattern || 'SINGLE'
      
      // Process historical patterns with enhanced analysis
      const patternsFromApi = data.historical_patterns || []
      console.log('[AI Suggestions] Historical patterns received from API:', patternsFromApi.length)
      
      // Enhance patterns with analysis
      const enhancedPatterns = processPatterns(patternsFromApi, sourceFields)
      historicalPatterns.value = enhancedPatterns
      
      // Generate pattern templates for multi-column patterns
      const templates = generatePatternTemplates(enhancedPatterns, sourceFields, allAvailableFields || [])
      patternTemplates.value = templates
      
      console.log('[AI Suggestions] Enhanced patterns:', enhancedPatterns.length)
      console.log('[AI Suggestions] Pattern templates generated:', templates.length)
      
      // BOOST: If historical patterns strongly match target columns, boost those suggestions
      // This addresses the issue where vector search gives weak scores for combined fields
      // but historical patterns show what target should be used
      if (enhancedPatterns.length > 0) {
        boostPatternMatchingSuggestions(enhancedPatterns)
        
        // Also add pattern-based suggestions to the list if they're not already there
        addPatternBasedSuggestions(enhancedPatterns)
      }
      
      // Debug output
      console.log('[AI Suggestions] === Results Summary ===')
      console.log('[AI Suggestions] Final suggestions:', suggestions.value.length)
      console.log('[AI Suggestions] Final historical patterns:', historicalPatterns.value.length)
      if (suggestions.value.length > 0) {
        console.log('[AI Suggestions] Top suggestion:', suggestions.value[0])
      }
      
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate suggestions'
      console.error('[AI Suggestions] Error:', error.value)
      suggestions.value = []
    } finally {
      loading.value = false
    }
  }
  
  // Helper: Normalize Databricks vector search scores
  // Raw scores from Databricks are typically in 0.001-0.01 range
  // We multiply by 100 to get a more intuitive 0-1 scale
  // BUT only for very small scores that are clearly raw Databricks scores
  function normalizeScore(rawScore: number): number {
    if (!rawScore || isNaN(rawScore)) return 0
    // Only normalize if score is VERY small (< 0.02) - clearly a raw Databricks score
    // Scores >= 0.02 are likely already in a reasonable range
    if (rawScore < 0.02) {
      return rawScore * 100
    }
    return rawScore
  }
  
  // Helper: Convert score to match quality
  // Uses RELATIVE scoring - compare against the top score in the results
  // This prevents unrelated fields from showing as "Strong" just because 
  // they have some vector similarity
  function getMatchQuality(score: number, isBestTarget: boolean): 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown' {
    // LLM's best target always gets Excellent
    if (isBestTarget) return 'Excellent'
    
    // Handle invalid scores
    if (isNaN(score) || score === null || score === undefined) {
      console.warn('[AI Suggestions] Invalid score:', score)
      return 'Unknown'
    }
    
    // Normalize if needed (in case raw score wasn't pre-normalized)
    const normalizedScore = score > 1 ? score / 100 : score
    
    // STRICTER thresholds - only truly good matches get high quality
    // These thresholds work with normalized scores (0-1 range after x100)
    if (normalizedScore >= 0.70) return 'Excellent'  // Very strong semantic match
    if (normalizedScore >= 0.55) return 'Strong'     // Good match
    if (normalizedScore >= 0.40) return 'Good'       // Moderate match
    if (normalizedScore >= 0.20) return 'Weak'       // Some relevance
    if (normalizedScore > 0) return 'Weak'
    return 'Unknown'
  }
  
  // Helper: Process historical patterns to detect multi-column mappings
  function processPatterns(patterns: any[], selectedFields: UnmappedField[]): HistoricalPattern[] {
    const selectedColNames = new Set(
      selectedFields.map(f => (f.src_column_physical_name || f.src_column_name || '').toLowerCase())
    )
    const selectedColWords = new Set<string>()
    selectedFields.forEach(f => {
      const words = (f.src_column_physical_name || f.src_column_name || '').toLowerCase().split(/[_\s]+/)
      words.forEach(w => selectedColWords.add(w))
    })
    
    return patterns.map((p: any) => {
      // Parse source columns to determine if multi-column
      const sourceColsStr = p.source_columns || ''
      const sourceCols = sourceColsStr.split(/[|,]/).map((c: string) => c.trim()).filter((c: string) => c)
      const isMultiColumn = sourceCols.length > 1 || 
                           p.source_relationship_type === 'CONCAT' ||
                           p.source_relationship_type === 'JOIN' ||
                           p.source_relationship_type === 'UNION' ||
                           (p.source_expression && (
                             p.source_expression.includes('CONCAT') ||
                             p.source_expression.includes('||')
                           ))
      
      // Calculate how well this pattern matches the current selection
      let matchedCols = 0
      let relevance = 0
      
      sourceCols.forEach((col: string) => {
        const colLower = col.toLowerCase()
        const colWords = colLower.split(/[_\s]+/)
        
        // Check direct match
        if (selectedColNames.has(colLower)) {
          matchedCols++
          relevance += 1.0
        } else {
          // Check word overlap
          const overlap = colWords.filter((w: string) => selectedColWords.has(w)).length
          if (overlap > 0) {
            relevance += overlap / Math.max(colWords.length, 1) * 0.5
          }
        }
      })
      
      // Normalize relevance by total columns in pattern
      const normalizedRelevance = sourceCols.length > 0 ? relevance / sourceCols.length : 0
      
      return {
        ...p,
        isMultiColumn,
        columnCount: sourceCols.length,
        matchedToCurrentSelection: matchedCols > 0,
        templateRelevance: normalizedRelevance,
        // Normalize search scores - Databricks returns raw scores that need x100
        search_score: normalizeScore(typeof p.search_score === 'number' ? p.search_score : parseFloat(p.search_score) || 0),
        confidence_score: normalizeScore(typeof p.confidence_score === 'number' ? p.confidence_score : parseFloat(p.confidence_score) || 0)
      } as HistoricalPattern
    }).sort((a, b) => {
      // Sort by relevance first, then by search score
      if (b.templateRelevance !== a.templateRelevance) {
        return (b.templateRelevance || 0) - (a.templateRelevance || 0)
      }
      return (b.search_score || 0) - (a.search_score || 0)
    })
  }
  
  // Helper: Boost suggestions that match high-relevance historical patterns
  // ONLY boost when we're confident the pattern is actually relevant
  function boostPatternMatchingSuggestions(patterns: HistoricalPattern[]) {
    // STRICT: Only boost patterns with HIGH relevance (> 0.5)
    // This prevents irrelevant patterns from polluting the suggestions
    const highlyRelevantPatterns = patterns.filter(p => 
      (p.templateRelevance || 0) >= 0.5 && p.matchedToCurrentSelection
    )
    
    if (highlyRelevantPatterns.length === 0) {
      console.log('[AI Suggestions] No highly relevant patterns to boost (need relevance >= 0.5 AND matchedToCurrentSelection)')
      return
    }
    
    console.log('[AI Suggestions] Boosting', highlyRelevantPatterns.length, 'highly relevant patterns')
    
    // For each highly relevant pattern, find matching suggestions
    for (const pattern of highlyRelevantPatterns) {
      const patternTarget = (pattern.tgt_column_name || '').toLowerCase()
      const patternTable = (pattern.tgt_table_name || '').toLowerCase()
      
      const matchingIdx = suggestions.value.findIndex(s => {
        const sugTarget = (s.tgt_column_name || '').toLowerCase()
        const sugTable = (s.tgt_table_name || '').toLowerCase()
        return sugTarget === patternTarget && (patternTable === '' || sugTable === patternTable)
      })
      
      if (matchingIdx >= 0) {
        const suggestion = suggestions.value[matchingIdx]
        
        // Boost this suggestion
        const boosted = {
          ...suggestion,
          match_quality: 'Excellent' as const,
          ai_reasoning: `Historical pattern match (${Math.round((pattern.templateRelevance || 0) * 100)}% relevance): This target has been successfully mapped ${pattern.columnCount || 1} time(s) with similar source fields using ${pattern.transformations_applied || 'direct mapping'}.`,
          fromPattern: true,
          patternId: pattern.mapped_field_id
        }
        
        // If not already at top, move to position 0 or 1 (after LLM best if present)
        if (matchingIdx > 1) {
          suggestions.value.splice(matchingIdx, 1)
          // Insert at position 1 (after LLM best) or 0 if LLM best isn't excellent
          const insertIdx = suggestions.value[0]?.match_quality === 'Excellent' && !suggestions.value[0]?.fromPattern ? 1 : 0
          suggestions.value.splice(insertIdx, 0, boosted)
        } else {
          // Just update in place
          suggestions.value[matchingIdx] = boosted
        }
        
        // Re-rank all suggestions
        suggestions.value.forEach((s, i) => { s.rank = i + 1 })
        
        console.log('[AI Suggestions] Boosted pattern-matching suggestion:', patternTarget, 'to rank', suggestions.value.findIndex(s => s.tgt_column_name?.toLowerCase() === patternTarget) + 1)
      }
    }
  }
  
  // Helper: Add suggestions based on historical patterns that aren't already in the list
  // ONLY add if the pattern is highly relevant to the user's selection
  function addPatternBasedSuggestions(patterns: HistoricalPattern[]) {
    // STRICT: Only add patterns that are:
    // 1. Multi-column AND
    // 2. Have high relevance (actually match the user's selected fields)
    const highlyRelevantPatterns = patterns.filter(p => 
      p.isMultiColumn && 
      p.matchedToCurrentSelection &&
      (p.templateRelevance || 0) >= 0.4
    ).slice(0, 2)  // Max 2 pattern suggestions
    
    console.log('[AI Suggestions] Adding pattern suggestions:', highlyRelevantPatterns.map(p => p.tgt_column_name))
    
    for (const pattern of highlyRelevantPatterns) {
      const patternTarget = (pattern.tgt_column_name || '').toLowerCase()
      
      // Check if already in suggestions
      const exists = suggestions.value.some(s => 
        (s.tgt_column_name || '').toLowerCase() === patternTarget
      )
      
      if (!exists && pattern.tgt_column_name) {
        // Add as a new suggestion at position based on search score
        const newSuggestion: AISuggestion = {
          semantic_field_id: 0, // Will need lookup
          tgt_table_name: pattern.tgt_table_name || '',
          tgt_table_physical_name: pattern.tgt_table_physical_name || pattern.tgt_table_name || '',
          tgt_column_name: pattern.tgt_column_name,
          tgt_column_physical_name: pattern.tgt_column_physical_name || pattern.tgt_column_name || '',
          tgt_comments: '',
          search_score: pattern.search_score || 0.5,
          match_quality: 'Strong',
          ai_reasoning: `📋 Pattern Match: This target typically uses ${pattern.columnCount || 2}+ columns with ${pattern.transformations_applied || 'combined'} transformation. ${pattern.source_relationship_type || 'CONCAT'} pattern detected.`,
          rank: 0,
          fromPattern: true,
          patternId: pattern.mapped_field_id
        }
        
        // Insert at position 1 (after best if present) or 0
        const insertIdx = suggestions.value.length > 0 && suggestions.value[0].match_quality === 'Excellent' ? 1 : 0
        suggestions.value.splice(insertIdx, 0, newSuggestion)
        
        console.log('[AI Suggestions] Added pattern-based suggestion:', pattern.tgt_column_name)
      }
    }
    
    // Re-rank all suggestions
    suggestions.value.forEach((s, i) => { s.rank = i + 1 })
  }
  
  // Helper: Generate pattern templates for multi-column patterns
  // ONLY show templates when the pattern is HIGHLY relevant to the user's selection
  function generatePatternTemplates(
    patterns: HistoricalPattern[], 
    selectedFields: UnmappedField[],
    availableFields: UnmappedField[]
  ): PatternTemplate[] {
    const templates: PatternTemplate[] = []
    
    console.log('[AI Suggestions] Generating templates from', patterns.length, 'patterns')
    console.log('[AI Suggestions] Selected fields:', selectedFields.map(f => f.src_column_name))
    
    // Get words from the selected field names and descriptions for matching
    const selectedFieldInfo = selectedFields.map(f => ({
      name: (f.src_column_physical_name || f.src_column_name || '').toLowerCase(),
      words: new Set((f.src_column_physical_name || f.src_column_name || '').toLowerCase().split(/[_\s]+/)),
      descWords: new Set((f.src_comments || '').toLowerCase().split(/\s+/).filter(w => w.length > 2))
    }))
    
    // STRICT filter: Only consider multi-column patterns where:
    // 1. Pattern has high relevance score (templateRelevance > 0.4)
    // 2. OR pattern's source columns have significant word overlap with selected field
    const relevantPatterns = patterns.filter(p => {
      if (!p.isMultiColumn) return false
      
      // Check if pattern columns have any word overlap with selected fields
      const patternCols = (p.source_columns || '').toLowerCase().split(/[|,]/).map(c => c.trim()).filter(c => c)
      const patternWords = new Set<string>()
      patternCols.forEach(col => col.split(/[_\s]+/).forEach(w => patternWords.add(w)))
      
      // Calculate word overlap with selected fields
      let overlap = 0
      selectedFieldInfo.forEach(sf => {
        sf.words.forEach(w => {
          if (patternWords.has(w)) overlap++
        })
      })
      
      const hasSignificantOverlap = overlap >= 1 && overlap >= Math.min(patternWords.size, 2) * 0.3
      const hasHighRelevance = (p.templateRelevance || 0) >= 0.4
      
      console.log(`[AI Suggestions] Pattern ${p.tgt_column_name}: overlap=${overlap}, relevance=${p.templateRelevance}, show=${hasSignificantOverlap || hasHighRelevance}`)
      
      return hasSignificantOverlap || hasHighRelevance
    })
    
    console.log('[AI Suggestions] Relevant multi-column patterns:', relevantPatterns.length)
    
    relevantPatterns.forEach(pattern => {
      const sourceColsStr = pattern.source_columns || ''
      const sourceCols = sourceColsStr.split(/[|,]/).map(c => c.trim()).filter(c => c)
      
      // If no source_columns, try to infer from expression or just show as template
      let columnsForTemplate = sourceCols
      if (columnsForTemplate.length === 0 && pattern.source_expression) {
        // Try to extract column names from expression
        // Match patterns like "column_name" or table.column
        const matches = pattern.source_expression.match(/\b([a-z][a-z0-9_]*)\b/gi) || []
        const keywords = new Set(['CONCAT', 'TRIM', 'UPPER', 'LOWER', 'INITCAP', 'COALESCE', 'CAST', 'AS', 'FROM', 'SELECT', 'AND', 'OR', 'NULL', 'STRING', 'INT', 'VARCHAR'])
        columnsForTemplate = matches.filter(m => !keywords.has(m.toUpperCase()))
      }
      
      // Determine which fields are already selected vs missing
      const selectedInPattern: string[] = []
      const missingInPattern: string[] = []
      
      // For each selected field, see if it matches any pattern column
      const matchedPatternCols = new Set<string>()
      selectedFields.forEach(field => {
        const fCol = (field.src_column_physical_name || field.src_column_name || '').toLowerCase()
        const fWords = new Set(fCol.split(/[_\s]+/))
        
        columnsForTemplate.forEach(col => {
          const colLower = col.toLowerCase()
          const colWords = colLower.split(/[_\s]+/)
          
          // Check for match
          const hasOverlap = colWords.some(w => fWords.has(w)) || fCol === colLower
          if (hasOverlap) {
            selectedInPattern.push(col)
            matchedPatternCols.add(col)
          }
        })
      })
      
      // Remaining columns are "missing"
      columnsForTemplate.forEach(col => {
        if (!matchedPatternCols.has(col)) {
          missingInPattern.push(col)
        }
      })
      
      // Create template if:
      // 1. It's a multi-column pattern (even if we couldn't match slots), OR
      // 2. User has some fields selected but not all
      const shouldShowTemplate = 
        (pattern.isMultiColumn && columnsForTemplate.length > 1) ||
        (selectedInPattern.length > 0 && missingInPattern.length > 0) ||
        (pattern.search_score && pattern.search_score > 0.4 && columnsForTemplate.length > 1)
      
      if (shouldShowTemplate) {
        // If we couldn't determine selected/missing, default to showing current field as selected
        // and pattern suggests adding more
        if (selectedInPattern.length === 0 && selectedFields.length > 0) {
          selectedInPattern.push(selectedFields[0].src_column_name)
          missingInPattern.push('Additional Field')
        }
        
        templates.push({
          pattern,
          relevanceScore: pattern.templateRelevance || pattern.search_score || 0,
          selectedFields: selectedInPattern,
          missingFields: missingInPattern,
          isComplete: missingInPattern.length === 0,
          suggestedSQL: pattern.source_expression || ''
        })
        
        console.log('[AI Suggestions] Created template for', pattern.tgt_column_name, {
          selected: selectedInPattern,
          missing: missingInPattern,
          score: pattern.search_score
        })
      }
    })
    
    // Sort by relevance score
    return templates.sort((a, b) => b.relevanceScore - a.relevanceScore)
  }

  function selectSuggestion(suggestion: AISuggestion) {
    selectedSuggestion.value = suggestion
    console.log('[AI Suggestions] Selected:', suggestion.tgt_column_name)
  }

  function clearSuggestions() {
    suggestions.value = []
    sourceFieldsUsed.value = []
    selectedSuggestion.value = null
    historicalPatterns.value = []
    patternTemplates.value = []
    recommendedExpression.value = ''
    detectedPatternType.value = 'SINGLE'
    error.value = null
    console.log('[AI Suggestions] Cleared suggestions')
  }
  
  // Action: Update source fields (when user adds more fields via template)
  function addSourceField(field: UnmappedField) {
    if (!sourceFieldsUsed.value.find(f => f.id === field.id)) {
      sourceFieldsUsed.value.push(field)
      console.log('[AI Suggestions] Added source field:', field.src_column_name)
    }
  }
  
  // Action: Set multiple source fields (for template completion)
  function setSourceFields(fields: UnmappedField[]) {
    sourceFieldsUsed.value = [...fields]
    console.log('[AI Suggestions] Set source fields:', fields.map(f => f.src_column_name))
  }

  return {
    // State
    suggestions,
    loading,
    error,
    sourceFieldsUsed,
    selectedSuggestion,
    historicalPatterns,
    patternTemplates,
    recommendedExpression,
    detectedPatternType,
    
    // Computed
    hasSuggestions,
    topSuggestion,
    hasRelevantTemplates,
    topTemplate,
    multiColumnPatterns,
    
    // Actions
    generateSuggestions,
    selectSuggestion,
    clearSuggestions,
    addSourceField,
    setSourceFields
  }
})

