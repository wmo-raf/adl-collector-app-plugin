<template>
  <div>
    <h2 style="margin-bottom:1rem">Offline Queue</h2>
    <p class="muted" style="margin-bottom:1rem">
      Submissions saved while offline. They sync automatically when you go online.
    </p>

    <p v-if="!items.length" class="card muted">No pending submissions.</p>

    <div v-for="item in items" :key="item.localId" class="card">
      <strong>Station #{{ item.station_link_id }}</strong>
      <span class="muted" style="font-size:0.8rem; margin-left:0.5rem">{{ item.observation_time }}</span>
      <div style="font-size:0.85rem; margin-top:0.25rem">
        {{ item.records?.length || 0 }} parameter(s)
      </div>
      <div style="margin-top:0.5rem; display:flex; gap:0.5rem">
        <button class="btn btn-primary" :disabled="syncing" @click="syncOne(item)">
          Sync now
        </button>
        <button class="btn btn-secondary" @click="discard(item.localId)">
          Discard
        </button>
      </div>
      <p v-if="syncErrors[item.localId]" class="error">{{ syncErrors[item.localId] }}</p>
    </div>

    <button v-if="items.length" class="btn btn-primary btn-full" :disabled="syncing"
            style="margin-top:0.5rem" @click="syncAll">
      {{ syncing ? 'Syncing…' : 'Sync All' }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listPending, dequeue, flushQueue } from '@/queue'
import { api } from '@/api'

const items = ref([])
const syncing = ref(false)
const syncErrors = ref({})

onMounted(refresh)

async function refresh() {
  items.value = await listPending()
}

async function syncOne(item) {
  syncing.value = true
  syncErrors.value[item.localId] = null
  try {
    await api.submitObservation(item)
    await dequeue(item.localId)
    await refresh()
  } catch (e) {
    syncErrors.value[item.localId] = e.data ? JSON.stringify(e.data) : e.message
  } finally {
    syncing.value = false
  }
}

async function syncAll() {
  syncing.value = true
  const results = await flushQueue((item) => api.submitObservation(item))
  results.forEach(r => {
    if (r.status === 'error') {
      syncErrors.value[r.localId] = r.err?.message || 'Error'
    }
  })
  await refresh()
  syncing.value = false
}

async function discard(localId) {
  await dequeue(localId)
  await refresh()
}
</script>
