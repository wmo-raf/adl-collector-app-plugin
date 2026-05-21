<template>
  <div>
    <router-link to="/stations" class="muted" style="font-size:0.875rem">← Back</router-link>
    <h2 style="margin:0.5rem 0 1rem">SYNOP FM12 — {{ stationName }}</h2>

    <div v-if="!decoded" class="card">
      <label>Raw SYNOP Message
        <textarea v-model="rawMessage" rows="4"
                  placeholder="AAXX 19061 60680 22560 60408 10220 ..."></textarea>
      </label>
      <label>Observation Time (optional, UTC)
        <input v-model="obsTimeLocal" type="datetime-local"/>
        <p class="muted" style="font-size:0.8rem">Leave blank to auto-detect from message.</p>
      </label>
      <p v-if="decodeError" class="error" style="margin-top:0.5rem">{{ decodeError }}</p>
      <button class="btn btn-secondary btn-full" style="margin-top:1rem"
              :disabled="decoding" @click="decode">
        {{ decoding ? 'Decoding…' : 'Decode & Preview' }}
      </button>
    </div>

    <div v-else class="card">
      <h3 style="margin-bottom:0.75rem">Decoded Parameters</h3>
      <table style="width:100%; border-collapse:collapse; font-size:0.9rem">
        <tr v-for="r in decoded.mapped_records" :key="r.fm12_element_path"
            style="border-bottom:1px solid #e2e8f0">
          <td style="padding:0.4rem 0">{{ r.adl_parameter_name }}</td>
          <td style="padding:0.4rem 0; text-align:right; font-family:monospace">
            {{ r.value }} <span class="muted">{{ r.source_unit_name }}</span>
          </td>
        </tr>
      </table>
      <p v-if="!decoded.mapped_records.length" class="muted">
        No parameters could be mapped. Check SYNOP parameter mappings on the connection.
      </p>
      <div style="display:flex; gap:0.5rem; margin-top:1rem">
        <button class="btn btn-secondary" @click="decoded = null">Edit</button>
        <button class="btn btn-primary" :disabled="submitting" @click="submit">
          {{ submitting ? 'Submitting…' : 'Confirm & Submit' }}
        </button>
      </div>
      <p v-if="submitError" class="error" style="margin-top:0.5rem">{{ submitError }}</p>
      <p v-if="submitSuccess" class="success" style="margin-top:0.5rem">SYNOP archived and queued for ingestion.</p>
    </div>
  </div>
</template>

<script setup>
import {ref, onMounted} from 'vue'
import {useRoute} from 'vue-router'
import {api} from '@/api'

const route = useRoute()
const stationName = ref('')
const rawMessage = ref('')
const obsTimeLocal = ref('')
const decoding = ref(false)
const decodeError = ref(null)
const decoded = ref(null)
const submitting = ref(false)
const submitError = ref(null)
const submitSuccess = ref(false)

onMounted(async () => {
  try {
    const sl = await api.getStationLink(route.params.id)
    stationName.value = sl.name
  } catch {
    stationName.value = `Station #${route.params.id}`
  }
})

async function decode() {
  decodeError.value = null
  decoding.value = true
  try {
    const res = await api.decodeSynop({
      station_link_id: Number(route.params.id),
      raw_message: rawMessage.value,
    })
    decoded.value = res
  } catch (e) {
    decodeError.value = e.data ? JSON.stringify(e.data) : e.message
  } finally {
    decoding.value = false
  }
}

async function submit() {
  submitError.value = null
  submitting.value = true
  try {
    const obsTime = obsTimeLocal.value
        ? (obsTimeLocal.value.endsWith('Z') ? obsTimeLocal.value : obsTimeLocal.value + ':00Z')
        : null
    await api.submitSynop({
      station_link_id: Number(route.params.id),
      raw_message: rawMessage.value,
      ...(obsTime ? {observation_time: obsTime} : {}),
    })
    submitSuccess.value = true
    rawMessage.value = ''
    obsTimeLocal.value = ''
    decoded.value = null
  } catch (e) {
    submitError.value = e.data ? JSON.stringify(e.data) : e.message
  } finally {
    submitting.value = false
  }
}
</script>
