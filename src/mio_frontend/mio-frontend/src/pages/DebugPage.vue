<template>
  <div class="debug-page">
    <q-card flat bordered class="toolbar-card">
      <div class="toolbar-header">
        <div>
          <div class="title">{{ t('debug.title') }}</div>
          <div class="subtitle">{{ t('debug.subtitle') }}</div>
        </div>
        <div class="chips">
          <q-chip dense square :color="autoRefresh ? 'positive' : 'grey-6'" text-color="white">
            {{ autoRefresh ? t('debug.autoOn') : t('debug.autoOff') }}
          </q-chip>
          <q-chip dense square :color="wrapLines ? 'primary' : 'grey-6'" text-color="white">
            {{ wrapLines ? t('debug.wrapOn') : t('debug.wrapOff') }}
          </q-chip>
          <q-chip dense square color="deep-purple-6" text-color="white">
            {{ t('debug.currentLevel', { level: viewLevel }) }}
          </q-chip>
        </div>
      </div>

      <div class="toolbar-grid">
        <q-select
          v-model="lineCount"
          :options="lineOptions"
          dense
          outlined
          emit-value
          map-options
          :label="t('debug.lineCount')"
        />
        <q-select
          v-model="viewLevel"
          :options="levelOptions"
          dense
          outlined
          emit-value
          map-options
          :label="t('debug.levelLabel')"
          @update:model-value="onLevelChange"
        />
        <q-input
          v-model="searchTerm"
          dense
          outlined
          clearable
          :label="t('debug.searchPlaceholder')"
          @keydown.enter="refresh"
        >
          <template #prepend>
            <q-icon name="search" />
          </template>
        </q-input>
        <div class="toggles">
          <q-toggle v-model="autoRefresh" color="primary" dense :label="t('debug.autoRefresh')" />
          <q-toggle v-model="followTail" color="primary" dense :label="t('debug.followTail')" />
        </div>
        <div class="toggles">
          <q-toggle v-model="wrapLines" color="primary" dense :label="t('debug.wrapLines')" />
        </div>
        <div class="actions">
          <q-btn :loading="loading" color="primary" unelevated icon="refresh" @click="refresh">
            <span class="q-ml-xs">{{ t('debug.refresh') }}</span>
          </q-btn>
          <q-btn flat dense icon="content_copy" @click="copyVisible">
            <span class="q-ml-xs">{{ t('debug.copyVisible') }}</span>
          </q-btn>
          <q-btn flat dense icon="download" @click="downloadVisible">
            <span class="q-ml-xs">{{ t('debug.downloadVisible') }}</span>
          </q-btn>
        </div>
      </div>

      <q-separator spaced />

      <div class="admin-settings" v-if="isAdmin">
        <div class="admin-fields">
          <q-toggle v-model="cleanupEnabled" color="primary" :label="t('debug.cleanupToggle')" />
          <q-input
            v-model.number="cleanupInterval"
            type="number"
            dense
            outlined
            :disable="!cleanupEnabled"
            :min="10"
            :label="t('debug.cleanupIntervalLabel')"
          />
          <div class="hint">
            {{ t('debug.cleanupHint', { readable: readableInterval, minSeconds: 10 }) }}
          </div>
        </div>
        <div class="admin-actions">
          <q-btn color="primary" unelevated :loading="saving" @click="saveSettings">
            {{ t('debug.applyChanges') }}
          </q-btn>
          <q-btn flat color="primary" :loading="cleaning" @click="runCleanup">
            {{ t('debug.runCleanup') }}
          </q-btn>
        </div>
      </div>
    </q-card>

    <q-card flat bordered class="log-card">
      <div class="log-meta">
        <div>
          <div class="meta-title">{{ t('debug.logPath', { path: logPath || 'logs/backend.log' }) }}</div>
          <div class="meta-sub">
            {{ t('debug.visibleCount', { count: visibleCount }) }} ·
            {{ t('debug.totalCount', { count: fetchCount }) }}
          </div>
        </div>
        <div class="meta-actions">
          <q-chip dense square color="primary" text-color="white">
            {{ t('debug.lastUpdated', { time: lastUpdated ? formatTime(lastUpdated) : '—' }) }}
          </q-chip>
        </div>
      </div>
      <div class="log-view" :class="{ 'wrap-lines': wrapLines }" ref="logView">
        <template v-if="visibleLines.length">
          <div
            v-for="(line, idx) in visibleLines"
            :key="idx"
            class="log-line"
            :class="lineClass(line)"
          >
            <span class="line-no">{{ idx + 1 }}</span>
            <span class="line-text">
              <span
                v-for="(segment, sidx) in splitBySearch(line)"
                :key="sidx"
                :class="{ highlight: segment.match }"
              >
                {{ segment.text }}
              </span>
            </span>
          </div>
        </template>
        <div v-else class="empty-state">
          {{ searchTerm ? t('debug.emptyFilter') : t('debug.emptyLogs') }}
        </div>
      </div>
    </q-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import {
  authState,
  fetchLogSettings,
  fetchLogs,
  triggerLogCleanup,
  updateLogSettings,
  type LogLevel
} from '../api';

