<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />
        <q-toolbar-title>
          {{ $t('layout.title') }}
        </q-toolbar-title>
        <LanguageSwitcher class="q-mr-sm" />
        <q-btn flat round :icon="$q.dark.isActive ? 'dark_mode' : 'light_mode'" @click="toggleDarkMode" class="q-mr-sm" />
        <div class="q-mr-md">{{ $t('nav.user', { username }) }}</div>
        <q-btn flat round icon="logout" @click="handleLogout" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered>
      <q-list>
        <q-item-label header>
          {{ $t('nav.menu') }}
        </q-item-label>

        <q-item clickable v-ripple to="/sessions">
          <q-item-section avatar>
            <q-icon name="chat" />
          </q-item-section>
          <q-item-section>
            {{ $t('nav.sessions') }}
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/personas">
          <q-item-section avatar>
            <q-icon name="people" />
          </q-item-section>
          <q-item-section>
            {{ $t('nav.personas') }}
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/profiles">
          <q-item-section avatar>
            <q-icon name="settings" />
          </q-item-section>
          <q-item-section>
            {{ $t('nav.profiles') }}
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/account">
          <q-item-section avatar>
            <q-icon name="manage_accounts" />
          </q-item-section>
          <q-item-section>
            {{ $t('nav.account') }}
          </q-item-section>
        </q-item>

        <q-item v-if="isAdmin" clickable v-ripple to="/admin/users">
          <q-item-section avatar>
            <q-icon name="security" />
          </q-item-section>
          <q-item-section>
            {{ $t('nav.adminUsers') }}
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/debug">
          <q-item-section avatar>
            <q-icon name="bug_report" />
          </q-item-section>
          <q-item-section>
            {{ $t('nav.debug') }}
          </q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <div class="q-pa-md" v-if="needsVerification">
        <q-banner class="bg-warning text-black" rounded dense>
          <div>
            {{ $t('layout.verifyBanner') }}
          </div>
          <template #action>
            <q-btn flat color="black" :label="$t('layout.goVerify')" @click="goToVerify" />
          </template>
        </q-banner>
      </div>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { authState, logout, EMAIL_VERIFICATION_EVENT } from '../api'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const leftDrawerOpen = ref(false)
const router = useRouter()
const $q = useQuasar()
const { t } = useI18n()

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
  $q.notify({ type: 'warning', message: t('layout.verifyNotify') })
  goToVerify()
}

onMounted(() => {
  window.addEventListener(EMAIL_VERIFICATION_EVENT, handleVerificationEvent)
})

onUnmounted(() => {
  window.removeEventListener(EMAIL_VERIFICATION_EVENT, handleVerificationEvent)
})
</script>
