<template>
  <q-page class="q-pa-md">
    <q-card flat bordered>
      <q-card-section class="row items-center justify-between">
        <div>
          <div class="text-h6">{{ t('admin.title') }}</div>
          <div class="text-subtitle2 text-grey-7">{{ t('admin.subtitle') }}</div>
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
          :no-data-label="t('admin.noData')"
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
                  {{ props.row.is_superuser ? t('admin.badgeAdmin') : t('admin.badgeMember') }}
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
          {{ t('admin.dialogTitle') }}
        </q-card-section>
        <q-card-section>
          {{ t('admin.dialogBody', { username: confirmDialog.target?.username }) }}
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('admin.cancel')" v-close-popup />
          <q-btn
            flat
            color="negative"
            :label="t('admin.delete')"
            :loading="confirmDialog.loading"
            @click="handleDelete"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useQuasar } from 'quasar'
import { authState, fetchAllUsers, deleteUserById, updateUserAdminStatus, type AdminUser } from '../api'
import { useI18n } from 'vue-i18n'

const $q = useQuasar()
const { t } = useI18n()
const loading = ref(false)
const rows = ref<AdminUser[]>([])
const confirmDialog = ref<{ open: boolean; target: AdminUser | null; loading: boolean}>({
  open: false,
  target: null,
  loading: false
})
const rowLoading = ref<Record<number, boolean>>({})

const columns = computed(() => [
  { name: 'id', label: t('admin.columns.id'), field: 'id', sortable: true, align: 'left' },
  { name: 'username', label: t('admin.columns.username'), field: 'username', sortable: true, align: 'left' },
  { name: 'email', label: t('admin.columns.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'role', label: t('admin.columns.role'), field: 'role', sortable: true, align: 'left' },
  { name: 'is_superuser', label: t('admin.columns.permission'), field: 'is_superuser', sortable: true, align: 'left' },
  { name: 'created_at', label: t('admin.columns.createdAt'), field: 'created_at', sortable: true, align: 'left' },
  { name: 'actions', label: t('admin.columns.actions'), field: 'actions', align: 'right' }
])

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
    $q.notify({ type: 'negative', message: error.response?.data?.detail || t('admin.notify.loadFailed') })
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
    $q.notify({ type: 'warning', message: t('admin.notify.cannotRemoveSelf') })
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
      message: t('admin.notify.updateStatus', { username: updated.username })
    })
  } catch (error: any) {
    console.error('Failed to update admin status', error)
    $q.notify({ type: 'negative', message: error.response?.data?.detail || t('admin.notify.updateFailed') })
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
    $q.notify({ type: 'positive', message: t('admin.notify.deleteSuccess', { username: confirmDialog.value.target.username }) })
    confirmDialog.value.open = false
    await loadUsers()
  } catch (error: any) {
    console.error('Failed to delete user', error)
    $q.notify({ type: 'negative', message: error.response?.data?.detail || t('admin.notify.deleteFailed') })
  } finally {
    confirmDialog.value.loading = false
  }
}

onMounted(loadUsers)
</script>
