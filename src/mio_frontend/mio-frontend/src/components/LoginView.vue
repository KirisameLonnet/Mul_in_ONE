<template>
  <div class="login-container">
    <div class="login-card">
      <McIntroduction 
        :title="$t('login.title')" 
        :subTitle="$t('login.subtitle')"
        :description="[$t('login.description')]"
      />
      
      <div class="form-group">
        <d-input 
          v-model="username" 
          :placeholder="$t('login.usernamePlaceholder')" 
          @keyup.enter="handleLogin"
          size="lg"
        />
      </div>

      <d-button 
        variant="solid" 
        color="primary" 
        size="lg" 
        width="100%"
        :disabled="!username"
        @click="handleLogin"
      >
        {{ $t('login.enterApp') }}
      </d-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { login } from '../api';

const username = ref('');

const handleLogin = () => {
  if (!username.value) return;
  login(username.value);
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.login-card {
  background: white;
  padding: 3rem;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 480px;
  text-align: center;
}

.form-group {
  margin-bottom: 1.5rem;
  text-align: left;
}
</style>
