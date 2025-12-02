<template>
  <q-layout view="lHh Lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center bg-gradient">
        <div class="lang-switcher">
          <LanguageSwitcher />
        </div>
        <div class="q-pa-md" style="max-width: 450px; width: 100%">
          <q-card class="login-card">
            <q-card-section class="text-center q-pb-none">
              <div class="text-h4 text-weight-bold q-mb-sm">{{ t('login.title') }}</div>
              <div class="text-subtitle2 text-grey-7">{{ t('login.subtitle') }}</div>
            </q-card-section>

            <q-card-section>
              <q-form @submit="handleLogin">
                <q-input
                  v-model="email"
                  :label="t('login.email')"
                  type="email"
                  outlined
                  dense
                  :rules="[val => !!val || t('login.rules.email')]"
                  class="q-mb-md"
                >
                  <template v-slot:prepend>
                    <q-icon name="email" />
                  </template>
                </q-input>

                <q-input
                  v-model="password"
                  :label="t('login.password')"
                  :type="showPassword ? 'text' : 'password'"
                  outlined
                  dense
                  :rules="[val => !!val || t('login.rules.password')]"
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
                  :label="t('login.signIn')"
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
              <div class="text-subtitle2 text-grey-7 q-mb-sm">{{ t('login.thirdParty') }}</div>
              <div class="row q-gutter-sm justify-center">
                <q-btn
                  flat
                  dense
                  :label="t('login.gitee')"
                  :style="{ color: $q.dark.isActive ? 'white' : '#C71D23' }"
                  @click="loginWithGitee"
                  :disable="!giteeAvailable"
                />
                <q-btn
                  flat
                  dense
                  :label="t('login.github')"
                  :style="{ color: $q.dark.isActive ? 'white' : '#24292e' }"
                  @click="loginWithGitHub"
                  :disable="!githubAvailable"
                />
              </div>
              <div class="text-caption text-grey-6 q-mt-sm">
                {{ t('login.noAccount') }}<a href="/register" class="text-primary">{{ t('login.goRegister') }}</a>
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
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const router = useRouter()
const route = useRoute()
const $q = useQuasar()
const { t } = useI18n()

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
    login(userInfo.username, response.access_token, {
      email: userInfo.email,
      isVerified: userInfo.is_verified,
      role: userInfo.role,
      isSuperuser: userInfo.is_superuser
    })
    
    $q.notify({
      type: 'positive',
      message: t('login.welcomeBack', { name: userInfo.display_name || userInfo.username })
    })
    
    // 跳转到目标页面或首页
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  } catch (err: any) {
    console.error('登录失败:', err)
    error.value = err.response?.data?.detail || t('login.loginFailed')
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
      login(userInfo.username, token, {
        email: userInfo.email,
        isVerified: userInfo.is_verified,
        role: userInfo.role,
        isSuperuser: userInfo.is_superuser
      })
      $q.notify({
        type: 'positive',
        message: t('login.welcomeBack', { name: userInfo.display_name || userInfo.username })
      })
      router.push('/')
    } catch (err) {
      error.value = t('login.oauthFailed')
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

.lang-switcher {
  position: absolute;
  top: 16px;
  right: 16px;
}
</style>
