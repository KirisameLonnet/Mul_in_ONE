<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">Personas</div>
      <div class="row items-center q-gutter-sm">
        <q-btn 
          color="secondary" 
          icon="storage" 
          label="构建向量数据库" 
          flat 
          class="q-mr-sm" 
          @click="buildVectorDatabase"
          :loading="buildingVectorDB"
        />
        <q-btn color="primary" icon="add" label="New Persona" @click="openCreateDialog" />
      </div>
    </div>

    <!-- Embedding Config Section -->
    <q-card class="q-mb-md" :class="$q.dark.isActive ? 'bg-grey-9' : 'bg-amber-1'">
      <q-card-section>
        <div class="text-h6 q-mb-sm">
          <q-icon name="settings" class="q-mr-sm" />
          全局 Embedding 模型配置
        </div>
        <div class="text-caption text-grey-7 q-mb-md">
          ⚠️ 使用人物背景传记功能（RAG）需要配置一个 Embedding 模型。此配置对所有 Persona 生效。
        </div>
        <div class="row items-start q-gutter-md">
          <q-select
            v-model="embeddingProfileId"
            :options="apiProfiles.filter(p => p.is_embedding_model)"
            option-value="id"
            option-label="name"
            label="Embedding API Profile"
            emit-value
            map-options
            clearable
            style="min-width: 300px"
            hint="只显示标记为 Embedding 模型的 API Profile"
          >
            <template v-slot:option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.name }}</q-item-label>
                  <q-item-label caption>{{ scope.opt.model }} (最大维度: {{ scope.opt.embedding_dim || 'N/A' }})</q-item-label>
                </q-item-section>
              </q-item>
            </template>
          </q-select>
          <q-input
            v-model.number="actualEmbeddingDim"
            type="number"
            label="实际使用维度"
            hint="留空使用最大维度"
            style="width: 160px"
            :disable="!embeddingProfileId"
            :rules="[val => !val || (val >= 32 && val <= (selectedEmbeddingProfile?.embedding_dim || 8192)) || `范围：32-${selectedEmbeddingProfile?.embedding_dim || 8192}`]"
          />
          <q-btn 
            color="primary" 
            label="保存配置" 
            @click="saveEmbeddingConfig"
            :loading="savingEmbeddingConfig"
          />
          <div v-if="currentEmbeddingModel" class="text-body2">
            当前模型: <q-chip dense>{{ currentEmbeddingModel }}</q-chip>
          </div>
        </div>
      </q-card-section>
    </q-card>

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
            <q-input
              v-model.number="newPersona.memory_window"
              type="number"
              label="Memory Window (-1 = Unlimited)"
              :rules="[val => val === -1 || val >= 1 || '必须为 -1 或 ≥ 1']"
            />
            <q-input
              v-model.number="newPersona.max_agents_per_turn"
              type="number"
              label="Max Agents/Turn (-1 = Unlimited)"
              :rules="[val => val === -1 || val >= 1 || '必须为 -1 或 ≥ 1']"
            />
            <q-select 
              v-model="newPersona.api_profile_id" 
              :options="apiProfiles" 
              option-value="id" 
              option-label="name" 
              label="API Profile" 
              emit-value 
              map-options 
            />
              <q-input v-model="newPersona.background" type="textarea" autogrow label="Background / Biography (任意长度)" />
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
            <q-input
              v-model.number="editPersona.memory_window"
              type="number"
              label="Memory Window (-1 = Unlimited)"
              :rules="[val => val === -1 || val >= 1 || '必须为 -1 或 ≥ 1']"
            />
            <q-input
              v-model.number="editPersona.max_agents_per_turn"
              type="number"
              label="Max Agents/Turn (-1 = Unlimited)"
              :rules="[val => val === -1 || val >= 1 || '必须为 -1 或 ≥ 1']"
            />
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
              <q-input v-model="editPersona.background" type="textarea" autogrow label="Background / Biography (任意长度)" />
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

    <!-- Build Vector DB Progress Dialog -->
    <q-dialog v-model="buildProgressDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">正在构建向量数据库</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-body2 q-mb-md">
            正在为所有 Persona 的背景资料生成向量索引...
          </div>
          <q-linear-progress 
            :value="buildProgress / 100" 
            size="20px"
            color="secondary"
            stripe
            rounded
          >
            <div class="absolute-full flex flex-center">
              <q-badge color="white" text-color="secondary" :label="`${buildProgress}%`" />
            </div>
          </q-linear-progress>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useQuasar } from 'quasar'
import { getPersonas, createPersona, updatePersona, deletePersona, getAPIProfiles, type Persona, type APIProfile, type UpdatePersonaPayload, authState } from '../api'

// Quasar instance
const $q = useQuasar()

// Table and data state
const loading = ref(false)
const personas = ref<Persona[]>([])
const apiProfiles = ref<APIProfile[]>([])
const creating = ref(false)
const createDialog = ref(false)
const editDialog = ref(false)
const deleteDialog = ref(false)
const updating = ref(false)
const deleting = ref(false)
const selectedPersona = ref<Persona | null>(null)

// Embedding config state
const embeddingProfileId = ref<number | null>(null)
const currentEmbeddingModel = ref<string>('')
const savingEmbeddingConfig = ref(false)
const actualEmbeddingDim = ref<number | null>(null)