type Segment = { text: string; match: boolean };

const logPath = ref('');
const rawLines = ref<string[]>([]);
const loading = ref(false);
const autoRefresh = ref(true);
const followTail = ref(true);
const wrapLines = ref(true);
const searchTerm = ref('');
const timer = ref<number | null>(null);
const lineCount = ref(1000);
const viewLevel = ref<LogLevel>('ERROR');
const cleanupEnabled = ref(true);
const cleanupInterval = ref(7 * 24 * 60 * 60);
const saving = ref(false);
const cleaning = ref(false);
const lastUpdated = ref<Date | null>(null);
const logView = ref<HTMLElement | null>(null);
const fetchCount = ref(0);
const { t } = useI18n();
const $q = useQuasar();

const isAdmin = computed(() => authState.isSuperuser || authState.role === 'admin');

const lineOptions = computed(() => [
  { label: t('debug.options.200'), value: 200 },
  { label: t('debug.options.500'), value: 500 },
  { label: t('debug.options.1000'), value: 1000 },
  { label: t('debug.options.2000'), value: 2000 },
]);

const levelOptions = computed(() => [
  { label: t('debug.levels.DEBUG'), value: 'DEBUG' },
  { label: t('debug.levels.INFO'), value: 'INFO' },
  { label: t('debug.levels.WARNING'), value: 'WARNING' },
  { label: t('debug.levels.ERROR'), value: 'ERROR' },
  { label: t('debug.levels.CRITICAL'), value: 'CRITICAL' },
]);

const readableInterval = computed(() => {
  const seconds = Math.max(cleanupInterval.value, 0);
  if (seconds >= 86400) {
    return `${(seconds / 86400).toFixed(1)}d`;
  }
  if (seconds >= 3600) {
    return `${(seconds / 3600).toFixed(1)}h`;
  }
  if (seconds >= 60) {
    return `${(seconds / 60).toFixed(1)}m`;
  }
  return `${seconds}s`;
});

const visibleLines = computed(() => {
  const term = searchTerm.value.trim().toLowerCase();
  if (!term) return rawLines.value;
  return rawLines.value.filter((line) => line.toLowerCase().includes(term));
});

const visibleCount = computed(() => visibleLines.value.length);

function formatTime(date: Date) {
  return date.toLocaleString();
}

function getLevel(line: string): LogLevel | 'UNKNOWN' {
  const tokens = line.trim().split(/\s+/);
  const candidate = tokens[1]?.toUpperCase();
  if (candidate === 'DEBUG' || candidate === 'INFO' || candidate === 'WARNING' || candidate === 'ERROR' || candidate === 'CRITICAL') {
    return candidate;
  }
  return 'UNKNOWN';
}

function lineClass(line: string) {
  const level = getLevel(line);
  return level === 'UNKNOWN' ? 'level-unknown' : `level-${level.toLowerCase()}`;
}

function splitBySearch(line: string): Segment[] {
  const term = searchTerm.value.trim();
  if (!term) return [{ text: line, match: false }];
  const lowerLine = line.toLowerCase();
  const lowerTerm = term.toLowerCase();
  const parts: Segment[] = [];
  let start = 0;
  let idx = lowerLine.indexOf(lowerTerm, start);
  while (idx !== -1) {
    if (idx > start) {
      parts.push({ text: line.slice(start, idx), match: false });
    }
    parts.push({ text: line.slice(idx, idx + term.length), match: true });
    start = idx + term.length;
    idx = lowerLine.indexOf(lowerTerm, start);
  }
  if (start < line.length) {
    parts.push({ text: line.slice(start), match: false });
  }
  return parts;
}

async function loadSettings() {
  try {
    const data = await fetchLogSettings();
    viewLevel.value = data.level;
    cleanupEnabled.value = data.cleanup_enabled;
    cleanupInterval.value = data.cleanup_interval_seconds;
  } catch (error: any) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('debug.loadFailed', { error }) });
  }
}

