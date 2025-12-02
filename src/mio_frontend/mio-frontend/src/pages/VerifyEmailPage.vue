<template>
  <q-layout view="lHh Lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center bg-gradient">
        <div class="q-pa-md" style="max-width: 450px; width: 100%">
          <q-card>
            <q-card-section class="text-center q-pb-none">
              <div class="text-h4 text-weight-bold q-mb-sm">
                <q-icon :name="iconName" :color="iconColor" size="xl" />
              </div>
              <div class="text-h5 q-mb-sm">{{ title }}</div>
              <div class="text-subtitle2 text-grey-7">{{ message }}</div>
              <div v-if="status === 'pending'" class="text-caption text-grey-6 q-mt-sm">
                没收到？请检查垃圾邮箱或点击验证邮件中的「Verify Email」按钮。
              </div>
            </q-card-section>

            <q-card-section class="text-center">
              <q-btn
                v-if="status === 'success'"
                label="立即登录"
                color="primary"
                @click="router.push('/login')"
                class="q-mt-md"
              />
              <q-btn
                v-else-if="status === 'error'"
                label="返回注册"
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
                  label="我已完成验证"
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
                  label="返回注册"
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

const router = useRouter()
const route = useRoute()

const status = ref<'loading' | 'success' | 'error' | 'pending'>('loading')
const title = ref('验证中...')
const message = ref('请稍候，正在验证你的邮箱')
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
    title.value = '验证你的邮箱'
    message.value = email.value
      ? `我们已经将验证邮件发送至 ${email.value}，请点击邮件中的链接完成激活。`
      : '我们已经将验证邮件发送至你的邮箱，请点击邮件中的链接完成激活。'
    return
  }
  
  try {
    await api.post('/auth/verify', { token })
    status.value = 'success'
    title.value = '验证成功！'
    message.value = '你的邮箱已验证，现在可以登录使用了'
    if (authState.isLoggedIn) {
      setVerificationStatus(true)
    }
  } catch (error: any) {
    status.value = 'error'
    title.value = '验证失败'
    message.value = error.response?.data?.detail || '验证令牌无效或已过期'
  }
})

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})

const resendButtonLabel = computed(() => {
  if (resendCooldown.value > 0) {
    return `重新发送 (${resendCooldown.value}s)`
  }
  return resendLoading.value ? '发送中...' : '重新发送验证邮件'
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
    resendError.value = '无法确定邮箱地址，请返回重新注册'
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
    resendSuccess.value = '验证邮件已重新发送，请查收'
    startCooldown()
  } catch (error: any) {
    resendError.value = error.response?.data?.detail || '发送失败，请稍后重试'
  } finally {
    resendLoading.value = false
  }
}
</script>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
}
</style>
