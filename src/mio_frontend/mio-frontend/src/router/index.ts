import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import SessionsPage from '../pages/SessionsPage.vue'
import PersonasPage from '../pages/PersonasPage.vue'
import ApiProfilesPage from '../pages/ApiProfilesPage.vue'
import ChatConversationPage from '../pages/ChatConversationPage.vue'
import { authState } from '../api'

const routes = [
  {
    path: '/login',
    component: LoginPage
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/sessions' },
      { path: 'sessions', component: SessionsPage },
      { path: 'personas', component: PersonasPage },
      { path: 'profiles', component: ApiProfilesPage }
    ]
  },
  {
    path: '/chat/:id',
    component: ChatConversationPage,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !authState.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})

export default router
