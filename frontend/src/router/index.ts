/**
 * Vue Router Configuration
 * 
 * Defines the application's routing structure and navigation hierarchy.
 * Uses nested routes with AppLayout as the parent wrapper component.
 * 
 * Route Structure:
 * - / (root) → Introduction/Dashboard page
 * - /unmapped-fields → Unmapped Fields page (multi-field mapping)
 * - /mapping-config → Mapping Configuration Wizard (configure mapping)
 * - /mappings → View Current Mappings (all users)
 * - /semantic-fields → Semantic Table Management (admin only)
 * - /config → Admin Configuration (admin only)
 * - /admin → Admin Tools - Transformations, User Management (admin only)
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
        {
          // V2 Unmapped fields page - main entry point for multi-field mapping
          path: '/unmapped-fields',
          name: 'unmapped-fields',
          component: () => import('../views/UnmappedFieldsView.vue')
        },
        {
          // V2 Mapping configuration page - configure multi-field mapping
          path: '/mapping-config',
          name: 'mapping-config',
          component: () => import('../views/MappingConfigView.vue')
        },
        {
          // View current mappings - available to all users
          path: '/mappings',
          name: 'mappings',
          component: () => import('../views/MappingsListView.vue')
        },
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
        {
          // Admin tools - transformations, user management, etc.
          path: '/admin',
          name: 'admin',
          component: () => import('../views/AdminView.vue')
        }
      ]
    }
  ],
})

export default router
