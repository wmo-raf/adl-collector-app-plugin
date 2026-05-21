<template>
  <div>
    <h2 style="margin-bottom:1rem">My Stations</h2>
    <p v-if="loading" class="muted">Loading…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <div v-else>
      <div v-for="sl in stations" :key="sl.id" class="card">
        <strong>{{ sl.name }}</strong>
        <div style="margin-top:0.75rem; display:flex; gap:0.5rem">
          <router-link :to="`/stations/${sl.id}/observe`" class="btn btn-primary">
            Enter Values
          </router-link>
          <router-link :to="`/stations/${sl.id}/synop`" class="btn btn-secondary">
            SYNOP
          </router-link>
        </div>
      </div>
      <p v-if="!stations.length" class="muted">No stations assigned to you.</p>
    </div>
  </div>
</template>

<script setup>
import {ref, onMounted} from 'vue'
import {api} from '@/api'

const stations = ref([])
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    stations.value = await api.getStationLinks()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>
