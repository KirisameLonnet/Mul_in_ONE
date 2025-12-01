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
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { authState, logout } from '../api'

const leftDrawerOpen = ref(false)
const router = useRouter()
const $q = useQuasar()

const username = computed(() => authState.username)

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
</script>
