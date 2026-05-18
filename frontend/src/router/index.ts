import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/oauth/callback',
      name: 'OAuthCallback',
      component: () => import('@/views/OAuthCallback.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/components/Layout/AppLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/dashboard',
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '仪表盘' },
        },
        {
          path: 'keys',
          name: 'ApiKeys',
          component: () => import('@/views/ApiKeys.vue'),
          meta: { title: 'API Keys' },
        },
        {
          path: 'usage',
          name: 'UsageStats',
          component: () => import('@/views/UsageStats.vue'),
          meta: { title: '用量统计' },
        },
        {
          path: 'applications',
          name: 'Applications',
          component: () => import('@/views/Applications.vue'),
          meta: { title: '我的申请' },
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/Profile.vue'),
          meta: { title: '个人资料' },
        },
        {
          path: 'playground',
          name: 'Playground',
          component: () => import('@/views/Playground.vue'),
          meta: { title: 'API 测试' },
        },
        // Admin routes
        {
          path: 'admin/users',
          name: 'AdminUsers',
          component: () => import('@/views/admin/Users.vue'),
          meta: { title: '用户管理', requireAdmin: true },
        },
        {
          path: 'admin/keys',
          name: 'AdminKeys',
          component: () => import('@/views/admin/AllKeys.vue'),
          meta: { title: '密钥管理', requireAdmin: true },
        },
        {
          path: 'admin/analytics',
          name: 'AdminAnalytics',
          component: () => import('@/views/admin/Analytics.vue'),
          meta: { title: '全局分析', requireAdmin: true },
        },
        {
          path: 'admin/models',
          name: 'AdminModels',
          component: () => import('@/views/admin/Models.vue'),
          meta: { title: '模型管理', requireAdmin: true },
        },
        {
          path: 'admin/providers',
          name: 'AdminProviders',
          component: () => import('@/views/admin/Providers.vue'),
          meta: { title: '数据源管理', requireAdmin: true },
        },
        {
          path: 'admin/applications',
          name: 'AdminApplications',
          component: () => import('@/views/admin/Applications.vue'),
          meta: { title: '审批管理', requireAdmin: true },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard',
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!to.meta.public) {
    if (!auth.token) {
      return { name: 'Login' }
    }
    if (!auth.user) {
      await auth.init()
      if (!auth.user) {
        return { name: 'Login' }
      }
    }
  }

  if (to.meta.requireAdmin && !auth.isAdmin) {
    return { name: 'Dashboard' }
  }
})

export default router
