import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import RegisterPage from '../pages/RegisterPage.vue'
import VerifyEmailPage from '../pages/VerifyEmailPage.vue'
import SessionsPage from '../pages/SessionsPage.vue'
import PersonasPage from '../pages/PersonasPage.vue'
import ApiProfilesPage from '../pages/ApiProfilesPage.vue'
import DebugPage from '../pages/DebugPage.vue'
import ChatConversationPage from '../pages/ChatConversationPage.vue'
import AccountSettingsPage from '../pages/AccountSettingsPage.vue'
import { authState } from '../api'
import AdminUsersPage from '../pages/AdminUsersPage.vue'

const routes = [
  {
    path: '/login',
    component: LoginPage,
    meta: { guest: true }
  },
  {
    path: '/register',
    component: RegisterPage,
    meta: { guest: true }
  },
  {
    path: '/verify-email',
    component: VerifyEmailPage,
    meta: { guest: true }
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/sessions' },
      { path: 'sessions', component: SessionsPage },
      { path: 'personas', component: PersonasPage },
      { path: 'profiles', component: ApiProfilesPage },
      { path: 'debug', component: DebugPage },
      { path: 'account', component: AccountSettingsPage },
      { path: 'chat/:id', component: ChatConversationPage },
      { path: 'admin/users', component: AdminUsersPage, meta: { requiresAdmin: true } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const isLoggedIn = authState.isLoggedIn
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const isGuestPage = to.matched.some(record => record.meta.guest)
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin)
  const isAdmin = authState.isSuperuser || authState.role === 'admin'

  if (requiresAuth && !isLoggedIn) {
    // 需要登录但未登录，跳转登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath } // 保存目标路径
    })
  } else if (isGuestPage && isLoggedIn) {
    // 已登录用户访问登录/注册页，跳转首页
    next('/')
  } else if (requiresAdmin && !isAdmin) {
    next('/sessions')
  } else {
    next()
  }
})

export default router
