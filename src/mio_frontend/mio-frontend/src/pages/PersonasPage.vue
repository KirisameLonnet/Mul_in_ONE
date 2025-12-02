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
      <template v-slot:body-cell-avatar="props">
        <q-td :props="props">
          <q-avatar size="32px" :color="getAvatarColor(props.row)" text-color="white">
            <img v-if="props.row.avatar_path" :src="getAvatarSrc(props.row.avatar_path, props.row.id)" alt="avatar" @error="props.row.avatar_path = ''" />
            <span v-else>{{ props.row.name.charAt(0) }}</span>
          </q-avatar>
        </q-td>
      </template>
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
            <div class="row items-center q-col-gutter-sm">
              <div class="col-auto">
                <q-avatar size="42px" :color="getAvatarColor({ name: newPersona.name, handle: newPersona.handle } as Persona)" text-color="white">
                  <img v-if="newPersona.avatar_path" :src="getAvatarSrc(newPersona.avatar_path)" alt="avatar preview" @error="newPersona.avatar_path = ''" />
                  <span v-else>{{ newPersona.name ? newPersona.name.charAt(0) : 'P' }}</span>
                </q-avatar>
              </div>
              <div class="col-auto">
                <q-btn
                  outline
                  color="primary"
                  icon="photo_camera"
                  label="Avatar"
                  @click="openAvatarDialog('create')"
                />
              </div>
            </div>
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
            <div class="row items-center q-col-gutter-sm">
              <div class="col-auto">
                <q-avatar size="42px" :color="getAvatarColor(editPersona as unknown as Persona)" text-color="white">
                  <img v-if="editPersona.avatar_path" :src="getAvatarSrc(editPersona.avatar_path, editPersona.id)" alt="avatar preview" @error="editPersona.avatar_path = ''" />
                  <span v-else>{{ editPersona.name ? editPersona.name.charAt(0) : 'P' }}</span>
                </q-avatar>
              </div>
              <div class="col-auto">
                <q-btn
                  outline
                  color="primary"
                  icon="photo_camera"
                  label="Avatar"
                  @click="openAvatarDialog('edit')"
                />
              </div>
            </div>
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
            <q-input
              v-model="editPersona.avatar_path"
              label="当前头像路径"
              readonly
              hint="头像路径由上传生成，不支持手动填写"
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

    <q-dialog v-model="avatarDialog">
      <q-card style="min-width: 520px">
        <q-card-section class="row items-center">
          <div class="text-h6">头像上传与应用</div>
          <q-space />
          <q-chip v-if="avatarDialogPersona" dense color="primary" text-color="white" icon="person">
            {{ avatarDialogPersona.name }} (@{{ avatarDialogPersona.handle }})
          </q-chip>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-md">
          <q-banner v-if="!canUploadAvatar" class="bg-amber-1 text-amber-10" dense>
            保存 Persona 后才能上传头像。创建时可先填写头像 URL，保存后再上传文件。
          </q-banner>
          <div class="row items-center q-gutter-md">
            <div class="avatar-crop-wrapper">
              <div
                class="avatar-crop-box"
                :style="{ width: `${cropBoxSize}px`, height: `${cropBoxSize}px` }"
                @mousedown="startCropDrag"
                @mousemove="onCropDrag"
                @mouseup="endCropDrag"
                @mouseleave="endCropDrag"
                @touchstart.prevent="startCropDrag"
                @touchmove.prevent="onCropDrag"
                @touchend.prevent="endCropDrag"
              >
                <img
                  v-if="avatarCrop.imageUrl"
                  :src="getAvatarSrc(avatarCrop.imageUrl, avatarDialogPersona?.id)"
                  alt="avatar crop"
                  :style="cropImageStyle"
                />
                <div v-else class="avatar-crop-placeholder">
                  选择头像文件后进行裁切
                </div>
              </div>
              <div class="q-mt-sm">
                <q-slider
                  v-model="avatarCrop.scale"
                  :min="minCropScale"
                  :max="4"
                  :step="0.01"
                  label
                  :disable="!avatarCrop.imageUrl"
                  color="primary"
                  @update:model-value="onScaleChange"
                />
                <div class="row items-center justify-between text-caption text-grey-7">
                  <span>缩放</span>
                  <q-btn dense flat icon="refresh" label="重置" :disable="!avatarCrop.imageUrl" @click="resetCrop" />
                </div>
              </div>
            </div>
            <div class="text-caption text-grey-7">
              推荐 1:1 PNG/JPG/WEBP · ≤2MB<br>
              上传接口 `/api/personas/personas/{id}/avatar`
            </div>
          </div>
          <q-file
            v-model="avatarUpload.file"
            label="选择头像文件"
            accept="image/*"
            dense
            clearable
            counter
            max-files="1"
            filled
            :disable="!canUploadAvatar"
            @update:model-value="onAvatarFileChange"
          >
            <template #prepend>
              <q-icon name="cloud_upload" />
            </template>
          </q-file>
          <div class="text-caption text-grey-6" v-if="avatarDialogPersona?.avatar_path">
            当前路径：{{ avatarDialogPersona.avatar_path }}
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="取消" color="primary" v-close-popup />
          <q-btn
            label="上传并应用"
            color="primary"
            :disable="!canUploadAvatar || !avatarUpload.file"
            :loading="avatarUpload.uploading"
            @click="handleAvatarUpload"
          />
        </q-card-actions>
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
import { ref, onMounted, reactive, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { getPersonas, createPersona, updatePersona, deletePersona, getAPIProfiles, uploadPersonaAvatar, type Persona, type APIProfile, type UpdatePersonaPayload, authState } from '../api'

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

// Avatar upload state
const avatarDialog = ref(false)
const avatarDialogMode = ref<'create' | 'edit'>('create')
const avatarDialogPersonaId = ref<number | null>(null)
const avatarUpload = reactive({
  file: null as File | null,
  uploading: false
})
const avatarDialogPersona = computed(() =>
  avatarDialogMode.value === 'edit' && avatarDialogPersonaId.value
    ? personas.value.find(p => p.id === avatarDialogPersonaId.value) || selectedPersona.value
    : null
)
const canUploadAvatar = computed(() => avatarDialogMode.value === 'edit' && !!avatarDialogPersonaId.value)
const cropBoxSize = 260
const avatarCacheBust = reactive<Record<number, string>>({})
const avatarCrop = reactive({
  imageUrl: '',
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  dragging: false,
  startX: 0,
  startY: 0,
  naturalWidth: 0,
  naturalHeight: 0
})

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
  is_default: false,
  avatar_path: ''
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
  is_default: false,
  avatar_path: ''
})