async function refresh() {
  loading.value = true;
  try {
    const data = await fetchLogs(lineCount.value, viewLevel.value);
    logPath.value = data.path;
    rawLines.value = data.lines || [];
    fetchCount.value = data.count || rawLines.value.length;
    lastUpdated.value = new Date();
    requestAnimationFrame(() => {
      if (followTail.value && logView.value) {
        logView.value.scrollTop = logView.value.scrollHeight;
      }
    });
  } catch (error: any) {
    rawLines.value = [`<${t('debug.loadFailed', { error })}>`];
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('debug.loadFailed', { error }) });
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  if (!isAdmin.value) return;
  saving.value = true;
  cleanupInterval.value = Math.max(cleanupInterval.value || 0, 10);
  try {
    const updated = await updateLogSettings({
      level: viewLevel.value,
      cleanup_enabled: cleanupEnabled.value,
      cleanup_interval_seconds: cleanupInterval.value,
    });
    viewLevel.value = updated.level;
    cleanupEnabled.value = updated.cleanup_enabled;
    cleanupInterval.value = updated.cleanup_interval_seconds;
    $q.notify({ type: 'positive', message: t('debug.saveSuccess') });
    refresh();
  } catch (error: any) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('debug.saveFailed') });
    await loadSettings();
  } finally {
    saving.value = false;
  }
}

async function runCleanup() {
  if (!isAdmin.value) return;
  cleaning.value = true;
  try {
    await triggerLogCleanup();
    $q.notify({ type: 'positive', message: t('debug.cleanupTriggered') });
    refresh();
  } catch (error: any) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('debug.saveFailed') });
  } finally {
    cleaning.value = false;
  }
}

function onLevelChange(value: LogLevel) {
  viewLevel.value = value;
  if (isAdmin.value) {
    saveSettings();
  } else {
    refresh();
  }
}

async function copyVisible() {
  const content = visibleLines.value.join('\n');
  if (!content) return;
  try {
    await navigator.clipboard.writeText(content);
    $q.notify({ type: 'positive', message: t('debug.copied') });
  } catch (error: any) {
    $q.notify({ type: 'negative', message: t('debug.copyFailed') });
  }
}

function downloadVisible() {
  const content = visibleLines.value.join('\n');
  if (!content) return;
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `backend-log-${Date.now()}.log`;
  link.click();
  URL.revokeObjectURL(url);
}

onMounted(() => {
  loadSettings().then(refresh);
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
  gap: 12px;
}
.toolbar-card {
  padding: 16px;
}
.toolbar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.title {
  font-size: 18px;
  font-weight: 700;
}
.subtitle {
  color: #666;
  margin-top: 2px;
}
.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.toolbar-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  align-items: center;
}
.toggles {
  display: flex;
  gap: 12px;
  align-items: center;
}
.actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}
.admin-settings {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e5e5e5;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}
.admin-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.admin-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.hint {
  color: #666;
  font-size: 12px;
}
.log-card {
  display: flex;
  flex-direction: column;
  flex: 1;
}
.log-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px 0;
}
.meta-title {
  font-weight: 600;
}
.meta-sub {
  color: #7a7a7a;
  font-size: 12px;
  margin-top: 2px;
}
.log-view {
  flex: 1;
  overflow: auto;
  background: #0b0c10;
  color: #c5c6c7;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  padding: 12px 0;
  border-radius: 6px;
  margin: 12px 12px 12px 12px;
}
.log-view.wrap-lines .line-text {
  white-space: pre-wrap;
}
.log-view:not(.wrap-lines) .line-text {
  white-space: pre;
}
.log-line {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 8px;
  align-items: start;
  padding: 4px 12px;
  border-left: 3px solid transparent;
}
.line-no {
  color: #8f95a3;
  text-align: right;
}
.line-text {
  color: inherit;
}
.line-text .highlight {
  background: rgba(255, 214, 102, 0.35);
  padding: 0 2px;
  border-radius: 3px;
}
.log-line.level-debug {
  border-color: #38bdf8;
  color: #cfeafe;
}
.log-line.level-info {
  border-color: #22c55e;
  color: #d2f1e1;
}
.log-line.level-warning {
  border-color: #facc15;
  color: #fef3c7;
}
.log-line.level-error {
  border-color: #f87171;
  color: #fde2e2;
}
.log-line.level-critical {
  border-color: #ef4444;
  color: #ffe4e6;
  font-weight: 600;
}
.log-line.level-unknown {
  border-color: #94a3b8;
}
.empty-state {
  color: #9da0a6;
  padding: 16px;
  text-align: center;
}
</style>
