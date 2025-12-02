<template>
  <q-page padding>
    <div class="text-h4 q-mb-xs">Account Settings</div>
    <div class="text-subtitle2 text-grey-7 q-mb-lg">Manage your profile information and account lifecycle.</div>

    <div v-if="loading" class="flex flex-center q-my-xl">
      <q-spinner size="3em" color="primary" />
    </div>

    <template v-else>
      <q-banner v-if="loadError" class="bg-negative text-white q-mb-md" rounded>
        {{ loadError }}
        <template #action>
          <q-btn flat color="white" label="Retry" @click="loadUser" />
        </template>
      </q-banner>

      <q-card class="q-mb-lg">
        <q-card-section class="bg-primary text-white">
          <div class="text-h6">Profile</div>
        </q-card-section>
        <q-card-section>
          <q-list separator>
            <q-item>
              <q-item-section>
                <q-item-label>Email</q-item-label>
                <q-item-label caption>{{ user?.email || '-' }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-chip :color="user?.is_verified ? 'positive' : 'warning'" text-color="white" dense>
                  {{ user?.is_verified ? 'Verified' : 'Pending' }}
                </q-chip>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section>
                <q-item-label>Username</q-item-label>
                <q-item-label caption>{{ user?.username || '-' }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section>
                <q-item-label>Display name</q-item-label>
                <q-item-label caption>{{ user?.display_name || 'Not set' }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section>
                <q-item-label>Role</q-item-label>
                <q-item-label caption>{{ user?.is_superuser ? 'Administrator' : 'Standard user' }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-chip :color="user?.is_superuser ? 'secondary' : 'primary'" text-color="white" dense>
                  {{ user?.is_superuser ? 'Superuser' : 'User' }}
                </q-chip>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section>
                <q-item-label>Status</q-item-label>
                <q-item-label caption>{{ user?.is_active ? 'Active' : 'Inactive' }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-chip :color="user?.is_active ? 'positive' : 'negative'" text-color="white" dense>
                  {{ user?.is_active ? 'Active' : 'Disabled' }}
                </q-chip>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>

      <q-card class="danger-card">
        <q-card-section class="bg-negative text-white">
          <div class="text-h6">Danger Zone</div>
          <div>Permanently delete your Mul in ONE account.</div>
        </q-card-section>
        <q-card-section>
          <p class="q-mb-md">
            Deleting your account removes all sessions, personas, API profiles, and stored data. This action cannot be undone.
          </p>
          <q-btn color="negative" icon="delete_forever" label="Delete Account" @click="openDeleteDialog" />
        </q-card-section>
      </q-card>
    </template>

    <q-dialog v-model="showDeleteDialog" persistent @hide="confirmKeywordInput = ''">
      <q-card style="min-width: 420px">
        <q-card-section class="bg-negative text-white">
          <div class="text-h6">
            <q-icon name="warning" class="q-mr-sm" />
            Confirm Account Deletion
          </div>
        </q-card-section>

        <q-card-section>
          <p class="q-mb-md">
            This will permanently delete your account and all associated data. Please type <strong>{{ CONFIRM_KEYWORD }}</strong> to continue.
          </p>
          <q-input
            v-model="confirmKeywordInput"
            outlined
            dense
            label="Type DELETE to confirm"
            autofocus
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup :disable="deleting" />
          <q-btn
            flat
            label="Delete"
            color="negative"
            :disable="!canConfirmDeletion || deleting"
            :loading="deleting"
            @click="handleDeleteAccount"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { getCurrentUser, deleteAccount, logout, type UserInfo } from '../api'

const user = ref<UserInfo | null>(null)
const loading = ref(true)
const loadError = ref('')
const showDeleteDialog = ref(false)
const deleting = ref(false)
const confirmKeywordInput = ref('')

const router = useRouter()
const $q = useQuasar()

const CONFIRM_KEYWORD = 'DELETE'
const canConfirmDeletion = computed(() => confirmKeywordInput.value === CONFIRM_KEYWORD)

const loadUser = async () => {
  loading.value = true
  loadError.value = ''
  try {
    user.value = await getCurrentUser()
  } catch (error) {
    loadError.value = 'Failed to load account information'
  } finally {
    loading.value = false
  }
}

const openDeleteDialog = () => {
  confirmKeywordInput.value = ''
  showDeleteDialog.value = true
}

const handleDeleteAccount = async () => {
  if (!canConfirmDeletion.value) return
  deleting.value = true
  try {
    await deleteAccount()
    logout()
    $q.notify({ type: 'positive', message: 'Account deleted successfully' })
    router.push('/register')
  } catch (error) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: detail || 'Failed to delete account' })
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}

onMounted(() => {
  loadUser()
})
</script>

<style scoped>
.danger-card {
  border: 1px solid #f44336;
}
</style>
