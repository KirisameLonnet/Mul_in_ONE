<template>
  <q-layout view="lHh Lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center bg-gradient">
        <div class="q-pa-md" style="max-width: 450px; width: 100%">
          <q-card class="login-card">
            <q-card-section class="text-center q-pb-none">
              <div class="text-h4 text-weight-bold q-mb-sm">Mul-in-ONE</div>
              <div class="text-subtitle2 text-grey-7">多智能体对话系统</div>
            </q-card-section>

            <q-card-section>
              <q-form @submit="handleLogin">
                <q-input
                  v-model="email"
                  label="邮箱"
                  type="email"
                  outlined
                  dense
                  :rules="[val => !!val || '请输入邮箱']"
                  class="q-mb-md"
                >
                  <template v-slot:prepend>
                    <q-icon name="email" />
                  </template>
                </q-input>

                <q-input
                  v-model="password"
                  label="密码"
                  :type="showPassword ? 'text' : 'password'"
                  outlined
                  dense
                  :rules="[val => !!val || '请输入密码']"
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

                <q-btn
                  label="登录"
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
              <div class="text-subtitle2 text-grey-7 q-mb-sm">第三方登录</div>
              <div class="row q-gutter-sm justify-center">
                <q-btn
                  flat
                  dense
                  label="Gitee"
                  :style="{ color: $q.dark.isActive ? 'white' : '#C71D23' }"
                  @click="loginWithGitee"
                  :disable="!giteeAvailable"
                />
                <q-btn
                  flat
                  dense
                  label="GitHub"
                  :style="{ color: $q.dark.isActive ? 'white' : '#24292e' }"
                  @click="loginWithGitHub"
                  :disable="!githubAvailable"
                />
              </div>
              <div class="text-caption text-grey-6 q-mt-sm">
                还没有账号？<a href="/register" class="text-primary">注册</a>
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
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authLogin, login, getCurrentUser, setVerificationStatus } from '../api'
import { useQuasar } from 'quasar'

const router = useRouter()
const route = useRoute()
const $q = useQuasar()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

// OAuth 可用性（可通过环境变量或后端配置检测）
const giteeAvailable = ref(true)
const githubAvailable = ref(true)

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  
  try {
    // 调用登录 API
    const response = await authLogin({
      username: email.value,
      password: password.value
    })
    
    // 先保存 token（临时用 email 作为 username）
    login(email.value, response.access_token)
    setVerificationStatus(false)
    
    // 获取用户信息
    const userInfo = await getCurrentUser()
    
    // 更新为正确的 username
    login(userInfo.username, response.access_token, { email: userInfo.email, isVerified: userInfo.is_verified })
    
    $q.notify({
      type: 'positive',
      message: `欢迎回来，${userInfo.display_name || userInfo.username}！`
    })
    
    // 跳转到目标页面或首页
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  } catch (err: any) {
    console.error('登录失败:', err)
    error.value = err.response?.data?.detail || '登录失败，请检查邮箱和密码'
  } finally {
    loading.value = false
  }
}

const loginWithGitee = () => {
  window.location.href = '/api/auth/gitee/authorize'
}

const loginWithGitHub = () => {
  window.location.href = '/api/auth/github/authorize'
}

// 处理 OAuth 回调（如果 URL 中有 token）
const handleOAuthCallback = async () => {
  const token = route.query.token as string
  if (token) {
    try {
      const userInfo = await getCurrentUser()
      login(userInfo.username, token)
      $q.notify({
        type: 'positive',
        message: `欢迎，${userInfo.display_name || userInfo.username}！`
      })
      router.push('/')
    } catch (err) {
      error.value = 'OAuth 登录失败'
    }
  }
}

// 组件加载时检查 OAuth 回调
handleOAuthCallback()
</script>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
}

.login-card {
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}
</style>
