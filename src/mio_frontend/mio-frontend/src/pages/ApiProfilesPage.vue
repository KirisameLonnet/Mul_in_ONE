<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">{{ t('apiProfiles.title') }}</div>
      <div>
        <q-btn color="primary" icon="refresh" flat @click="loadProfiles" class="q-mr-sm" />
        <q-btn color="primary" icon="add" :label="t('apiProfiles.new')" @click="openCreateDialog" />
      </div>
    </div>

    <q-table
      :rows="profiles"
      :columns="columns"
      row-key="id"
      :loading="loading"
    >
      <template v-slot:body-cell-api_key="props">
        <q-td :props="props">
          {{ props.row.api_key_preview }}
        </q-td>
      </template>
      <template v-slot:body-cell-actions="props">
        <q-td :props="props" class="text-right">
          <q-btn dense flat icon="edit" @click="openEditDialog(props.row)" />
          <q-btn dense flat icon="delete" color="negative" @click="openDeleteDialog(props.row)" />
          <q-btn dense flat icon="health_and_safety" color="positive" class="q-ml-sm" @click="serverHealthCheck(props.row)" />
          <q-chip v-if="healthStatus[props.row.id]" :color="healthStatus[props.row.id]?.status === 'OK' ? 'positive' : 'negative'" text-color="white" dense class="q-ml-sm">
            {{ healthStatus[props.row.id]?.status }}
          </q-chip>
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="createDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">{{ t('apiProfiles.createDialog.title') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="handleCreate" class="q-gutter-md">
            <q-input v-model="newProfile.name" :label="t('apiProfiles.createDialog.name')" :rules="[val => !!val || t('common.required')]" />
            <q-input v-model="newProfile.base_url" :label="t('apiProfiles.createDialog.baseUrl')" :rules="[val => !!val || t('common.required')]" />
            <q-input v-model="newProfile.model" :label="t('apiProfiles.createDialog.model')" :rules="[val => !!val || t('common.required')]" />
            <q-input v-model="newProfile.api_key" :label="t('apiProfiles.createDialog.apiKey')" type="password" :rules="[val => !!val || t('common.required')]" />
            <q-input v-model.number="newProfile.temperature" type="number" :label="t('apiProfiles.createDialog.temperature')" step="0.1" min="0" max="2" />
            
            <q-separator />
            <div class="text-subtitle2 text-grey-7">{{ t('apiProfiles.embedding.title') }}</div>
            <q-checkbox v-model="newProfile.is_embedding_model" :label="t('apiProfiles.embedding.supportEmbedding')" />
            <q-input 
              v-model.number="newProfile.embedding_dim" 
              type="number" 
              :label="t('apiProfiles.embedding.maxDim')" 
              :hint="t('apiProfiles.embedding.hint')"
              :disable="!newProfile.is_embedding_model"
              :rules="[val => !newProfile.is_embedding_model || (val && val >= 32 && val <= 8192) || t('apiProfiles.embedding.dimRange')]"
            />
            <div v-if="newProfile.is_embedding_model" class="text-caption text-grey-6 q-mt-sm">
              💡 {{ t('apiProfiles.embedding.tip', { dim: newProfile.embedding_dim || 4096 }) }}
            </div>
            
            <div align="right">
              <q-btn flat :label="t('common.cancel')" color="primary" v-close-popup />
              <q-btn flat :label="t('common.create')" type="submit" color="primary" :loading="creating" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="editDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">{{ t('apiProfiles.editDialog.title') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="handleUpdate" class="q-gutter-md">
            <q-input v-model="editProfile.name" :label="t('apiProfiles.createDialog.name')" :rules="[val => !!val || t('common.required')]" />
            <q-input v-model="editProfile.base_url" :label="t('apiProfiles.createDialog.baseUrl')" :rules="[val => !!val || t('common.required')]" />
            <q-input v-model="editProfile.model" :label="t('apiProfiles.createDialog.model')" :rules="[val => !!val || t('common.required')]" />
            <q-input v-model.number="editProfile.temperature" type="number" :label="t('apiProfiles.createDialog.temperature')" step="0.1" min="0" max="2" />
            <q-input v-model="editProfile.api_key" :label="t('apiProfiles.editDialog.apiKey')" type="password" />

            <q-separator />
            <div class="text-subtitle2 text-grey-7">{{ t('apiProfiles.embedding.title') }}</div>
            <q-checkbox v-model="editProfile.is_embedding_model" :label="t('apiProfiles.embedding.supportEmbedding')" />
            <q-input 
              v-model.number="editProfile.embedding_dim" 
              type="number" 
              :label="t('apiProfiles.embedding.maxDim')" 
              :hint="t('apiProfiles.embedding.hint')"
              :disable="!editProfile.is_embedding_model"
              :rules="[val => !editProfile.is_embedding_model || (val && val >= 32 && val <= 8192) || t('apiProfiles.embedding.dimRange')]"
            />
            <div v-if="editProfile.is_embedding_model" class="text-caption text-grey-6 q-mt-sm">
              💡 {{ t('apiProfiles.embedding.tip', { dim: editProfile.embedding_dim || 4096 }) }}
            </div>

            <div align="right">
              <q-btn flat :label="t('common.cancel')" color="primary" v-close-popup />
              <q-btn flat :label="t('common.save')" type="submit" color="primary" :loading="updating" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialog">
      <q-card>
        <q-card-section class="text-h6">
          {{ t('apiProfiles.deleteDialog.title') }}
        </q-card-section>
        <q-card-section>
          {{ t('apiProfiles.deleteDialog.body', { name: selectedProfile?.name }) }}
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" color="primary" v-close-popup />
          <q-btn flat :label="t('common.delete')" color="negative" @click="handleDelete" :loading="deleting" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useQuasar } from 'quasar'
import { api, getAPIProfiles, createAPIProfile, updateAPIProfile, deleteAPIProfile, type APIProfile, type UpdateAPIProfilePayload, authState } from '../api'
import { useI18n } from 'vue-i18n'

const $q = useQuasar()
const { t } = useI18n()
const profiles = ref<APIProfile[]>([])
const loading = ref(false)
const creating = ref(false)
const createDialog = ref(false)
const editDialog = ref(false)
const deleteDialog = ref(false)
const updating = ref(false)
const deleting = ref(false)
const selectedProfile = ref<APIProfile | null>(null)
const healthStatus = ref<Record<number, { status: string; provider_status?: number; detail?: string }>>({})

const newProfile = reactive({
  name: '',
  base_url: '',
  model: '',
  api_key: '',
  temperature: 0.7,
  is_embedding_model: false,
  embedding_dim: null as number | null
})

const editProfile = reactive({
  id: 0,
  name: '',
  base_url: '',
  model: '',
  temperature: 0.7,
  api_key: '',
  is_embedding_model: false,
  embedding_dim: null as number | null
})

const columns = computed(() => [
  { name: 'id', label: t('apiProfiles.columns.id'), field: 'id', sortable: true },
  { name: 'name', label: t('apiProfiles.columns.name'), field: 'name', sortable: true },
  { name: 'base_url', label: t('apiProfiles.columns.baseUrl'), field: 'base_url' },
  { name: 'model', label: t('apiProfiles.columns.model'), field: 'model' },
  { name: 'api_key', label: t('apiProfiles.columns.apiKeyPreview'), field: 'api_key_preview' },
  { name: 'temperature', label: t('apiProfiles.columns.temperature'), field: 'temperature' },
  { name: 'actions', label: t('common.actions'), field: 'actions', align: 'right' as const }
])

const loadProfiles = async () => {
  loading.value = true
  try {
    profiles.value = await getAPIProfiles(authState.username)
  } catch (e) {
    $q.notify({ type: 'negative', message: t('apiProfiles.notify.loadFailed') })
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  createDialog.value = true
}

const openEditDialog = (profile: APIProfile) => {
  selectedProfile.value = profile
  editProfile.id = profile.id
  editProfile.name = profile.name
  editProfile.base_url = profile.base_url
  editProfile.model = profile.model
  editProfile.temperature = profile.temperature ?? 0.7
  editProfile.api_key = ''
  editProfile.is_embedding_model = profile.is_embedding_model ?? false
  editProfile.embedding_dim = profile.embedding_dim ?? null
  editDialog.value = true
}

const openDeleteDialog = (profile: APIProfile) => {
  selectedProfile.value = profile
  deleteDialog.value = true
}

const handleCreate = async () => {
  creating.value = true
  try {
    await createAPIProfile({
      username: authState.username,
      name: newProfile.name,
      base_url: newProfile.base_url,
      model: newProfile.model,
      api_key: newProfile.api_key,
      temperature: newProfile.temperature,
      is_embedding_model: newProfile.is_embedding_model,
      embedding_dim: newProfile.embedding_dim
    })
    createDialog.value = false
    $q.notify({ type: 'positive', message: t('apiProfiles.notify.createSuccess') })
    loadProfiles()
  } catch (e) {
    $q.notify({ type: 'negative', message: t('apiProfiles.notify.createFailed') })
  } finally {
    creating.value = false
  }
}

const handleUpdate = async () => {
  if (!selectedProfile.value) return
  updating.value = true
  try {
    const payload: UpdateAPIProfilePayload = {
      username: authState.username,
      name: editProfile.name,
      base_url: editProfile.base_url,
      model: editProfile.model,
      temperature: editProfile.temperature,
      is_embedding_model: editProfile.is_embedding_model,
      embedding_dim: editProfile.embedding_dim
    }
    if (editProfile.api_key) {
      payload.api_key = editProfile.api_key
    }
    await updateAPIProfile(editProfile.id, payload)
    editDialog.value = false
    $q.notify({ type: 'positive', message: t('apiProfiles.notify.updateSuccess') })
    loadProfiles()
  } catch (e) {
    $q.notify({ type: 'negative', message: t('apiProfiles.notify.updateFailed') })
  } finally {
    updating.value = false
  }
}

const handleDelete = async () => {
  if (!selectedProfile.value) return
  deleting.value = true
  try {
    await deleteAPIProfile(authState.username, selectedProfile.value.id)
    deleteDialog.value = false
    $q.notify({ type: 'positive', message: t('apiProfiles.notify.deleteSuccess') })
    loadProfiles()
  } catch (e: any) {
    const errorMsg = e?.response?.data?.detail || e?.message || String(e)
    console.error('Delete profile error:', errorMsg, e)
    $q.notify({ 
      type: 'negative', 
      message: t('apiProfiles.notify.deleteFailed'),
      caption: errorMsg 
    })
  } finally {
    deleting.value = false
  }
}

// 后端健康检查（避免前端 CORS 问题）
const serverHealthCheck = async (profile: APIProfile) => {
  $q.notify({ type: 'info', message: t('apiProfiles.notify.serverChecking', { name: profile.name }) })
  try {
    const { data } = await api.get(`/personas/api-profiles/${profile.id}/health`, {
      params: { username: authState.username }
    })
    healthStatus.value = {
      ...healthStatus.value,
      [profile.id]: data
    }
    if (data.status === 'OK') {
      $q.notify({ type: 'positive', message: t('apiProfiles.notify.serverHealthy', { status: data.provider_status ?? '' }) })
    } else {
      $q.notify({ type: 'warning', message: t('apiProfiles.notify.serverFailed', { reason: data.detail ? String(data.detail).slice(0, 200) : t('common.failed') }) })
    }
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || e
    $q.notify({ type: 'negative', message: t('apiProfiles.notify.serverCheckFailed', { detail: String(detail).slice(0, 200) }) })
  }
}

onMounted(loadProfiles)
</script>
