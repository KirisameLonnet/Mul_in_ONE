<template>
  <d-layout class="main-layout">
    <d-aside class="sidebar" width="250px">
      <div class="user-info">
        <d-avatar :name="username" width="40" height="40" />
        <div class="details">
          <div class="name">{{ username }}</div>
        </div>
      </div>

      <d-menu :select-keys="[currentView]" @select="onMenuSelect">
        <d-menu-item key="sessions">
          <template #icon><i class="icon-message"></i></template>
          Sessions
        </d-menu-item>
        <d-menu-item key="personas">
          <template #icon><i class="icon-people"></i></template>
          Personas
        </d-menu-item>
        <d-menu-item key="profiles">
          <template #icon><i class="icon-setting"></i></template>
          API Profiles
        </d-menu-item>
        <d-menu-item key="debug">
          <template #icon><i class="icon-info"></i></template>
          DEBUG
        </d-menu-item>
      </d-menu>

      <div class="footer">
        <d-button variant="text" color="danger" @click="handleLogout" width="100%">
          <i class="icon-logout"></i> Logout
        </d-button>
      </div>
    </d-aside>

    <d-content class="content">
      <SessionManager v-if="currentView === 'sessions'" />
      <PersonaManager v-if="currentView === 'personas'" />
      <APIProfileManager v-if="currentView === 'profiles'" />
      <DebugPage v-if="currentView === 'debug'" />
    </d-content>
  </d-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { authState, logout } from '../api';
import SessionManager from './SessionManager.vue';
import PersonaManager from './PersonaManager.vue';
import APIProfileManager from './APIProfileManager.vue';
import DebugPage from '../pages/DebugPage.vue';

const currentView = ref('sessions');

const username = computed(() => authState.username);

const onMenuSelect = (key: string) => {
  currentView.value = key;
};

const handleLogout = () => {
  logout();
};
</script>

<style scoped>
.main-layout {
  height: 100vh;
  width: 100vw;
}

.sidebar {
  background: #f8f9fa;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  padding: 1rem 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0 1.5rem 1.5rem;
  border-bottom: 1px solid #eee;
  margin-bottom: 1rem;
}

.details .name {
  font-weight: bold;
  color: #333;
}

.details .tenant {
  font-size: 0.8rem;
  color: #888;
}

.footer {
  margin-top: auto;
  padding: 1rem;
  border-top: 1px solid #eee;
}

.content {
  background: #fff;
  overflow: hidden;
}
</style>
