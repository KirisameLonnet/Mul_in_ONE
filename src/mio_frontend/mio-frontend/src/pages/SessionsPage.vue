<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">Sessions</div>
      <div class="row q-gutter-sm">
        <q-btn 
          v-if="selectedSessions.length > 0"
          color="negative" 
          icon="delete" 
          :label="`Delete (${selectedSessions.length})`" 
          @click="openBatchDeleteDialog" 
          :loading="deleting"
        />
        <q-input
          v-model="searchQuery"
          dense
          outlined
          placeholder="Search sessions..."
          class="q-mr-sm"
          style="min-width: 250px"
        >
          <template v-slot:append>
            <q-icon name="search" />
          </template>
        </q-input>
        <q-btn color="primary" icon="add" label="New Session" @click="openCreateSessionDialog" :loading="creating" />
      </div>
    </div>

    <div v-if="loading" class="flex flex-center q-pa-lg">
      <q-spinner size="3em" color="primary" />
    </div>

    <q-list v-else bordered separator class="rounded-borders">
      <q-item 
        v-for="session in filteredSessions" 
        :key="session.id" 
        clickable 
        v-ripple 
        :to="`/chat/${session.id}`"
      >
        <q-item-section avatar @click.prevent.stop>
          <q-checkbox v-model="selectedSessions" :val="session.id" />
        </q-item-section>
        <q-item-section avatar>
          <q-icon name="chat_bubble" color="primary" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ session.title || `Session #${session.id}` }}</q-item-label>
          <q-item-label caption>{{ new Date(session.created_at).toLocaleString() }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <div class="row items-center q-gutter-sm">
            <q-btn 
              flat 
              round 
              dense 
              icon="edit" 
              color="primary" 
              @click.prevent.stop="openEditSessionDialog(session)"
            >
              <q-tooltip>Edit Session Detail</q-tooltip>
            </q-btn>
            <q-btn 
              flat 
              round 
              dense 
              icon="delete" 
              color="negative" 
              @click.prevent.stop="openDeleteDialog(session)"
            >
              <q-tooltip>Delete Session</q-tooltip>
            </q-btn>
            <q-icon name="chevron_right" />
          </div>
        </q-item-section>
      </q-item>
      <q-item v-if="filteredSessions.length === 0">
        <q-item-section class="text-center text-grey">
          No sessions found.
        </q-item-section>
      </q-item>
    </q-list>

    <!-- Create Session Dialog -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 450px">
        <q-card-section class="bg-primary text-white">
          <div class="text-h6">
            <q-icon name="add_circle" class="q-mr-sm" />
            Create New Session
          </div>
        </q-card-section>

        <q-card-section>
          <q-input v-model="newSessionTitle" outlined dense label="Session Title (optional)" maxlength="255" class="q-mb-md" />
          <div class="row q-col-gutter-md q-mb-md">
            <div class="col-6">
              <q-input v-model="newSessionDisplayName" outlined dense label="Your display name (optional)" maxlength="128" />
            </div>
            <div class="col-6">
              <q-input v-model="newSessionHandle" outlined dense label="Your handle (optional)" maxlength="128" prefix="@" />
            </div>
          </div>
          <q-input
            v-model="newSessionPersona"
            outlined
            autogrow
            type="textarea"
            label="Describe yourself (optional)"
            placeholder="Help agents understand who you are..."
            hint="This helps agents understand your role in the conversation"
            :maxlength="500"
            counter
            rows="3"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            flat
            label="Create"
            color="primary"
            @click="handleCreateSession"
            :loading="creating"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <!-- Edit Session Dialog -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 450px">
        <q-card-section class="bg-secondary text-white">
          <div class="text-h6">
            <q-icon name="edit" class="q-mr-sm" />
            Edit Session Detail
          </div>
        </q-card-section>

        <q-card-section>
          <q-input v-model="editSessionTitle" outlined dense label="Session Title (optional)" maxlength="255" class="q-mb-md" />
          <div class="row q-col-gutter-md q-mb-md">
            <div class="col-6">
              <q-input v-model="editSessionDisplayName" outlined dense label="Your display name (optional)" maxlength="128" />
            </div>
            <div class="col-6">
              <q-input v-model="editSessionHandle" outlined dense label="Your handle (optional)" maxlength="128" prefix="@" />
            </div>
          </div>
          <q-input
            v-model="editSessionPersona"
            outlined
            autogrow
            type="textarea"
            label="Describe yourself (optional)"
            placeholder="Help agents understand who you are..."
            hint="This helps agents understand your role in the conversation"
            :maxlength="500"
            counter
            rows="3"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            flat
            label="Save"
            color="primary"
            @click="handleUpdateSession"
            :loading="updating"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Delete Confirmation Dialog -->
    <q-dialog v-model="showDeleteDialog">
      <q-card>
        <q-card-section class="row items-center">
          <q-avatar icon="warning" color="negative" text-color="white" />
          <span class="q-ml-sm">Are you sure you want to delete this session? This action cannot be undone.</span>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn flat label="Delete" color="negative" @click="handleDeleteSession" :loading="deleting" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Batch Delete Confirmation Dialog -->
    <q-dialog v-model="showBatchDeleteDialog">
      <q-card>
        <q-card-section class="row items-center">
          <q-avatar icon="warning" color="negative" text-color="white" />
          <span class="q-ml-sm">Are you sure you want to delete {{ selectedSessions.length }} sessions? This action cannot be undone.</span>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn flat label="Delete All" color="negative" @click="handleBatchDelete" :loading="deleting" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getSessions, createSession, updateSessionMeta, deleteSession, deleteSessions, type Session } from '../api'
