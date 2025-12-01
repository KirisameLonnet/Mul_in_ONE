<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">Sessions</div>
      <q-btn color="primary" icon="add" label="New Session" @click="openCreateSessionDialog" :loading="creating" />
    </div>

    <div v-if="loading" class="flex flex-center q-pa-lg">
      <q-spinner size="3em" color="primary" />
    </div>

    <q-list v-else bordered separator class="rounded-borders">
      <q-item 
        v-for="session in sessions" 
        :key="session.id" 
        clickable 
        v-ripple 
        :to="`/chat/${session.id}`"
      >
        <q-item-section avatar>
          <q-icon name="chat_bubble" color="primary" />
        </q-item-section>
        <q-item-section>
          <q-item-label>Session #{{ session.id }}</q-item-label>
          <q-item-label caption>{{ new Date(session.created_at).toLocaleString() }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-icon name="chevron_right" />
        </q-item-section>
      </q-item>
      <q-item v-if="sessions.length === 0">
        <q-item-section class="text-center text-grey">
          No sessions found. Create one to start chatting.
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
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSessions, createSession, type Session } from '../api'
import { useQuasar } from 'quasar'

const sessions = ref<Session[]>([])
const loading = ref(false)
const creating = ref(false)
const showCreateDialog = ref(false)
const newSessionTitle = ref('')
const newSessionDisplayName = ref('')
const newSessionHandle = ref('')
const newSessionPersona = ref('')
const router = useRouter()
const $q = useQuasar()

const loadSessions = async () => {
  loading.value = true
  try {
    sessions.value = await getSessions()
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

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
</style>