// Computed: currently selected embedding profile
const selectedEmbeddingProfile = computed(() => {
  return apiProfiles.value.find(p => p.id === embeddingProfileId.value)
})

// Vector DB build state
const buildingVectorDB = ref(false)
const buildProgress = ref(0)
const buildProgressDialog = ref(false)

const newPersona = reactive({
  name: '',
  handle: '',
  prompt: '',
  background: '',
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
  background: '',
  tone: 'neutral',
  proactivity: 0.5,
  memory_window: 8,
  max_agents_per_turn: 2,
  api_profile_id: null as number | null,
  is_default: false
})

const columns = [
  { name: 'name', label: 'Name', field: 'name', sortable: true },
  { name: 'handle', label: 'Handle', field: 'handle', sortable: true },
  { name: 'tone', label: 'Tone', field: 'tone' },
  { name: 'proactivity', label: 'Proactivity', field: 'proactivity' },
  { name: 'api_profile', label: 'API Profile', field: 'api_profile_name' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' as const }
]

const loadData = async () => {
  loading.value = true
  try {
    const [pData, apData] = await Promise.all([
      getPersonas(authState.username),
      getAPIProfiles(authState.username)
    ])
    personas.value = pData
    apiProfiles.value = apData
    // Load current embedding config
    await loadEmbeddingConfig()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to load data' })
  } finally {
    loading.value = false
  }
}

const loadEmbeddingConfig = async () => {
  try {
    const response = await fetch(`/api/personas/embedding-config?username=${authState.username}`)
    if (response.ok) {
      const data = await response.json()
      if (data.api_profile_id) {
        embeddingProfileId.value = data.api_profile_id
        currentEmbeddingModel.value = data.api_model || ''
      }
    }
  } catch (e) {
    console.error('Failed to load embedding config:', e)
  }
}

const saveEmbeddingConfig = async () => {
  savingEmbeddingConfig.value = true
  try {
    const response = await fetch(`/api/personas/embedding-config?username=${authState.username}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_profile_id: embeddingProfileId.value
      })
    })
    if (response.ok) {
      $q.notify({ type: 'positive', message: 'Embedding 配置已保存' })
      await loadEmbeddingConfig()
    } else {
      const error = await response.json()
      $q.notify({ type: 'negative', message: error.detail || '保存配置失败' })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: '保存配置失败' })
  } finally {
    savingEmbeddingConfig.value = false
  }
}

const buildVectorDatabase = async () => {
  if (!embeddingProfileId.value) {
    $q.notify({ 
      type: 'warning', 
      message: '请先配置 Embedding 模型',
      caption: '向量数据库需要 embedding 模型来生成文档向量'
    })
    return
  }

  // Use actualEmbeddingDim if specified, otherwise fall back to profile's max dimension
  const embeddingProfile = apiProfiles.value.find(p => p.id === embeddingProfileId.value)
  const expectedDim = actualEmbeddingDim.value || embeddingProfile?.embedding_dim

  buildingVectorDB.value = true
  buildProgress.value = 0
  buildProgressDialog.value = true

  try {
    const url = new URL(`/api/personas/build-vector-db`, window.location.origin)
    url.searchParams.set('username', authState.username)
    if (expectedDim) {
      url.searchParams.set('expected_dim', String(expectedDim))
    }
    
    const response = await fetch(url.toString(), { method: 'POST' })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    if (!response.body) {
      throw new Error('Response body is null')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep the last incomplete line in buffer
      
      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const data = JSON.parse(line)
          if (data.progress !== undefined) {
            buildProgress.value = data.progress
          }
          
          // Handle completion
          if (data.status === 'completed' || data.status === 'completed_with_errors') {
            const details = data.details || {}
            const errors = details.errors || []
            
            const notifyType = errors.length > 0 ? 'warning' : 'positive'
            const message = errors.length > 0 
              ? `完成，但有 ${errors.length} 个错误`
              : '向量数据库构建成功'
            
            $q.notify({ 
              type: notifyType, 
              message,
              caption: `处理了 ${details.processed} 个 Persona，共 ${details.docs} 个文档`,
              timeout: 3000
            })

            if (errors.length > 0) {
              console.error('Build errors:', errors)
              $q.notify({
                type: 'info',
                message: '查看控制台以获取详细错误信息',
                timeout: 2000
              })
            }
          } else if (data.status === 'failed') {
             throw new Error(data.error || 'Unknown error')
          }
        } catch (e) {
          console.warn('Failed to parse progress line:', line, e)
        }
      }
    }
  } catch (e) {
    console.error('Build vector DB error:', e)
    $q.notify({ 
      type: 'negative', 
      message: '构建向量数据库时发生错误',
      caption: String(e)
    })
  } finally {
    buildingVectorDB.value = false
    setTimeout(() => {
      buildProgressDialog.value = false
    }, 1500)
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
  editPersona.background = (persona as any).background || ''
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
      username: authState.username,
      name: newPersona.name,
      handle: newPersona.handle,
      prompt: newPersona.prompt,
      background: newPersona.background || undefined,
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
      username: authState.username,
      name: editPersona.name,
      handle: editPersona.handle,
      prompt: editPersona.prompt,
      background: editPersona.background || undefined,
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
    await deletePersona(authState.username, selectedPersona.value.id)
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
