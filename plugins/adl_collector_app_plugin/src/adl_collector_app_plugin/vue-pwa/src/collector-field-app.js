import {createApp} from 'vue'
import {createPinia} from 'pinia'
import App from './App.vue'
import router from './router'

const el = document.getElementById('collector-field-app')

const props = el
    ? {
        apiBase: el.dataset.apiBase || '/api/adl-collector',
        tokenUrl: el.dataset.tokenUrl || '/api/auth/token/',
    }
    : {}

const app = createApp(App, props)
app.use(createPinia())
app.use(router)
app.mount(el || '#collector-field-app')
