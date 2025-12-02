<template>
  <div class="manager-container">
    <div class="header">
      <h2>{{ $t('apiProfiles.title') }}</h2>
    </div>
    
    <div class="content-wrapper">
      <!-- Create Form -->
      <d-card class="create-card">
        <template #header>{{ $t('apiProfiles.createDialog.title') }}</template>
        <d-form layout="vertical">
          <d-form-item :label="$t('apiProfiles.createDialog.name')">
            <d-input v-model="newProfile.name" placeholder="e.g. GPT-4" />
          </d-form-item>
          
          <d-form-item :label="$t('apiProfiles.createDialog.baseUrl')">
            <d-input v-model="newProfile.base_url" placeholder="https://api.openai.com/v1" />
          </d-form-item>
          
          <d-form-item :label="$t('apiProfiles.createDialog.model')">
            <d-input v-model="newProfile.model" placeholder="gpt-4" />
          </d-form-item>
          
          <d-form-item :label="$t('apiProfiles.createDialog.apiKey')">
            <d-input v-model="newProfile.api_key" type="password" placeholder="sk-..." />
          </d-form-item>
          
          <d-form-item :label="$t('apiProfiles.createDialog.temperature')">
            <d-input-number v-model="newProfile.temperature" :step="0.1" :min="0" :max="2" />
          </d-form-item>
          
          <d-form-item>
            <d-button variant="solid" color="primary" @click="handleCreate" :disabled="!isValid">{{ $t('apiProfiles.createDialog.create') }}</d-button>
          </d-form-item>
        </d-form>
      </d-card>

      <!-- List -->
      <div class="list-section">
        <h3>{{ $t('apiProfiles.listTitle') }}</h3>
        <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>
        <div v-else class="profile-grid">
          <d-card v-for="profile in profiles" :key="profile.id" class="profile-card">
            <template #header>
              <div class="card-header">
                <span class="name">{{ profile.name }}</span>
                <d-tag type="primary" variant="outline">{{ profile.model }}</d-tag>
              </div>
            </template>
            <div class="card-content">
              <div class="info-row">
                <span class="label">{{ $t('apiProfiles.columns.baseUrl') }}:</span>
                <span class="value">{{ profile.base_url }}</span>
              </div>
              <div class="info-row">
                <span class="label">{{ $t('apiProfiles.columns.apiKeyPreview') }}:</span>
                <span class="value code">{{ profile.api_key_preview }}</span>
              </div>
              <div class="info-row">
                <span class="label">{{ $t('apiProfiles.columns.temperature') }}:</span>
                <span class="value">{{ profile.temperature }}</span>
              </div>
            </div>
          </d-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { getAPIProfiles, createAPIProfile, type APIProfile, authState } from '../api';

const profiles = ref<APIProfile[]>([]);
const loading = ref(false);
const { t } = useI18n();

const newProfile = reactive({
  name: '',
  base_url: '',
  model: '',
  api_key: '',
  temperature: 0.4
});

const isValid = computed(() => {
  return newProfile.name && newProfile.base_url && newProfile.model && newProfile.api_key;
});

const loadProfiles = async () => {
  loading.value = true;
  try {
    profiles.value = await getAPIProfiles(authState.username);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const handleCreate = async () => {
  if (!isValid.value) return;
  try {
    await createAPIProfile({
      username: authState.username,
      ...newProfile
    });
    // Reset form
    newProfile.name = '';
    newProfile.base_url = '';
    newProfile.model = '';
    newProfile.api_key = '';
    newProfile.temperature = 0.4;
    
    await loadProfiles();
  } catch (e) {
    alert(t('apiProfiles.notify.createFailed'));
    console.error(e);
  }
};

onMounted(loadProfiles);
</script>

<style scoped>
.manager-container {
  padding: 1rem;
  height: 100%;
  overflow-y: auto;
}

.header {
  margin-bottom: 1.5rem;
}

.content-wrapper {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
  align-items: start;
}

.create-card {
  position: sticky;
  top: 0;
}

.list-section h3 {
  margin-bottom: 1rem;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-weight: bold;
  font-size: 1.1em;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
}

.label {
  color: #666;
}

.value {
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.value.code {
  font-family: monospace;
  background: #f5f5f5;
  padding: 2px 4px;
  border-radius: 4px;
}

@media (max-width: 1024px) {
  .content-wrapper {
    grid-template-columns: 1fr;
  }
  
  .create-card {
    position: static;
  }
}
</style>
