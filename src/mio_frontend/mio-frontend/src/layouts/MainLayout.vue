<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />
        <q-toolbar-title>
          MIO Dashboard
        </q-toolbar-title>
        <q-btn flat round :icon="$q.dark.isActive ? 'dark_mode' : 'light_mode'" @click="toggleDarkMode" class="q-mr-sm" />
        <div class="q-mr-md">User: {{ username }}</div>
        <q-btn flat round icon="logout" @click="handleLogout" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered>
      <q-list>
        <q-item-label header>
          Menu
        </q-item-label>

        <q-item clickable v-ripple to="/sessions">
          <q-item-section avatar>
            <q-icon name="chat" />
          </q-item-section>
          <q-item-section>
            Sessions
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/personas">
          <q-item-section avatar>
            <q-icon name="people" />
          </q-item-section>
          <q-item-section>
            Personas
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/profiles">
          <q-item-section avatar>
            <q-icon name="settings" />
          </q-item-section>
          <q-item-section>
            API Profiles
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/account">
          <q-item-section avatar>
            <q-icon name="manage_accounts" />
          </q-item-section>
          <q-item-section>
            Account Settings
          </q-item-section>
        </q-item>

        <q-item v-if="isAdmin" clickable v-ripple to="/admin/users">
          <q-item-section avatar>
            <q-icon name="security" />
          </q-item-section>
          <q-item-section>
            Admin Users
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/debug">
          <q-item-section avatar>
            <q-icon name="bug_report" />
          </q-item-section>
          <q-item-section>
            DEBUG
          </q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <div class="q-pa-md" v-if="needsVerification">
        <q-banner class="bg-warning text-black" rounded dense>
          <div>
            邮箱未验证：请前往邮箱点击验证链接后再继续使用写操作。可在 Account Settings 页面重新发送邮件。
          </div>
          <template #action>
            <q-btn flat color="black" label="去验证" @click="goToVerify" />
          </template>
        </q-banner>
      </div>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { authState, logout, EMAIL_VERIFICATION_EVENT } from '../api'

const leftDrawerOpen = ref(false)
const router = useRouter()
const $q = useQuasar()

const username = computed(() => authState.username)
const needsVerification = computed(() => authState.isLoggedIn && !authState.isVerified)
const isAdmin = computed(() => authState.isSuperuser || authState.role === 'admin')

function toggleLeftDrawer () {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

function toggleDarkMode() {
  $q.dark.toggle()
}

function handleLogout() {
  logout()
  router.push('/login')
}

function goToVerify() {
  router.push({ path: '/verify-email', query: { email: authState.email || undefined } })
}

const handleVerificationEvent = () => {
  $q.notify({ type: 'warning', message: '请先完成邮箱验证后再执行此操作' })
  goToVerify()
}

onMounted(() => {
  window.addEventListener(EMAIL_VERIFICATION_EVENT, handleVerificationEvent)
})

onUnmounted(() => {
  window.removeEventListener(EMAIL_VERIFICATION_EVENT, handleVerificationEvent)
})
</script>
