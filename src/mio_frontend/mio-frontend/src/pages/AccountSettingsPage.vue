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

      <q-card v-if="user && !user.is_verified" class="q-mb-lg warning-card">
        <q-card-section class="bg-warning text-black">
          <div class="text-h6">Email verification required</div>
          <div class="text-body2">
            You must verify your email before creating sessions, personas, or API profiles. Please check your inbox and click the link. Not seeing the email?
          </div>
        </q-card-section>
        <q-card-section class="column q-gutter-sm">
          <q-btn
            color="primary"
            :disable="resendLoading || resendCooldown > 0"
            :label="resendButtonLabel"
            @click="handleResend"
          />
          <q-btn
            outline
            color="primary"
            label="I've verified my email"
            :loading="manualRefreshLoading"
            :disable="manualRefreshLoading"
            @click="handleManualVerificationRefresh"
          />
          <div
            v-if="resendSuccess || resendError"
            class="text-caption"
            :class="resendError ? 'text-negative' : 'text-positive'"
          >
            {{ resendError || resendSuccess }}
          </div>
        </q-card-section>
      </q-card>

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
          <q-btn
            color="negative"
            icon="delete_forever"
            label="Delete Account"
            @click="openDeleteDialog"
            :disable="resendLoading"
          />
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { getCurrentUser, deleteAccount, logout, requestVerificationEmail, authState, type UserInfo } from '../api'

const user = ref<UserInfo | null>(null)
const loading = ref(true)
const loadError = ref('')
const showDeleteDialog = ref(false)
const deleting = ref(false)
const confirmKeywordInput = ref('')
const resendLoading = ref(false)
const resendSuccess = ref('')
const resendError = ref('')
const resendCooldown = ref(0)
const manualRefreshLoading = ref(false)
let cooldownTimer: number | null = null

const router = useRouter()
const $q = useQuasar()

const CONFIRM_KEYWORD = 'DELETE'
const canConfirmDeletion = computed(() => confirmKeywordInput.value === CONFIRM_KEYWORD)
const resendButtonLabel = computed(() => {
  if (resendCooldown.value > 0) {
    return `Resend verification email (${resendCooldown.value}s)`
  }
  return resendLoading.value ? 'Sending...' : 'Resend verification email'
})

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

const refreshUserSilently = async () => {
  const profile = await getCurrentUser()
  user.value = profile
  return profile
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

const startCooldown = () => {
  resendCooldown.value = 60
  cooldownTimer = window.setInterval(() => {
    if (resendCooldown.value <= 1) {
      resendCooldown.value = 0
      if (cooldownTimer) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    } else {
      resendCooldown.value -= 1
    }
  }, 1000)
}

const handleResend = async () => {
  if (!user.value?.email) {
    resendError.value = 'Missing email address'
    return
  }
  if (resendCooldown.value > 0 || resendLoading.value) {
    return
  }
  resendLoading.value = true
  resendError.value = ''
  resendSuccess.value = ''
  try {
    await requestVerificationEmail(user.value.email)
    resendSuccess.value = 'Verification email re-sent'
    startCooldown()
  } catch (error: any) {
    resendError.value = error.response?.data?.detail || 'Failed to send verification email'
  } finally {
    resendLoading.value = false
  }
}

const handleManualVerificationRefresh = async () => {
  manualRefreshLoading.value = true
  try {
    const profile = await refreshUserSilently()
    if (profile.is_verified) {
      $q.notify({ type: 'positive', message: 'Email verified! You now have full access.' })
    } else {
      $q.notify({ type: 'warning', message: 'Still pending. Please check your inbox or resend the link.' })
    }
  } catch (error) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: detail || 'Unable to refresh verification status' })
  } finally {
    manualRefreshLoading.value = false
  }
}

onMounted(() => {
  loadUser()
})

watch(
  () => authState.isVerified,
  async (isVerified, wasVerified) => {
    if (isVerified && !wasVerified && (!user.value || !user.value.is_verified)) {
      try {
        await refreshUserSilently()
        $q.notify({ type: 'positive', message: 'Email verified! Account data refreshed.' })
      } catch (error) {
        console.error('Failed to refresh account data', error)
      }
    }
  },
  { immediate: false }
)

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})
</script>

<style scoped>
.danger-card {
  border: 1px solid #f44336;
}
.warning-card {
  border: 1px solid #ff9800;
}
</style>
