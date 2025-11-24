<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">Personas</div>
      <div>
        <q-btn color="primary" icon="refresh" flat class="q-mr-sm" @click="loadData" />
        <q-btn color="primary" icon="add" label="New Persona" @click="openCreateDialog" />
      </div>
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
          <div class="text-h6">Create New Persona</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="handleCreate" class="q-gutter-md">
            <q-input v-model="newPersona.name" label="Name" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="newPersona.handle" label="Handle" prefix="@" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="newPersona.tone" label="Tone" />
            <q-input v-model.number="newPersona.proactivity" type="number" label="Proactivity (0-1)" step="0.1" min="0" max="1" />
            <q-input v-model.number="newPersona.memory_window" type="number" label="Memory Window" min="1" max="200" />
            <q-input v-model.number="newPersona.max_agents_per_turn" type="number" label="Max Agents/Turn" min="1" max="8" />
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

    <q-dialog v-model="editDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Persona</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="handleUpdate" class="q-gutter-md">
            <q-input v-model="editPersona.name" label="Name" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="editPersona.handle" label="Handle" prefix="@" :rules="[val => !!val || 'Field is required']" />
            <q-input v-model="editPersona.tone" label="Tone" />
            <q-input v-model.number="editPersona.proactivity" type="number" label="Proactivity (0-1)" step="0.1" min="0" max="1" />
            <q-input v-model.number="editPersona.memory_window" type="number" label="Memory Window" min="1" max="200" />
            <q-input v-model.number="editPersona.max_agents_per_turn" type="number" label="Max Agents/Turn" min="1" max="8" />
            <q-select 
              v-model="editPersona.api_profile_id" 
              :options="apiProfiles" 
              option-value="id" 
              option-label="name" 
              label="API Profile" 
              emit-value 
              map-options 
              clearable
            />
            <q-input v-model="editPersona.prompt" type="textarea" label="System Prompt" :rules="[val => !!val || 'Field is required']" />
            <q-checkbox v-model="editPersona.is_default" label="Set as Default" />

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
        <q-card-section class="text-h6">Delete Persona</q-card-section>
        <q-card-section>
          Are you sure you want to delete "{{ selectedPersona?.name }}"?
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
import { getPersonas, createPersona, updatePersona, deletePersona, getAPIProfiles, type Persona, type APIProfile, type UpdatePersonaPayload, authState } from '../api'

const $q = useQuasar()
const personas = ref<Persona[]>([])
const apiProfiles = ref<APIProfile[]>([])
const loading = ref(false)
const creating = ref(false)
const createDialog = ref(false)
const editDialog = ref(false)
const deleteDialog = ref(false)
const updating = ref(false)
const deleting = ref(false)
const selectedPersona = ref<Persona | null>(null)

const newPersona = reactive({
  name: '',
  handle: '',
  prompt: '',
  tone: 'neutral',
  proactivity: 0.5,
  memory_window: 8,
  max_agents_per_turn: 2,
  api_profile_id: null as number | null,
  is_default: false
})

const editPersona = reactive({
  id: 0,
  name: '',
  handle: '',
  prompt: '',
  tone: 'neutral',
  proactivity: 0.5,
  memory_window: 8,
  max_agents_per_turn: 2,
  api_profile_id: null as number | null,
  is_default: false
})

const columns = [
  { name: 'id', label: 'ID', field: 'id', sortable: true },
  { name: 'name', label: 'Name', field: 'name', sortable: true },
  { name: 'handle', label: 'Handle', field: 'handle', sortable: true },
  { name: 'tone', label: 'Tone', field: 'tone' },
  { name: 'proactivity', label: 'Proactivity', field: 'proactivity' },
  { name: 'api_profile', label: 'API Profile', field: 'api_profile_name' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' }
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

const openEditDialog = (persona: Persona) => {
  selectedPersona.value = persona
  editPersona.id = persona.id
  editPersona.name = persona.name
  editPersona.handle = persona.handle
  editPersona.prompt = persona.prompt
  editPersona.tone = persona.tone
  editPersona.proactivity = persona.proactivity
  editPersona.memory_window = persona.memory_window
  editPersona.max_agents_per_turn = persona.max_agents_per_turn
  editPersona.api_profile_id = persona.api_profile_id ?? null
  editPersona.is_default = persona.is_default
  editDialog.value = true
}

const openDeleteDialog = (persona: Persona) => {
  selectedPersona.value = persona
  deleteDialog.value = true
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
      memory_window: newPersona.memory_window,
      max_agents_per_turn: newPersona.max_agents_per_turn,
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

const handleUpdate = async () => {
  if (!selectedPersona.value) return
  updating.value = true
  try {
    const payload: UpdatePersonaPayload = {
      tenant_id: authState.tenantId,
      name: editPersona.name,
      handle: editPersona.handle,
      prompt: editPersona.prompt,
      tone: editPersona.tone,
      proactivity: editPersona.proactivity,
      memory_window: editPersona.memory_window,
      max_agents_per_turn: editPersona.max_agents_per_turn,
      api_profile_id: editPersona.api_profile_id,
      is_default: editPersona.is_default
    }
    await updatePersona(editPersona.id, payload)
    editDialog.value = false
    $q.notify({ type: 'positive', message: 'Persona updated' })
    loadData()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to update persona' })
  } finally {
    updating.value = false
  }
}

const handleDelete = async () => {
  if (!selectedPersona.value) return
  deleting.value = true
  try {
    await deletePersona(authState.tenantId, selectedPersona.value.id)
    deleteDialog.value = false
    $q.notify({ type: 'positive', message: 'Persona deleted' })
    loadData()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to delete persona' })
  } finally {
    deleting.value = false
  }
}

onMounted(loadData)
</script>
