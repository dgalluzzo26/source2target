/**
 * Vue Router Configuration
 * 
 * Defines the application's routing structure and navigation hierarchy.
 * Uses nested routes with AppLayout as the parent wrapper component.
 * 
 * Route Structure:
 * V4 Target-First Workflow:
 * - /projects → Projects list (dashboard)
 * - /projects/:id → Project detail (target tables)
 * 
 * V3 Source-First Workflow (legacy):
 * - / (root) → Introduction/Dashboard page
 * - /unmapped-fields → Unmapped Fields page (select source fields)
 * - /mapping-config → Mapping Configuration (SQL editor approach)
 * - /mappings → View Current Mappings (all users)
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
          // Projects list - main V4 entry point
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
        // V3 SOURCE-FIRST WORKFLOW (Legacy)
        // ================================================================
        {
          // Unmapped fields page - main entry point for mapping
          path: '/unmapped-fields',
          name: 'unmapped-fields',
          component: () => import('../views/UnmappedFieldsView.vue')
        },
        {
          // Mapping configuration page - SQL editor approach
          path: '/mapping-config',
          name: 'mapping-config',
          component: () => import('../views/MappingConfigViewV3.vue')
        },
        {
          // View current mappings - available to all users
          path: '/mappings',
          name: 'mappings',
          component: () => import('../views/MappingsListViewV3.vue')
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
