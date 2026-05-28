<template>
  <div id="adl-pwa">
    <header class="app-header">
      <span class="app-title">ADL Collector</span>
      <nav v-if="auth.isLoggedIn">
        <router-link to="/stations">Stations</router-link>
        <router-link to="/pending">Pending ({{ pendingCount }})</router-link>
        <button @click="auth.logout(); $router.push('/login')" class="btn-link">Logout</button>
      </nav>
    </header>

    <main class="app-main">
      <router-view/>
    </main>
  </div>
</template>

<script setup>
import {ref, onMounted, onUnmounted} from 'vue'
import {useAuthStore} from '@/stores/auth'
import {listPending, flushQueue} from '@/queue'
import {api, configureApi} from '@/api'

const props = defineProps({
  apiBase: {type: String, default: '/api/adl-collector'},
  tokenUrl: {type: String, default: '/api/token/'},
})

// Apply Django-supplied URLs before any API call fires
configureApi({apiBase: props.apiBase, tokenUrl: props.tokenUrl})

const auth = useAuthStore()
const pendingCount = ref(0)

async function refreshPendingCount() {
  const items = await listPending()
  pendingCount.value = items.length
}

async function syncOnline() {
  if (!auth.isLoggedIn) return
  await flushQueue((item) => api.submitObservation(item))
  await refreshPendingCount()
}

onMounted(async () => {
  await refreshPendingCount()
  window.addEventListener('online', syncOnline)
  if (navigator.onLine) syncOnline()
})

onUnmounted(() => {
  window.removeEventListener('online', syncOnline)
})
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: system-ui, sans-serif;
  background: #f4f6f8;
  color: #1a1a2e;
}

#adl-pwa {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: #1a3a5c;
  color: #fff;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-title {
  font-weight: 700;
  font-size: 1.1rem;
}

nav {
  display: flex;
  gap: 1rem;
  align-items: center;
}

nav a, .btn-link {
  color: #a8d4f5;
  text-decoration: none;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
}

nav a.router-link-active {
  color: #fff;
  font-weight: 600;
}

.app-main {
  flex: 1;
  padding: 1rem;
  max-width: 640px;
  width: 100%;
  margin: 0 auto;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.btn {
  display: inline-block;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 0.95rem;
  transition: opacity 0.15s;
}

.btn-primary {
  background: #1a3a5c;
  color: #fff;
}

.btn-secondary {
  background: #e2e8f0;
  color: #1a1a2e;
}

.btn:disabled {
  background: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-full {
  width: 100%;
  text-align: center;
}

input, select, textarea {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.95rem;
  margin-top: 0.25rem;
}

label {
  font-weight: 600;
  font-size: 0.875rem;
  color: #475569;
  display: block;
  margin-top: 0.75rem;
}

.error {
  color: #dc2626;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 0.65rem 0.9rem;
  margin-bottom: 0.75rem;
  color: #b91c1c;
  font-size: 0.875rem;
}

.error-banner p {
  margin: 0;
}

.error-banner p + p {
  margin-top: 0.25rem;
}

.field-error {
  display: block;
  color: #dc2626;
  font-size: 0.8rem;
  font-weight: 400;
  margin-top: 0.2rem;
}

.input-error {
  border-color: #dc2626 !important;
}

.success {
  color: #16a34a;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.success-banner {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  padding: 0.65rem 0.9rem;
  margin-bottom: 0.75rem;
  color: #15803d;
  font-size: 0.875rem;
}

.success-banner p {
  margin: 0.2rem 0 0;
  font-weight: 400;
}

.muted {
  color: #94a3b8;
}
</style>
