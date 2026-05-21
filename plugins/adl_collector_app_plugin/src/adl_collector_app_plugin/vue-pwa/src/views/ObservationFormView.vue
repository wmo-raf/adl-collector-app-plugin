<template>
  <div>
    <router-link to="/stations" class="muted" style="font-size:0.875rem">← Back</router-link>
    <h2 style="margin:0.5rem 0 1rem">{{ stationLink?.name || 'Loading…' }}</h2>

    <p v-if="loadError" class="error">{{ loadError }}</p>

    <form v-if="stationLink" @submit.prevent="submit" class="card">
      <label>Observation Time (local)
        <input v-model="obsTimeLocal" type="datetime-local" required />
      </label>

      <div v-for="vm in stationLink.variable_mappings" :key="vm.id" style="margin-top:0.75rem">
        <label>
          {{ vm.adl_parameter_name }}
          <span class="muted" style="font-weight:400"> ({{ vm.obs_parameter_unit }})</span>
          <input v-model.number="values[vm.id]" type="number" step="any"
                 :placeholder="vm.is_rainfall ? 'Accumulation' : ''" />
        </label>
        <p v-if="vm.range_check" class="muted" style="font-size:0.8rem">
          Range: {{ vm.range_check.min }} – {{ vm.range_check.max }}
        </p>
      </div>

      <p v-if="submitError" class="error" style="margin-top:0.75rem">{{ submitError }}</p>
      <p v-if="submitSuccess" class="success" style="margin-top:0.75rem">
        {{ isOffline ? 'Saved offline — will sync when online.' : 'Submitted successfully.' }}
      </p>

      <button class="btn btn-primary btn-full" style="margin-top:1rem" :disabled="submitting">
        {{ submitting ? 'Submitting…' : (isOffline ? 'Save Offline' : 'Submit') }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api'
import { enqueue } from '@/queue'

const route = useRoute()
const stationLink = ref(null)
const loadError = ref(null)
const values = reactive({})
const obsTimeLocal = ref('')
const submitting = ref(false)
const submitError = ref(null)
const submitSuccess = ref(false)
const isOffline = ref(!navigator.onLine)

onMounted(async () => {
  window.addEventListener('online', () => { isOffline.value = false })
  window.addEventListener('offline', () => { isOffline.value = true })
  try {
    stationLink.value = await api.getStationLink(route.params.id)
  } catch (e) {
    loadError.value = e.message
  }
})

function buildPayload() {
  // Append Z so AwareDateTimeField accepts the string
  const obsTime = obsTimeLocal.value
    ? (obsTimeLocal.value.endsWith('Z') ? obsTimeLocal.value : obsTimeLocal.value + ':00Z')
    : null

  const now = new Date().toISOString()
  return {
    station_link_id: stationLink.value.id,
    observation_time: obsTime,
    submission_time: now,
    records: stationLink.value.variable_mappings
      .filter(vm => values[vm.id] !== undefined && values[vm.id] !== '')
      .map(vm => ({ variable_mapping_id: vm.id, value: values[vm.id] })),
  }
}

async function submit() {
  submitError.value = null
  submitSuccess.value = false
  submitting.value = true
  const payload = buildPayload()

  try {
    if (isOffline.value) {
      await enqueue(payload)
    } else {
      await api.submitObservation(payload)
    }
    submitSuccess.value = true
    // Reset values
    Object.keys(values).forEach(k => delete values[k])
    obsTimeLocal.value = ''
  } catch (e) {
    if (!navigator.onLine) {
      // Fell offline mid-submit — queue it
      await enqueue(payload)
      submitSuccess.value = true
      isOffline.value = true
    } else {
      submitError.value = e.data ? JSON.stringify(e.data) : e.message
    }
  } finally {
    submitting.value = false
  }
}
</script>
