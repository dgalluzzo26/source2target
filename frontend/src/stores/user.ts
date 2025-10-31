import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// import { AuthAPI, handleApiError } from '@/services/api' // Disabled for frontend-only deployment

export interface User {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'platform_user' | 'user'
  is_admin: boolean
  is_platform_user: boolean
  is_active: boolean
  last_login?: string
  date_joined: string
}

export const useUserStore = defineStore('user', () => {
  const currentUser = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  const isAuthenticated = computed(() => currentUser.value !== null)
  const isAdmin = computed(() => currentUser.value?.is_admin || false)
  const isPlatformUser = computed(() => currentUser.value?.is_platform_user || false)

  const getCurrentUser = async () => {
    loading.value = true
    error.value = null
    
    try {
      // Call the backend API to get the real user from Databricks context
      const response = await fetch('/api/auth/current-user')
      if (!response.ok) {
        throw new Error('Failed to get user information')
      }
      
      const userInfo = await response.json()
      
      currentUser.value = {
        id: 1, // Backend doesn't have user ID yet
        email: userInfo.email || 'demo.user@gainwell.com',
        display_name: userInfo.display_name || 'Demo User',
        role: userInfo.is_admin ? 'admin' : 'platform_user',
        is_admin: userInfo.is_admin || false,
        is_platform_user: true,
        is_active: true,
        date_joined: new Date().toISOString()
      }
      
      console.log(`User detected: ${userInfo.email} (${userInfo.detection_method})`)
      return { success: true }
    } catch (error) {
      console.error('Error getting user from API:', error)
      // Fallback to dummy user
      currentUser.value = {
        id: 1,
        email: 'demo.user@gainwell.com',
        display_name: 'Demo User',
        role: 'platform_user',
        is_admin: false,
        is_platform_user: true,
        is_active: true,
        date_joined: new Date().toISOString()
      }
      return { success: false, error: 'Failed to get user' }
    } finally {
      loading.value = false
    }
  }

  const refreshProfile = async () => {
    // Frontend-only mode: No profile refresh needed
    console.log('Frontend-only mode: Profile refresh skipped')
  }

  const initializeAuth = async () => {
    // Automatically detect user from Databricks context (like original app)
    await getCurrentUser()
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    currentUser,
    loading,
    error,
    
    // Getters
    isAuthenticated,
    isAdmin,
    isPlatformUser,
    
    // Actions
    getCurrentUser,
    refreshProfile,
    initializeAuth,
    clearError
  }
})