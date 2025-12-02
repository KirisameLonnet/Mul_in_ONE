import { createApp } from 'vue'
import { Quasar, Notify, Dialog, Dark } from 'quasar'
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'
import '@devui-design/icons/icomoon/devui-icon.css'
import App from './App.vue'
import router from './router'
import MateChat from '@matechat/core'
import { initTheme } from './theme'
import { i18n } from './i18n'

const app = createApp(App)

app.use(Quasar, {
  plugins: {
    Notify,
    Dialog,
    Dark
  }, 
})

// Initialize theme
initTheme()

app.use(i18n)
app.use(router)
app.use(MateChat)

app.mount('#app')
