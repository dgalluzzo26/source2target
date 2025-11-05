// API Service for Backend Communication

// In Databricks, the backend is on the same domain, so use relative URLs
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

interface ApiResponse<T> {
  data?: T
  error?: string
}

interface HealthResponse {
  status: string
}

interface DataItem {
  id: number
  name: string
  value: number
}

interface DataResponse {
  data: DataItem[]
}

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    return { data }
  } catch (error) {
    console.error('API Error:', error)
    return { error: error instanceof Error ? error.message : 'Unknown error occurred' }
  }
}

/**
 * Health Check
 */
export async function checkHealth(): Promise<ApiResponse<HealthResponse>> {
  return apiFetch<HealthResponse>('/api/health')
}

/**
 * Get Data
 */
export async function getData(): Promise<ApiResponse<DataResponse>> {
  return apiFetch<DataResponse>('/api/data')
}

/**
 * Example POST request
 */
export async function postData<T>(endpoint: string, data: unknown): Promise<ApiResponse<T>> {
  return apiFetch<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// Placeholder exports for components that need them
export class SystemAPI {
  static async getStatus() {
    // Placeholder - not implemented yet
    return {}
  }

  static async getHealth() {
    // Placeholder - not implemented yet
    return {}
  }
}

export const handleApiError = (error: any) => {
  console.error('API Error:', error)
  return { error: 'An error occurred' }
}

/**
 * Semantic Table API
 */
export interface SemanticRecord {
  id?: number
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_nullable: string
  tgt_physical_datatype: string
  tgt_comments?: string
  semantic_field?: string
}

export interface SemanticRecordCreate {
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_nullable: string
  tgt_physical_datatype: string
  tgt_comments?: string
}

export interface SemanticRecordUpdate {
  tgt_table_name?: string
  tgt_table_physical_name?: string
  tgt_column_name?: string
  tgt_column_physical_name?: string
  tgt_nullable?: string
  tgt_physical_datatype?: string
  tgt_comments?: string
}

export class SemanticAPI {
  /**
   * Get all semantic table records
   */
  static async getAllRecords(): Promise<ApiResponse<SemanticRecord[]>> {
    return apiFetch<SemanticRecord[]>('/api/semantic/records')
  }

  /**
   * Create a new semantic table record
   */
  static async createRecord(record: SemanticRecordCreate): Promise<ApiResponse<SemanticRecord>> {
    return apiFetch<SemanticRecord>('/api/semantic/records', {
      method: 'POST',
      body: JSON.stringify(record),
    })
  }

  /**
   * Update an existing semantic table record
   */
  static async updateRecord(recordId: number, record: SemanticRecordUpdate): Promise<ApiResponse<SemanticRecord>> {
    return apiFetch<SemanticRecord>(`/api/semantic/records/${recordId}`, {
      method: 'PUT',
      body: JSON.stringify(record),
    })
  }

  /**
   * Delete a semantic table record
   */
  static async deleteRecord(recordId: number): Promise<ApiResponse<{ status: string; message: string }>> {
    return apiFetch<{ status: string; message: string }>(`/api/semantic/records/${recordId}`, {
      method: 'DELETE',
    })
  }
}

export default {
  checkHealth,
  getData,
  postData,
}

