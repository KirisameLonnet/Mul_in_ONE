<template>
  <q-page class="q-pa-md">
    <q-card flat bordered>
      <q-card-section class="row items-center justify-between">
        <div>
          <div class="text-h6">User Administration</div>
          <div class="text-subtitle2 text-grey-7">Manage all registered accounts</div>
        </div>
        <q-btn dense flat round icon="refresh" :loading="loading" @click="loadUsers" />
      </q-card-section>

      <q-separator />

      <q-card-section>
        <q-table
          flat
          bordered
          :rows="rows"
          :columns="columns"
          row-key="id"
          :loading="loading"
          no-data-label="暂无用户"
        >
          <template #body-cell-created_at="props">
            <q-td :props="props">
              {{ formatDate(props.row.created_at) }}
            </q-td>
          </template>
          <template #body-cell-is_superuser="props">
            <q-td :props="props">
              <div class="row items-center">
                <q-badge :color="props.row.is_superuser ? 'primary' : 'grey'">
                  {{ props.row.is_superuser ? 'Admin' : 'Member' }}
                </q-badge>
                <q-toggle
                  class="q-ml-md"
                  size="sm"
                  color="primary"
                  :model-value="props.row.is_superuser"
                  :disable="props.row.username === authState.username || isRowBusy(props.row.id)"
                  @update:model-value="value => handleAdminToggle(props.row, value)"
                />
                <q-spinner v-if="isRowBusy(props.row.id)" size="xs" class="q-ml-sm" />
              </div>
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                size="sm"
                dense
                flat
                round
                color="negative"
                icon="delete"
                :disable="props.row.username === authState.username"
                @click="promptDelete(props.row)"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <q-dialog v-model="confirmDialog.open">
      <q-card style="min-width: 350px">
        <q-card-section class="text-h6">
          删除用户
        </q-card-section>
        <q-card-section>
          确定删除用户
          <strong>{{ confirmDialog.target?.username }}</strong>
          ？该操作不可撤销。
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="取消" v-close-popup />
          <q-btn
            flat
            color="negative"
            label="删除"
            :loading="confirmDialog.loading"
            @click="handleDelete"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { authState, fetchAllUsers, deleteUserById, updateUserAdminStatus, type AdminUser } from '../api'

const $q = useQuasar()
const loading = ref(false)
const rows = ref<AdminUser[]>([])
const confirmDialog = ref<{ open: boolean; target: AdminUser | null; loading: boolean}>({
  open: false,
  target: null,
  loading: false
})
const rowLoading = ref<Record<number, boolean>>({})

const columns = [
  { name: 'id', label: 'ID', field: 'id', sortable: true, align: 'left' },
  { name: 'username', label: '用户名', field: 'username', sortable: true, align: 'left' },
  { name: 'email', label: '邮箱', field: 'email', sortable: true, align: 'left' },
  { name: 'role', label: '角色', field: 'role', sortable: true, align: 'left' },
  { name: 'is_superuser', label: '权限', field: 'is_superuser', sortable: true, align: 'left' },
  { name: 'created_at', label: '注册时间', field: 'created_at', sortable: true, align: 'left' },
  { name: 'actions', label: '操作', field: 'actions', align: 'right' }
]

const formatDate = (value: string) => {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString()
}

const loadUsers = async () => {
  loading.value = true
  try {
    rows.value = await fetchAllUsers()
  } catch (error: any) {
    console.error('Failed to load users', error)
    $q.notify({ type: 'negative', message: error.response?.data?.detail || '获取用户列表失败' })
  } finally {
    loading.value = false
  }
}

const setRowBusy = (id: number, busy: boolean) => {
  rowLoading.value = { ...rowLoading.value, [id]: busy }
}

const isRowBusy = (id: number) => rowLoading.value[id] === true

const handleAdminToggle = async (user: AdminUser, isAdmin: boolean) => {
  if (user.username === authState.username && !isAdmin) {
    $q.notify({ type: 'warning', message: '不能取消自己的管理员权限' })
    return
  }
  if (user.is_superuser === isAdmin) {
    return
  }
  setRowBusy(user.id, true)
  try {
    const updated = await updateUserAdminStatus(user.id, isAdmin)
    rows.value = rows.value.map(row => (row.id === updated.id ? updated : row))
    $q.notify({
      type: 'positive',
      message: isAdmin ? `已将 ${updated.username} 设置为管理员` : `已取消 ${updated.username} 的管理员权限`
    })
  } catch (error: any) {
    console.error('Failed to update admin status', error)
    $q.notify({ type: 'negative', message: error.response?.data?.detail || '更新管理员权限失败' })
  } finally {
    setRowBusy(user.id, false)
  }
}

const promptDelete = (user: AdminUser) => {
  confirmDialog.value = {
    open: true,
    target: user,
    loading: false
  }
}

const handleDelete = async () => {
  if (!confirmDialog.value.target) {
    return
  }
  confirmDialog.value.loading = true
  try {
    await deleteUserById(confirmDialog.value.target.id)
    $q.notify({ type: 'positive', message: `已删除用户 ${confirmDialog.value.target.username}` })
    confirmDialog.value.open = false
    await loadUsers()
  } catch (error: any) {
    console.error('Failed to delete user', error)
    $q.notify({ type: 'negative', message: error.response?.data?.detail || '删除用户失败' })
  } finally {
    confirmDialog.value.loading = false
  }
}

onMounted(loadUsers)
</script>
