<template>
  <div class="debug-page">
    <div class="controls">
      <d-select v-model="lineCount" :options="lineOptions" style="width: 160px" />
      <d-button @click="refresh" :loading="loading">
        <i class="icon-refresh"></i> {{ t('debug.refresh') }}
      </d-button>
      <d-switch v-model="autoRefresh" />
      <span class="label">{{ t('debug.autoRefresh') }}</span>
      <span class="path">{{ logPath }}</span>
    </div>
    <div class="log-view" ref="logView">
      <pre>{{ logs }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const logs = ref('');
const logPath = ref('');
const loading = ref(false);
const autoRefresh = ref(true);
const timer = ref<number | null>(null);
const lineCount = ref(1000);
const { t } = useI18n();
const lineOptions = computed(() => [
  { label: t('debug.options.200'), value: 200 },
  { label: t('debug.options.500'), value: 500 },
  { label: t('debug.options.1000'), value: 1000 },
  { label: t('debug.options.2000'), value: 2000 },
]);

async function refresh() {
  loading.value = true;
  try {
    const res = await fetch(`/api/debug/logs?lines=${lineCount.value}`);
    const data = await res.json();
    logPath.value = data.path;
    logs.value = (data.lines || []).join('\n');
    // Scroll to bottom
    requestAnimationFrame(() => {
      const el = document.querySelector('.log-view');
      if (el) el.scrollTop = el.scrollHeight;
    });
  } catch (e) {
    logs.value = `<${t('debug.loadFailed', { error: e })}>`;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  refresh();
  timer.value = window.setInterval(() => {
    if (autoRefresh.value) {
      refresh();
    }
  }, 2000);
});

onBeforeUnmount(() => {
  if (timer.value) {
    clearInterval(timer.value);
    timer.value = null;
  }
});
</script>

<style scoped>
.debug-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.controls {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #eee;
}
.controls .label {
  color: #666;
}
.controls .path {
  margin-left: auto;
  font-size: 12px;
  color: #999;
}
.log-view {
  flex: 1;
  overflow: auto;
  background: #0b0c10;
  color: #c5c6c7;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  padding: 12px;
}
pre {
  white-space: pre-wrap;
}
</style>
