<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">Personas</div>
      <q-btn color="primary" icon="add" label="New Persona" @click="openCreateDialog" />
    </div>

    <q-table
      :rows="personas"
      :columns="columns"
      row-key="id"
      :loading="loading"
    >
      <template v-slot:body-cell-handle="props">
        <q-td :props="props">
          <q-chip color="primary" text-color="white" dense>@{{ props.value }}</q-chip>
        </q-td>
      </template>
      <template v-slot:body-cell-api_profile="props">
        <q-td :props="props">
          {{ props.row.api_profile_name || '-' }}
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="createDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Create New Persona</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="handleCreate" class="q-gutter-md">
            <q-input v-model="newPersona.name" label="Name" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="newPersona.handle" label="Handle" prefix="@" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="newPersona.tone" label="Tone" />
            <q-input v-model.number="newPersona.proactivity" type="number" label="Proactivity (0-1)" step="0.1" min="0" max="1" />
            <q-select 
              v-model="newPersona.api_profile_id" 
              :options="apiProfiles" 
              option-value="id" 
              option-label="name" 
              label="API Profile" 
              emit-value 
              map-options 
            />
            <q-input v-model="newPersona.prompt" type="textarea" label="System Prompt" :rules="[val => !!val || 'Field is required']" />
            <q-checkbox v-model="newPersona.is_default" label="Set as Default" />
            
            <div align="right">
              <q-btn flat label="Cancel" color="primary" v-close-popup />
              <q-btn flat label="Create" type="submit" color="primary" :loading="creating" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useQuasar } from 'quasar'
import { getPersonas, createPersona, getAPIProfiles, type Persona, type APIProfile, authState } from '../api'

const $q = useQuasar()
const personas = ref<Persona[]>([])
const apiProfiles = ref<APIProfile[]>([])
const loading = ref(false)
const creating = ref(false)
const createDialog = ref(false)

const newPersona = reactive({
  name: '',
  handle: '',
  prompt: '',
  tone: 'neutral',
  proactivity: 0.5,
  api_profile_id: null as number | null,
  is_default: false
})

const columns = [
  { name: 'id', label: 'ID', field: 'id', sortable: true },
  { name: 'name', label: 'Name', field: 'name', sortable: true },
  { name: 'handle', label: 'Handle', field: 'handle', sortable: true },
  { name: 'tone', label: 'Tone', field: 'tone' },
  { name: 'proactivity', label: 'Proactivity', field: 'proactivity' },
  { name: 'api_profile', label: 'API Profile', field: 'api_profile_name' }
]

const loadData = async () => {
  loading.value = true
  try {
    const [pData, apData] = await Promise.all([
      getPersonas(authState.tenantId),
      getAPIProfiles(authState.tenantId)
    ])
    personas.value = pData
    apiProfiles.value = apData
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to load data' })
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  createDialog.value = true
}

const handleCreate = async () => {
  creating.value = true
  try {
    await createPersona({
      tenant_id: authState.tenantId,
      name: newPersona.name,
      handle: newPersona.handle,
      prompt: newPersona.prompt,
      tone: newPersona.tone,
      proactivity: newPersona.proactivity,
      api_profile_id: newPersona.api_profile_id || undefined,
      is_default: newPersona.is_default
    })
    createDialog.value = false
    $q.notify({ type: 'positive', message: 'Persona created' })
    loadData()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to create persona' })
  } finally {
    creating.value = false
  }
}

onMounted(loadData)
</script>