const columns = [
  { name: 'avatar', label: '头像', field: 'avatar_path', align: 'left' as const },
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
    pData.forEach(p => {
      avatarCacheBust[p.id] = avatarCacheBust[p.id] || String(Date.now())
    })
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
  editPersona.avatar_path = persona.avatar_path || ''
  editDialog.value = true
}

const openAvatarDialog = (mode: 'create' | 'edit') => {
  avatarDialogMode.value = mode
  avatarUpload.file = null
  avatarDialogPersonaId.value = mode === 'edit' && editPersona.id ? editPersona.id : null
  if (mode === 'edit' && editPersona.avatar_path) {
    const src = getAvatarSrc(editPersona.avatar_path, editPersona.id)
    avatarCrop.imageUrl = src
    const img = new Image()
    img.onload = () => {
      avatarCrop.naturalWidth = img.naturalWidth
      avatarCrop.naturalHeight = img.naturalHeight
      resetCrop()
    }
    img.src = src
  } else {
    avatarCrop.imageUrl = ''
    resetCrop()
  }
  avatarDialog.value = true
}

const avatarColorPalette = ['primary', 'secondary', 'accent', 'teal', 'indigo', 'deep-orange', 'purple', 'cyan']
const getAvatarColor = (persona: Pick<Persona, 'name' | 'handle'>) => {
  const seed = (persona.handle || persona.name || 'persona') + persona.name
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    hash = (hash << 5) - hash + seed.charCodeAt(i)
    hash |= 0
  }
  const index = Math.abs(hash) % avatarColorPalette.length
  return avatarColorPalette[index]
}

const getAvatarSrc = (path?: string | null, personaId?: number) => {
  if (!path) return ''
  const version = personaId ? avatarCacheBust[personaId] : ''
  if (path.startsWith('blob:')) return path
  if (/^https?:\/\//i.test(path)) {
    const url = new URL(path)
    if (version) url.searchParams.set('v', version)
    return url.toString()
  }
  const normalized = path.startsWith('/') ? path : `/${path}`
  const url = new URL(normalized, window.location.origin)
  if (version) url.searchParams.set('v', version)
  return url.toString()
}

const openDeleteDialog = (persona: Persona) => {
  selectedPersona.value = persona
  deleteDialog.value = true
}

const handleAvatarUpload = async () => {
  if (!canUploadAvatar.value) {
    $q.notify({ type: 'warning', message: '请先保存 Persona 后再上传头像' })
    return
  }
  if (!avatarDialogPersonaId.value || !avatarUpload.file) {
    $q.notify({ type: 'warning', message: '请选择头像文件' })
    return
  }
  avatarUpload.uploading = true
  try {
    const blob = await generateCroppedBlob()
    const croppedFile = new File([blob], avatarUpload.file.name, { type: blob.type })
    const updated = await uploadPersonaAvatar(avatarDialogPersonaId.value, croppedFile, authState.username)
    personas.value = personas.value.map(p => (p.id === updated.id ? updated : p))
    if (editPersona.id === updated.id) {
      editPersona.avatar_path = updated.avatar_path || ''
    }
    if (selectedPersona.value?.id === updated.id) {
      selectedPersona.value = updated
    }
    avatarCacheBust[updated.id] = String(Date.now())
    $q.notify({ type: 'positive', message: '头像已上传并应用' })
    avatarDialog.value = false
  } catch (e: any) {
    console.error(e)
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || '上传头像失败' })
  } finally {
    avatarUpload.uploading = false
    avatarUpload.file = null
  }
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
      is_default: editPersona.is_default,
      avatar_path: editPersona.avatar_path === '' ? null : editPersona.avatar_path
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

