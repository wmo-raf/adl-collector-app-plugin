<template>
  <div>
    <router-link to="/stations" class="muted" style="font-size:0.875rem">← Back</router-link>
    <h2 style="margin:0.5rem 0 1rem">{{ stationLink?.name || 'Loading…' }}</h2>

    <p v-if="loadError" class="error">{{ loadError }}</p>

    <form v-if="stationLink" @submit.prevent="submit" class="card">

      <!-- Success banner -->
      <div v-if="submitSuccess" class="success-banner">
        <strong>{{ isOffline ? 'Saved offline.' : 'Submitted successfully.' }}</strong>
        <p>{{ isOffline
          ? 'Your observation has been queued and will sync automatically when back online.'
          : 'Your observation has been recorded.' }}</p>
      </div>

      <!-- Submit error banner -->
      <div v-if="submitErrors.nonField.length" class="error-banner">
        <p v-for="msg in submitErrors.nonField" :key="msg">{{ msg }}</p>
      </div>

      <label for="obs-date">Observation Date (UTC)
        <input id="obs-date" name="obs_date" v-model="obsDate" type="date" required
               :class="{ 'input-error': submitErrors.fields.observation_time }" />
        <span v-if="submitErrors.fields.observation_time" class="field-error">
          {{ submitErrors.fields.observation_time.join(' ') }}
        </span>
      </label>
      <label for="obs-hour" style="margin-top:0.75rem">Observation Hour (UTC)
        <select id="obs-hour" name="obs_hour" v-model.number="obsHour">
          <option v-for="h in 24" :key="h-1" :value="h-1">
            {{ String(h-1).padStart(2, '0') }}:00
          </option>
        </select>
      </label>

      <div v-for="vm in stationLink.variable_mappings" :key="vm.id" style="margin-top:0.75rem">
        <label :for="`field-${vm.id}`">
          {{ vm.adl_parameter_name }}
          <span class="muted" style="font-weight:400"> ({{ vm.obs_parameter_unit }})</span>
          <select v-if="vm.wmo_options"
                  :id="`field-${vm.id}`" :name="`field_${vm.id}`"
                  v-model.number="values[vm.id]">
            <option value="">— Select —</option>
            <option v-for="[code, label] in vm.wmo_options" :key="code" :value="code">{{ label }}</option>
          </select>
          <input v-else
                 :id="`field-${vm.id}`" :name="`field_${vm.id}`"
                 v-model.number="values[vm.id]" type="number" step="any"
                 :placeholder="vm.is_rainfall ? 'Accumulation' : ''" />
        </label>
        <p v-if="vm.range_check" class="muted" style="font-size:0.8rem">
          Range: {{ vm.range_check.min }} – {{ vm.range_check.max }}
        </p>
      </div>

      <button class="btn btn-primary btn-full" style="margin-top:1rem" :disabled="!hasAnyValue || submitting">
        {{ submitting ? 'Submitting…' : (isOffline ? 'Save Offline' : 'Submit') }}
      </button>
    </form>
  </div>
</template>

<script setup>
import {ref, reactive, computed, onMounted} from 'vue'
import {useRoute} from 'vue-router'
import {api} from '@/api'
import {enqueue} from '@/queue'

const route = useRoute()
const stationLink = ref(null)
const loadError = ref(null)
const values = reactive({})
const obsDate = ref(new Date().toISOString().slice(0, 10))
const obsHour = ref(0)
const submitting = ref(false)
const submitErrors = ref({nonField: [], fields: {}})
const submitSuccess = ref(false)
const isOffline = ref(!navigator.onLine)

const emptyErrors = () => ({nonField: [], fields: {}})

const hasAnyValue = computed(() =>
  Object.values(values).some(v => v !== undefined && v !== '' && v !== null)
)

function parseErrors(e) {
  const result = emptyErrors()
  const data = e.data
  if (!data) {
    result.nonField.push(e.message || 'An unexpected error occurred.')
    return result
  }
  for (const [key, value] of Object.entries(data)) {
    const messages = Array.isArray(value) ? value : [String(value)]
    if (key === 'non_field_errors' || key === 'detail') {
      result.nonField.push(...messages)
    } else {
      result.fields[key] = messages
    }
  }
  return result
}

onMounted(async () => {
  window.addEventListener('online', () => {isOffline.value = false})
  window.addEventListener('offline', () => {isOffline.value = true})
  try {
    stationLink.value = await api.getStationLink(route.params.id)
  } catch (e) {
    loadError.value = e.message
  }
})

function buildPayload() {
  const obsTime = obsDate.value
    ? `${obsDate.value}T${String(obsHour.value).padStart(2, '0')}:00:00Z`
    : null

  const now = new Date().toISOString()
  return {
    station_link_id: stationLink.value.id,
    observation_time: obsTime,
    submission_time: now,
    records: stationLink.value.variable_mappings
      .filter(vm => values[vm.id] !== undefined && values[vm.id] !== '')
      .map(vm => ({variable_mapping_id: vm.id, value: values[vm.id]})),
  }
}

async function submit() {
  submitErrors.value = emptyErrors()
  submitSuccess.value = false
  const payload = buildPayload()

  if (payload.records.length === 0) {
    submitErrors.value.nonField.push('Please enter at least one observation value before submitting.')
    return
  }

  submitting.value = true

  try {
    if (isOffline.value) {
      await enqueue(payload)
    } else {
      await api.submitObservation(payload)
    }
    submitSuccess.value = true
    // Reset form fields
    Object.keys(values).forEach(k => delete values[k])
    obsDate.value = new Date().toISOString().slice(0, 10)
    obsHour.value = 0
  } catch (e) {
    if (!navigator.onLine) {
      // Fell offline mid-submit — queue it
      await enqueue(payload)
      isOffline.value = true
      submitSuccess.value = true
    } else {
      submitErrors.value = parseErrors(e)
    }
  } finally {
    submitting.value = false
  }
}
</script>
