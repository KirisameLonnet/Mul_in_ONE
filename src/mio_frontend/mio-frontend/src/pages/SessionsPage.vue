<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h4">Sessions</div>
      <q-btn color="primary" icon="add" label="New Session" @click="handleCreateSession" :loading="creating" />
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
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSessions, createSession, type Session, authState } from '../api'
import { useQuasar } from 'quasar'

const sessions = ref<Session[]>([])
const loading = ref(false)
const creating = ref(false)
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

const handleCreateSession = async () => {
  creating.value = true
  try {
    const newSessionId = await createSession()
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
