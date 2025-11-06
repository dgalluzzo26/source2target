/**
 * User Store (Pinia)
 * 
 * Manages user authentication state and profile information.
 * Automatically detects the current user from Databricks workspace context
 * using the backend's /api/auth/current-user endpoint.
 * 
 * Authentication Flow:
 * 1. App initialization calls initializeAuth()
 * 2. Backend attempts to detect user via multiple methods:
 *    - X-Forwarded-Email header (Databricks App)
 *    - WorkspaceClient API
 *    - Environment variables
 *    - Falls back to demo user for local dev
 * 3. Admin status checked via Databricks workspace group membership
 * 
 * @module stores/user
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * User profile information structure.
 * 
 * Represents an authenticated user with their role and permissions.
 * Admin status is determined by Databricks workspace group membership.
 */
export interface User {
  /** Numeric user ID (not currently used by backend) */
  id: number
  /** User email address (primary identifier) */
  email: string
  /** Display name for UI (derived from email) */
  display_name: string
  /** User role determining permissions */
  role: 'admin' | 'platform_user' | 'user'
  /** Whether user has admin privileges (can access Config page) */
  is_admin: boolean
  /** Whether user can access the platform */
  is_platform_user: boolean
  /** Whether user account is active */
  is_active: boolean
  /** Last login timestamp (optional) */
  last_login?: string
  /** Account creation timestamp */
  date_joined: string
}

/**
 * User store composable.
 * 
 * Provides reactive state management for user authentication and profile.
 * Automatically initialized on app startup to detect current user.
 */
export const useUserStore = defineStore('user', () => {
  // ========================================================================
  // State
  // ========================================================================
  
  /** Current authenticated user profile or null if not authenticated */
  const currentUser = ref<User | null>(null)
  
  /** Loading state for async operations */
  const loading = ref(false)
  
  /** Error message from last failed operation */
  const error = ref<string | null>(null)
  
  // ========================================================================
  // Computed Properties (Getters)
  // ========================================================================
  
  /** Whether a user is currently authenticated */
  const isAuthenticated = computed(() => currentUser.value !== null)
  
  /** Whether current user has admin privileges */
  const isAdmin = computed(() => currentUser.value?.is_admin || false)
  
  /** Whether current user can access the platform */
  const isPlatformUser = computed(() => currentUser.value?.is_platform_user || false)

  // ========================================================================
  // Actions
  // ========================================================================

  /**
   * Fetch current user information from backend.
   * 
   * Calls /api/auth/current-user which attempts to detect the user from
   * Databricks workspace context through multiple methods. Falls back to
   * a demo user for local development.
   * 
   * @returns Promise with success status and optional error message
   */
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

  /**
   * Refresh user profile (no-op in current implementation).
   * 
   * Placeholder for future profile refresh functionality. Currently does
   * nothing as profile information is static after initial load.
   */
  const refreshProfile = async () => {
    // Frontend-only mode: No profile refresh needed
    console.log('Frontend-only mode: Profile refresh skipped')
  }

  /**
   * Initialize authentication on app startup.
   * 
   * Automatically detects the current user from Databricks workspace context.
   * This should be called once during app initialization (in main.ts or App.vue).
   * Matches the behavior of the original Streamlit app.
   * 
   * @returns Promise that resolves when user detection completes
   */
  const initializeAuth = async () => {
    // Automatically detect user from Databricks context (like original app)
    await getCurrentUser()
  }

  /**
   * Clear the current error message.
   * 
   * Useful for dismissing error notifications in the UI.
   */
  const clearError = () => {
    error.value = null
  }

  // ========================================================================
  // Store API
  // ========================================================================

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