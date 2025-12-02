<template>
  <div class="language-switcher">
    <label class="sr-only">{{ $t('languageSwitcher.label') }}</label>
    <select :value="locale" @change="onChange">
      <option v-for="opt in availableLocales" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { availableLocales, setLocale } from '../i18n'

const { locale } = useI18n()

const onChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  setLocale(target.value)
}
</script>

<style scoped>
.language-switcher select {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #d0d7de;
  background: #fff;
  font-size: 12px;
  min-width: 110px;
}

.language-switcher select:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.25);
}

.sr-only {
  position: absolute;
  left: -9999px;
}
</style>
