/**
 * Vue Router Configuration
 * 
 * Defines the application's routing structure and navigation hierarchy.
 * Uses nested routes with AppLayout as the parent wrapper component.
 * 
 * Route Structure:
 * - / (root) → Introduction/Dashboard page
 * - /mapping → Field Mapping page (mapped/unmapped fields, AI suggestions)
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
          // Field mapping page - main application functionality
          path: '/mapping',
          name: 'mapping',
          component: () => import('../views/MappingView.vue')
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
