import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'introduction',
          component: () => import('../views/IntroductionView.vue')
        },
        {
          path: '/mapping',
          name: 'mapping',
          component: () => import('../views/MappingView.vue')
        },
        {
          path: '/config',
          name: 'config',
          component: () => import('../views/ConfigView.vue')
        },
        {
          path: '/admin',
          name: 'admin',
          component: () => import('../views/AdminView.vue')
        }
      ]
    }
  ],
})

export default router
