<template>
  <q-page class="flex flex-center">
    <div class="q-pa-md" style="max-width: 400px">
      <q-card>
        <q-card-section>
          <div class="text-h6">Login</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="username" label="Username" />
          <q-input v-model="tenantId" label="Tenant ID" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Login" color="primary" @click="login" />
        </q-card-actions>
      </q-card>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login as apiLogin } from '../api'

const username = ref('user')
const tenantId = ref('default')
const router = useRouter()

const login = async () => {
  await apiLogin(username.value, tenantId.value)
  router.push('/')
}
</script>
