// API Service for Backend Communication

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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

export default {
  checkHealth,
  getData,
  postData,
}

