<template>
  <div class="manager-container">
    <div class="header">
      <h2>Persona Management</h2>
    </div>
    
    <div class="content-wrapper">
      <!-- Create Form -->
      <d-card class="create-card">
        <template #header>Create New Persona</template>
        <d-form layout="vertical">
          <d-form-item label="Name">
            <d-input v-model="newPersona.name" placeholder="e.g. Coding Assistant" />
          </d-form-item>
          
          <d-form-item label="Handle">
            <d-input v-model="newPersona.handle" placeholder="e.g. coder" />
          </d-form-item>
          
          <d-form-item label="Tone">
            <d-input v-model="newPersona.tone" placeholder="e.g. professional" />
          </d-form-item>
          
          <d-form-item label="Proactivity (0.0 - 1.0)">
            <d-input-number v-model="newPersona.proactivity" :step="0.1" :min="0" :max="1" />
          </d-form-item>
          
          <d-form-item label="API Profile">
            <d-select v-model="newPersona.api_profile_id" placeholder="Select API Profile">
              <d-option 
                v-for="p in apiProfiles" 
                :key="p.id" 
                :value="p.id"
                :label="`${p.name} (${p.model})`"
              />
            </d-select>
          </d-form-item>
          
          <d-form-item>
            <d-checkbox v-model="newPersona.is_default">Set as Default</d-checkbox>
          </d-form-item>
          
          <d-form-item label="System Prompt">
            <d-textarea v-model="newPersona.prompt" placeholder="Enter system prompt..." :rows="4" />
          </d-form-item>
          
          <d-form-item>
            <d-button variant="solid" color="primary" @click="handleCreate" :disabled="!isValid">Create Persona</d-button>
          </d-form-item>
        </d-form>
      </d-card>

      <!-- List -->
      <div class="list-section">
        <h3>Existing Personas</h3>
        <div v-if="loading" class="loading">Loading...</div>
        <div v-else class="persona-grid">
          <d-card v-for="persona in personas" :key="persona.id" class="persona-card">
            <template #header>
              <div class="card-header">
                <span class="name">{{ persona.name }}</span>
                <d-tag type="primary">@{{ persona.handle }}</d-tag>
              </div>
            </template>
            <div class="card-content">
              <p class="prompt">{{ persona.prompt }}</p>
              <div class="meta-tags">
                <d-tag type="info" variant="outline">Tone: {{ persona.tone }}</d-tag>
                <d-tag type="success" variant="outline">Proactivity: {{ persona.proactivity }}</d-tag>
                <d-tag v-if="persona.api_profile_name" type="warning" variant="outline">API: {{ persona.api_profile_name }}</d-tag>
              </div>
                <div class="card-actions">
                  <d-button 
                    size="sm" 
                    variant="outline" 
                    @click="handleRefreshRAG(persona.id)"
                    :loading="refreshingPersonaId === persona.id"
                  >
                    刷新资料库
                  </d-button>
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
import { getPersonas, createPersona, getAPIProfiles, type Persona, type APIProfile, authState } from '../api';

const personas = ref<Persona[]>([]);
const apiProfiles = ref<APIProfile[]>([]);
const loading = ref(false);
const refreshingPersonaId = ref<number | null>(null);

const newPersona = reactive({
  name: '',
  handle: '',
  prompt: '',
  tone: 'neutral',
  proactivity: 0.5,
  api_profile_id: undefined as number | undefined,
  is_default: false
});

const isValid = computed(() => {
  return newPersona.name && newPersona.prompt && newPersona.handle;
});

const loadData = async () => {
  loading.value = true;
  try {
    const [pData, apiData] = await Promise.all([
      getPersonas(authState.username),
      getAPIProfiles(authState.username)
    ]);
    personas.value = pData;
    apiProfiles.value = apiData;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const handleCreate = async () => {
  if (!isValid.value) return;
  try {
    await createPersona({
      username: authState.username,
      ...newPersona
    });
    // Reset form
    newPersona.name = '';
    newPersona.handle = '';
    newPersona.prompt = '';
    newPersona.tone = 'neutral';
    newPersona.proactivity = 0.5;
    newPersona.api_profile_id = undefined;
    newPersona.is_default = false;
    
    await loadData();
  } catch (e) {
    alert('Failed to create persona');
    console.error(e);
  }
};

onMounted(loadData);
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

const handleRefreshRAG = async (personaId: number) => {
  refreshingPersonaId.value = personaId;
  try {
    const response = await fetch(
      `http://localhost:8000/api/personas/personas/${personaId}/refresh_rag?username=${authState.username}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to refresh RAG');
    }
    
    const result = await response.json();
    alert(`成功刷新！摄取了 ${result.documents_added} 个文档片段到 ${result.collection_name}`);
  } catch (e: any) {
    alert(`刷新失败：${e.message}`);
    console.error(e);
  } finally {
    refreshingPersonaId.value = null;
  }
};

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

.persona-grid {
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
  gap: 1rem;
}

.prompt {
  color: #666;
  font-size: 0.9em;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

  .card-actions {
    margin-top: 0.5rem;
    display: flex;
    gap: 0.5rem;
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