import { useQuasar } from 'quasar'

const sessions = ref<Session[]>([])
const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const deleting = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const showBatchDeleteDialog = ref(false)
const searchQuery = ref('')
const selectedSessions = ref<string[]>([])

// Create form state
const newSessionTitle = ref('')
const newSessionDisplayName = ref('')
const newSessionHandle = ref('')
const newSessionPersona = ref('')

// Edit form state
const editSessionId = ref<string | null>(null)
const editSessionTitle = ref('')
const editSessionDisplayName = ref('')
const editSessionHandle = ref('')
const editSessionPersona = ref('')

// Delete state
const sessionToDelete = ref<Session | null>(null)

const router = useRouter()
const $q = useQuasar()

const filteredSessions = computed(() => {
  if (!searchQuery.value) return sessions.value
  const query = searchQuery.value.toLowerCase()
  return sessions.value.filter(s => 
    (s.title && s.title.toLowerCase().includes(query)) ||
    s.id.toLowerCase().includes(query)
  )
})

const loadSessions = async () => {
  loading.value = true
  try {
    sessions.value = await getSessions()
    selectedSessions.value = [] // Clear selection on reload
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: 'Failed to load sessions'
    })
  } finally {
    loading.value = false
  }
}

const openCreateSessionDialog = () => {
  newSessionTitle.value = ''
  newSessionDisplayName.value = ''
  newSessionHandle.value = ''
  newSessionPersona.value = ''
  showCreateDialog.value = true
}

const openEditSessionDialog = (session: Session) => {
  editSessionId.value = session.id
  editSessionTitle.value = session.title || ''
  editSessionDisplayName.value = session.user_display_name || ''
  editSessionHandle.value = session.user_handle || ''
  editSessionPersona.value = session.user_persona || ''
  showEditDialog.value = true
}

const openDeleteDialog = (session: Session) => {
  sessionToDelete.value = session
  showDeleteDialog.value = true
}

const openBatchDeleteDialog = () => {
  showBatchDeleteDialog.value = true
}

const handleCreateSession = async () => {
  creating.value = true
  try {
    const persona = newSessionPersona.value.trim() || undefined
    const title = newSessionTitle.value.trim() || undefined
    const displayName = newSessionDisplayName.value.trim() || undefined
    const handle = newSessionHandle.value.trim() || undefined
    
    const newSessionId = await createSession(persona, title, displayName, handle)
    showCreateDialog.value = false
    router.push(`/chat/${newSessionId}`)
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: 'Failed to create session'
    })
  } finally {
    creating.value = false
  }
}

const handleUpdateSession = async () => {
  if (!editSessionId.value) return
  updating.value = true
  try {
    const payload = {
      title: editSessionTitle.value.trim() || null,
      user_display_name: editSessionDisplayName.value.trim() || null,
      user_handle: editSessionHandle.value.trim() || null,
      user_persona: editSessionPersona.value.trim() || undefined
    }
    
    await updateSessionMeta(editSessionId.value, payload)
    showEditDialog.value = false
    $q.notify({
      type: 'positive',
      message: 'Session updated successfully'
    })
    await loadSessions()
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: 'Failed to update session'
    })
  } finally {
    updating.value = false
  }
}

const handleDeleteSession = async () => {
  if (!sessionToDelete.value) return
  deleting.value = true
  try {
    await deleteSession(sessionToDelete.value.id)
    showDeleteDialog.value = false
    $q.notify({
      type: 'positive',
      message: 'Session deleted successfully'
    })
    await loadSessions()
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: 'Failed to delete session'
    })
  } finally {
    deleting.value = false
    sessionToDelete.value = null
  }
}

const handleBatchDelete = async () => {
  deleting.value = true
  try {
    await deleteSessions(selectedSessions.value)
    showBatchDeleteDialog.value = false
    $q.notify({
      type: 'positive',
      message: 'Sessions deleted successfully'
    })
    await loadSessions()
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: 'Failed to delete sessions'
    })
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
</style>
