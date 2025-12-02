<template>
  <q-layout view="lHh Lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center bg-gradient">
        <div class="lang-switcher">
          <LanguageSwitcher />
        </div>
        <div class="q-pa-md" style="max-width: 450px; width: 100%">
          <q-card>
            <q-card-section class="text-center q-pb-none">
              <div class="text-h4 text-weight-bold q-mb-sm">
                <q-icon :name="iconName" :color="iconColor" size="xl" />
              </div>
              <div class="text-h5 q-mb-sm">{{ title }}</div>
              <div class="text-subtitle2 text-grey-7">{{ message }}</div>
              <div v-if="status === 'pending'" class="text-caption text-grey-6 q-mt-sm">
                {{ t('verifyEmail.pendingHint') }}
              </div>
            </q-card-section>

            <q-card-section class="text-center">
              <q-btn
                v-if="status === 'success'"
                :label="t('verifyEmail.loginNow')"
                color="primary"
                @click="router.push('/login')"
                class="q-mt-md"
              />
              <q-btn
                v-else-if="status === 'error'"
                :label="t('verifyEmail.backToRegister')"
                color="primary"
                outline
                @click="router.push('/register')"
                class="q-mt-md"
              />
              <div
                v-else-if="status === 'pending'"
                class="q-mt-md column items-center q-gutter-sm"
              >
                <q-btn
                  :label="t('verifyEmail.iVerified')"
                  color="primary"
                  @click="router.push('/login')"
                />
                <q-btn
                  :disable="resendLoading || resendCooldown > 0"
                  outline
                  color="primary"
                  :label="resendButtonLabel"
                  @click="handleResend"
                />
                <div
                  v-if="resendSuccess || resendError"
                  class="text-caption"
                  :class="resendError ? 'text-negative' : 'text-positive'"
                >
                  {{ resendError || resendSuccess }}
                </div>
                <q-btn
                  flat
                  color="grey"
                  :label="t('verifyEmail.backToRegister')"
                  @click="router.push('/register')"
                />
              </div>
              <q-spinner v-else color="primary" size="50px" class="q-mt-md" />
            </q-card-section>
          </q-card>
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api, requestVerificationEmail, setVerificationStatus, authState } from '../api'
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const status = ref<'loading' | 'success' | 'error' | 'pending'>('loading')
const title = ref(t('verifyEmail.titleVerifying'))
const message = ref(t('verifyEmail.msgVerifying'))
const email = ref<string | null>(null)
const resendLoading = ref(false)
const resendSuccess = ref('')
const resendError = ref('')
const resendCooldown = ref(0)
let cooldownTimer: number | null = null

const iconName = computed(() => {
  switch (status.value) {
    case 'success':
      return 'check_circle'
    case 'error':
      return 'error'
    case 'pending':
      return 'mark_email_read'
    default:
      return 'hourglass_empty'
  }
})

const iconColor = computed(() => {
  switch (status.value) {
    case 'success':
      return 'positive'
    case 'error':
      return 'negative'
    case 'pending':
      return 'primary'
    default:
      return 'grey'
  }
})

onMounted(async () => {
  const token = route.query.token as string | undefined
  email.value = (route.query.email as string) || null

  if (!token) {
    status.value = 'pending'
    title.value = t('verifyEmail.titleNeedVerify')
    message.value = email.value
      ? t('verifyEmail.msgSentWithEmail', { email: email.value })
      : t('verifyEmail.msgSent')
    return
  }
  
  try {
    await api.post('/auth/verify', { token })
    status.value = 'success'
    title.value = t('verifyEmail.titleSuccess')
    message.value = t('verifyEmail.msgSuccess')
    if (authState.isLoggedIn) {
      setVerificationStatus(true)
    }
  } catch (error: any) {
    status.value = 'error'
    title.value = t('verifyEmail.titleFailed')
    message.value = error.response?.data?.detail || t('verifyEmail.msgFailed')
  }
})

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})

const resendButtonLabel = computed(() => {
  if (resendCooldown.value > 0) {
    return t('verifyEmail.resendCooldown', { seconds: resendCooldown.value })
  }
  return resendLoading.value ? t('verifyEmail.resendSending') : t('verifyEmail.resend')
})

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
  if (!email.value) {
    resendError.value = t('verifyEmail.resendFailedMissingEmail')
    return
  }
  if (resendCooldown.value > 0 || resendLoading.value) {
    return
  }

  resendLoading.value = true
  resendError.value = ''
  resendSuccess.value = ''
  try {
    await requestVerificationEmail(email.value)
    resendSuccess.value = t('verifyEmail.resendSuccess')
    startCooldown()
  } catch (error: any) {
    resendError.value = error.response?.data?.detail || t('verifyEmail.resendFailed')
  } finally {
    resendLoading.value = false
  }
}
</script>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
}

.lang-switcher {
  position: absolute;
  top: 16px;
  right: 16px;
}
</style>
