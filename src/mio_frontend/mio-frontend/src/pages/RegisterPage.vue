<template>
  <q-layout view="lHh Lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center bg-gradient">
        <div class="q-pa-md" style="max-width: 450px; width: 100%">
          <q-card class="register-card">
            <q-card-section class="text-center q-pb-none">
              <div class="text-h4 text-weight-bold q-mb-sm">创建账号</div>
              <div class="text-subtitle2 text-grey-7">加入 Mul-in-ONE</div>
            </q-card-section>

            <q-card-section>
              <q-form @submit="handleRegister">
                <q-input
                  v-model="form.username"
                  label="用户名"
                  outlined
                  dense
                  :rules="[
                    val => !!val || '请输入用户名',
                    val => val.length >= 3 || '用户名至少3个字符'
                  ]"
                  class="q-mb-md"
                >
                  <template v-slot:prepend>
                    <q-icon name="person" />
                  </template>
                </q-input>

                <q-input
                  v-model="form.email"
                  label="邮箱"
                  type="email"
                  outlined
                  dense
                  :rules="[
                    val => !!val || '请输入邮箱',
                    val => /.+@.+\..+/.test(val) || '请输入有效的邮箱地址'
                  ]"
                  class="q-mb-md"
                >
                  <template v-slot:prepend>
                    <q-icon name="email" />
                  </template>
                </q-input>

                <q-input
                  v-model="form.password"
                  label="密码"
                  :type="showPassword ? 'text' : 'password'"
                  outlined
                  dense
                  :rules="[
                    val => !!val || '请输入密码',
                    val => val.length >= 6 || '密码至少6个字符'
                  ]"
                  class="q-mb-md"
                >
                  <template v-slot:prepend>
                    <q-icon name="lock" />
                  </template>
                  <template v-slot:append>
                    <q-icon
                      :name="showPassword ? 'visibility_off' : 'visibility'"
                      class="cursor-pointer"
                      @click="showPassword = !showPassword"
                    />
                  </template>
                </q-input>

                <q-input
                  v-model="form.confirmPassword"
                  label="确认密码"
                  :type="showPassword ? 'text' : 'password'"
                  outlined
                  dense
                  :rules="[
                    val => !!val || '请确认密码',
                    val => val === form.password || '两次密码输入不一致'
                  ]"
                  class="q-mb-md"
                >
                  <template v-slot:prepend>
                    <q-icon name="lock" />
                  </template>
                </q-input>

                <q-input
                  v-model="form.display_name"
                  label="显示名称（可选）"
                  outlined
                  dense
                  class="q-mb-md"
                >
                  <template v-slot:prepend>
                    <q-icon name="badge" />
                  </template>
                </q-input>

                <!-- Cloudflare Turnstile -->
                <div id="turnstile-widget" class="q-mb-md"></div>

                <q-btn
                  label="注册"
                  type="submit"
                  color="primary"
                  class="full-width q-mb-md"
                  :loading="loading"
                  size="md"
                />
              </q-form>
            </q-card-section>

            <q-separator />

            <q-card-section class="text-center q-pt-md">
              <div class="text-caption text-grey-6">
                已有账号？<a href="/login" class="text-primary">立即登录</a>
              </div>
            </q-card-section>
          </q-card>

          <q-banner v-if="error" class="bg-negative text-white q-mt-md" rounded>
            <template v-slot:avatar>
              <q-icon name="error" />
            </template>
            {{ error }}
          </q-banner>
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useQuasar } from 'quasar'

const router = useRouter()
const $q = useQuasar()

const form = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  display_name: ''
})

const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

// Turnstile
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || ''
let turnstileWidget: string | null = null

onMounted(() => {
  // 加载 Turnstile 脚本
  if (TURNSTILE_SITE_KEY && !window.turnstile) {
    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
    script.async = true
    script.defer = true
    script.onload = initTurnstile
    document.head.appendChild(script)
  } else if (window.turnstile) {
    initTurnstile()
  }
})

onUnmounted(() => {
  if (turnstileWidget && window.turnstile) {
    window.turnstile.remove(turnstileWidget)
  }
})

const initTurnstile = () => {
  if (!TURNSTILE_SITE_KEY || !window.turnstile) return
  
  const container = document.getElementById('turnstile-widget')
  if (container) {
    turnstileWidget = window.turnstile.render(container, {
      sitekey: TURNSTILE_SITE_KEY,
      theme: $q.dark.isActive ? 'dark' : 'light'
    })
  }
}

const getTurnstileToken = (): string | null => {
  if (!turnstileWidget || !window.turnstile) return null
  return window.turnstile.getResponse(turnstileWidget)
}

const handleRegister = async () => {
  loading.value = true
  error.value = ''
  
  try {
    // 获取 Turnstile token
    const turnstileToken = getTurnstileToken()
    
    // 调用带验证码的注册接口
    await api.post('/auth/register-with-captcha', {
      email: form.value.email,
      password: form.value.password,
      username: form.value.username,
      display_name: form.value.display_name || undefined,
      turnstile_token: turnstileToken
    })
    
    $q.notify({
      type: 'positive',
      message: '注册成功！请检查邮箱并完成验证后再登录。'
    })

    router.push({
      path: '/verify-email',
      query: { email: form.value.email }
    })
  } catch (err: any) {
    console.error('注册失败:', err)
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') {
      error.value = detail
    } else if (detail?.msg) {
      error.value = detail.msg
    } else {
      error.value = '注册失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
}

.register-card {
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}
</style>
