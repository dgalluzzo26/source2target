/**
 * Vue Router Configuration
 * 
 * Defines the application's routing structure and navigation hierarchy.
 * Uses nested routes with AppLayout as the parent wrapper component.
 * 
 * Route Structure:
 * V4 Target-First Workflow:
 * - / (root) → Introduction/Dashboard page
 * - /projects → Projects list
 * - /projects/:id → Project detail (target tables & suggestions)
 * 
 * Admin:
 * - /semantic-fields → Semantic Table Management (admin only)
 * - /config → Admin Configuration (admin only)
 * 
 * All routes use code-splitting (lazy loading) for better performance,
 * except AppLayout which is loaded immediately as it's always needed.
 * 
 * @module router
 */

import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'

/**
 * Application router instance.
 * 
 * Configured with:
 * - HTML5 history mode for clean URLs (no hash)
 * - Nested route structure under AppLayout
 * - Lazy-loaded route components for code splitting
 */
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          // Default route - Introduction/Dashboard page
          path: '',
          name: 'introduction',
          component: () => import('../views/IntroductionView.vue')
        },
        
        // ================================================================
        // V4 TARGET-FIRST WORKFLOW
        // ================================================================
        {
          // Projects list - main entry point
          path: '/projects',
          name: 'projects',
          component: () => import('../views/ProjectsListView.vue')
        },
        {
          // Project detail - target tables and suggestions
          path: '/projects/:id',
          name: 'project-detail',
          component: () => import('../views/ProjectDetailView.vue')
        },
        
        // ================================================================
        // ADMIN
        // ================================================================
        {
          // Semantic table management - admin only
          path: '/semantic-fields',
          name: 'semantic-fields',
          component: () => import('../views/SemanticFieldsView.vue')
        },
        {
          // Admin configuration page - general settings
          path: '/config',
          name: 'config',
          component: () => import('../views/ConfigView.vue')
        },
      ]
    }
  ],
})

export default router
