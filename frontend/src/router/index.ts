/**
 * Vue Router Configuration
 * 
 * Defines the application's routing structure and navigation hierarchy.
 * Uses nested routes with AppLayout as the parent wrapper component.
 * 
 * Route Structure:
 * - / (root) → Introduction/Dashboard page
 * - /unmapped-fields → Unmapped Fields page (multi-field mapping)
 * - /mapping-config → Mapping Configuration page (configure mapping)
 * - /config → Admin Configuration page (semantic table, settings)
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
          // Admin configuration page - semantic table and settings
          path: '/config',
          name: 'config',
          component: () => import('../views/ConfigView.vue')
        }
      ]
    }
  ],
})

export default router