const minCropScale = computed(() => {
  if (!avatarCrop.naturalWidth || !avatarCrop.naturalHeight) return 1
  // Shorter edge fills crop box
  const fitScale = Math.max(cropBoxSize / avatarCrop.naturalWidth, cropBoxSize / avatarCrop.naturalHeight)
  return fitScale
})

watch(minCropScale, val => {
  if (avatarCrop.scale < val) {
    avatarCrop.scale = val
  }
})

const resetCrop = () => {
  avatarCrop.scale = minCropScale.value
  avatarCrop.offsetX = 0
  avatarCrop.offsetY = 0
}

const clampOffset = () => {
  const halfW = (avatarCrop.naturalWidth * avatarCrop.scale) / 2
  const halfH = (avatarCrop.naturalHeight * avatarCrop.scale) / 2
  const boundX = Math.max(halfW - cropBoxSize / 2, 0)
  const boundY = Math.max(halfH - cropBoxSize / 2, 0)
  avatarCrop.offsetX = Math.min(boundX, Math.max(-boundX, avatarCrop.offsetX))
  avatarCrop.offsetY = Math.min(boundY, Math.max(-boundY, avatarCrop.offsetY))
}

const onAvatarFileChange = (file: File | File[] | null) => {
  const chosen = Array.isArray(file) ? file[0] : file
  avatarUpload.file = chosen || null
  avatarCrop.imageUrl = ''
  if (!chosen) {
    resetCrop()
    return
  }
  const url = URL.createObjectURL(chosen)
  avatarCrop.imageUrl = url
  const img = new Image()
  img.onload = () => {
    avatarCrop.naturalWidth = img.naturalWidth
    avatarCrop.naturalHeight = img.naturalHeight
    avatarCrop.scale = minCropScale.value
    avatarCrop.offsetX = 0
    avatarCrop.offsetY = 0
  }
  img.src = url
}

const startCropDrag = (event: MouseEvent | TouchEvent) => {
  if (!avatarCrop.imageUrl) return
  avatarCrop.dragging = true
  const point = 'touches' in event ? event.touches[0] : event
  avatarCrop.startX = point.clientX
  avatarCrop.startY = point.clientY
}

const onCropDrag = (event: MouseEvent | TouchEvent) => {
  if (!avatarCrop.dragging) return
  const point = 'touches' in event ? event.touches[0] : event
  const dx = point.clientX - avatarCrop.startX
  const dy = point.clientY - avatarCrop.startY
  avatarCrop.offsetX += dx
  avatarCrop.offsetY += dy
  clampOffset()
  avatarCrop.startX = point.clientX
  avatarCrop.startY = point.clientY
}

const endCropDrag = () => {
  avatarCrop.dragging = false
}

const onScaleChange = () => {
  clampOffset()
}

const cropImageStyle = computed(() => {
  if (!avatarCrop.imageUrl) return {}
  return {
    width: 'auto',
    height: 'auto',
    maxWidth: 'none',
    maxHeight: 'none',
    transform: `translate(-50%, -50%) translate(${avatarCrop.offsetX}px, ${avatarCrop.offsetY}px) scale(${avatarCrop.scale})`,
    transformOrigin: 'center center'
  }
})

const generateCroppedBlob = async (): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    if (!avatarCrop.imageUrl || !avatarUpload.file) {
      reject(new Error('没有可裁剪的头像'))
      return
    }
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      avatarCrop.naturalWidth = img.naturalWidth
      avatarCrop.naturalHeight = img.naturalHeight
      const canvas = document.createElement('canvas')
      const outputSize = 512
      canvas.width = outputSize
      canvas.height = outputSize
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('Canvas 不可用'))
        return
      }
      const scaleFactor = outputSize / cropBoxSize
      const drawWidth = img.width * avatarCrop.scale * scaleFactor
      const drawHeight = img.height * avatarCrop.scale * scaleFactor
      const centerX = outputSize / 2 + avatarCrop.offsetX * scaleFactor
      const centerY = outputSize / 2 + avatarCrop.offsetY * scaleFactor
      const dx = centerX - drawWidth / 2
      const dy = centerY - drawHeight / 2
      ctx.fillStyle = '#fff'
      ctx.fillRect(0, 0, outputSize, outputSize)
      ctx.drawImage(img, dx, dy, drawWidth, drawHeight)
      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob)
        } else {
          reject(new Error('生成头像失败'))
        }
      }, 'image/png')
    }
    img.onerror = reject
    img.src = avatarCrop.imageUrl
  })
}
</script>

<style scoped>
.avatar-crop-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.avatar-crop-box {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: repeating-conic-gradient(#f1f5f9 0% 25%, #e2e8f0 0% 50%);
  border: 1px solid #e0e0e0;
  touch-action: none;
}
.avatar-crop-box img {
  position: absolute;
  top: 50%;
  left: 50%;
  user-select: none;
  pointer-events: none;
}
.avatar-crop-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 12px;
}
</style>
