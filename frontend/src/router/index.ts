/**
 * Vue Router Configuration
 * 
 * Defines the application's routing structure and navigation hierarchy.
 * Uses nested routes with AppLayout as the parent wrapper component.
 * 
 * Route Structure:
 * - / (root) → Introduction/Dashboard page
 * - /unmapped-fields → Unmapped Fields page (select source fields)
 * - /mapping-config → Mapping Configuration (SQL editor approach)
 * - /mappings → View Current Mappings (all users)
 * - /semantic-fields → Semantic Table Management (admin only)
 * - /config → Admin Configuration (admin only)
 * - /admin → Admin Tools - System settings, User Management (admin only)
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
          // Admin tools - system settings, user management, etc.
          path: '/admin',
          name: 'admin',
          component: () => import('../views/AdminView.vue')
        }
      ]
    }
  ],
})

export default router
