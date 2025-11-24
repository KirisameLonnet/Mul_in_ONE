<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">API Profiles</div>
      <div>
        <q-btn color="primary" icon="refresh" flat @click="loadProfiles" class="q-mr-sm" />
        <q-btn color="primary" icon="add" label="New Profile" @click="openCreateDialog" />
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
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="createDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Create New API Profile</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="handleCreate" class="q-gutter-md">
            <q-input v-model="newProfile.name" label="Name" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="newProfile.base_url" label="Base URL" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="newProfile.model" label="Model" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="newProfile.api_key" label="API Key" type="password" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model.number="newProfile.temperature" type="number" label="Temperature" step="0.1" min="0" max="2" />
            
            <div align="right">
              <q-btn flat label="Cancel" color="primary" v-close-popup />
              <q-btn flat label="Create" type="submit" color="primary" :loading="creating" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="editDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit API Profile</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="handleUpdate" class="q-gutter-md">
            <q-input v-model="editProfile.name" label="Name" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="editProfile.base_url" label="Base URL" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="editProfile.model" label="Model" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model.number="editProfile.temperature" type="number" label="Temperature" step="0.1" min="0" max="2" />
            <q-input v-model="editProfile.api_key" label="API Key (leave blank to keep)" type="password" />

            <div align="right">
              <q-btn flat label="Cancel" color="primary" v-close-popup />
              <q-btn flat label="Save" type="submit" color="primary" :loading="updating" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialog">
      <q-card>
        <q-card-section class="text-h6">
          Delete API Profile
        </q-card-section>
        <q-card-section>
          Are you sure you want to delete "{{ selectedProfile?.name }}"?
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn flat label="Delete" color="negative" @click="handleDelete" :loading="deleting" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useQuasar } from 'quasar'
import { getAPIProfiles, createAPIProfile, updateAPIProfile, deleteAPIProfile, type APIProfile, type UpdateAPIProfilePayload, authState } from '../api'

const $q = useQuasar()
const profiles = ref<APIProfile[]>([])
const loading = ref(false)
const creating = ref(false)
const createDialog = ref(false)
const editDialog = ref(false)
const deleteDialog = ref(false)
const updating = ref(false)
const deleting = ref(false)
const selectedProfile = ref<APIProfile | null>(null)

const newProfile = reactive({
  name: '',
  base_url: '',
  model: '',
  api_key: '',
  temperature: 0.7
})

const editProfile = reactive({
  id: 0,
  name: '',
  base_url: '',
  model: '',
  temperature: 0.7,
  api_key: ''
})

const columns = [
  { name: 'id', label: 'ID', field: 'id', sortable: true },
  { name: 'name', label: 'Name', field: 'name', sortable: true },
  { name: 'base_url', label: 'Base URL', field: 'base_url' },
  { name: 'model', label: 'Model', field: 'model' },
  { name: 'api_key', label: 'API Key (Preview)', field: 'api_key_preview' },
  { name: 'temperature', label: 'Temperature', field: 'temperature' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' }
]

const loadProfiles = async () => {
  loading.value = true
  try {
    profiles.value = await getAPIProfiles(authState.tenantId)
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to load profiles' })
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
      tenant_id: authState.tenantId,
      name: newProfile.name,
      base_url: newProfile.base_url,
      model: newProfile.model,
      api_key: newProfile.api_key,
      temperature: newProfile.temperature
    })
    createDialog.value = false
    $q.notify({ type: 'positive', message: 'Profile created' })
    loadProfiles()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to create profile' })
  } finally {
    creating.value = false
  }
}

const handleUpdate = async () => {
  if (!selectedProfile.value) return
  updating.value = true
  try {
    const payload: UpdateAPIProfilePayload = {
      tenant_id: authState.tenantId,
      name: editProfile.name,
      base_url: editProfile.base_url,
      model: editProfile.model,
      temperature: editProfile.temperature
    }
    if (editProfile.api_key) {
      payload.api_key = editProfile.api_key
    }
    await updateAPIProfile(editProfile.id, payload)
    editDialog.value = false
    $q.notify({ type: 'positive', message: 'Profile updated' })
    loadProfiles()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to update profile' })
  } finally {
    updating.value = false
  }
}

const handleDelete = async () => {
  if (!selectedProfile.value) return
  deleting.value = true
  try {
    await deleteAPIProfile(authState.tenantId, selectedProfile.value.id)
    deleteDialog.value = false
    $q.notify({ type: 'positive', message: 'Profile deleted' })
    loadProfiles()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to delete profile' })
  } finally {
    deleting.value = false
  }
}

onMounted(loadProfiles)
</script>
