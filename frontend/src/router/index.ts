import { createRouter, createWebHistory, type RouteLocationGeneric } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('@/views/Dashboard.vue') },
      // 项目管理（仅项目本身）
      { path: 'projects', component: () => import('@/views/Projects.vue') },
      // 独立页面，人工关联项目
      { path: 'versions', component: () => import('@/views/standalone/VersionsPage.vue') },
      { path: 'features', component: () => import('@/views/standalone/FeaturesPage.vue') },
      { path: 'test-points', component: () => import('@/views/TestPoints.vue') },
      { path: 'test-cases', component: () => import('@/views/TestCases.vue') },
      { path: 'test-plans', component: () => import('@/views/TestPlans.vue') },
      { path: 'executions', component: () => import('@/views/standalone/TestExecutionsPage.vue') },
      { path: 'reports', component: () => import('@/views/standalone/ReportsPage.vue') },
      { path: 'reports/:executionId', component: () => import('@/views/standalone/ReportsPage.vue') },
      { path: 'executions/:executionId/results', component: () => import('@/views/executions/ExecutionResults.vue') },
      { path: 'executions/:executionId/logs', component: () => import('@/views/executions/ExecutionLogs.vue') },
      { path: 'executor-rules', component: () => import('@/views/executions/ExecutionCenter.vue') },
      // 兼容旧路径
      { path: 'projects/:projectId', redirect: '/projects' },
      { path: 'projects/:projectId/versions', redirect: '/versions' },
      { path: 'projects/:projectId/features', redirect: '/features' },
      { path: 'projects/:projectId/test-points', redirect: '/test-points' },
      { path: 'projects/:projectId/test-cases', redirect: '/test-cases' },
      { path: 'projects/:projectId/test-plans', redirect: '/test-plans' },
      { path: 'projects/:projectId/executions', redirect: '/executions' },
      { path: 'projects/:projectId/reports', redirect: '/reports' },
      { path: 'projects/:projectId/reports/:executionId', redirect: (to: RouteLocationGeneric) => `/reports/${String(to.params.executionId ?? '')}` },
      { path: 'test-points/:projectId', redirect: '/test-points' },
      { path: 'test-cases/:projectId', redirect: '/test-cases' },
      { path: 'test-plans/:projectId', redirect: '/test-plans' },
      { path: 'agents', component: () => import('@/views/Agents.vue') },
      { path: 'ai-models', component: () => import('@/views/AIModels.vue'), meta: { admin: true } },
      { path: 'knowledge', component: () => import('@/views/Knowledge.vue'), meta: { admin: true } },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, _from, next) => {
  const store = useUserStore()
  if (!to.meta.public && !store.token) return next('/login')
  if (to.meta.admin && !store.isAdmin()) return next('/dashboard')
  next()
})

export default router
