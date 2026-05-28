<template>
  <div>
    <router-link to="/stations" class="muted" style="font-size:0.875rem">← Back</router-link>
    <h2 style="margin:0.5rem 0 1rem">SYNOP FM12 — {{ stationName }}</h2>

    <!-- Step 1: Entry -->
    <div v-if="!decoded" class="card">

      <!-- Non-field errors -->
      <div v-if="decodeErrors.nonField.length" class="error-banner">
        <p v-for="msg in decodeErrors.nonField" :key="msg">{{ msg }}</p>
      </div>

      <label for="synop-raw">
        Raw SYNOP Message
        <textarea id="synop-raw" name="raw_message" v-model="rawMessage" rows="4"
                  :class="{ 'input-error': decodeErrors.fields.raw_message }"
                  placeholder="AAXX 19061 60680 22560 60408 10220 ..."></textarea>
        <span v-if="decodeErrors.fields.raw_message" class="field-error">
          {{ decodeErrors.fields.raw_message.join(' ') }}
        </span>
      </label>

      <div style="display:flex; gap:0.75rem; margin-top:0.75rem">
        <label for="synop-year" style="flex:1">Year
          <select id="synop-year" name="observation_year" v-model="observationYear"
                  :class="{ 'input-error': decodeErrors.fields.observation_year }">
            <option v-for="y in yearChoices" :key="y" :value="y">{{ y }}</option>
          </select>
          <span v-if="decodeErrors.fields.observation_year" class="field-error">
            {{ decodeErrors.fields.observation_year.join(' ') }}
          </span>
        </label>
        <label for="synop-month" style="flex:1">Month
          <select id="synop-month" name="observation_month" v-model="observationMonth"
                  :class="{ 'input-error': decodeErrors.fields.observation_month }">
            <option v-for="m in monthChoices" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
          <span v-if="decodeErrors.fields.observation_month" class="field-error">
            {{ decodeErrors.fields.observation_month.join(' ') }}
          </span>
        </label>
      </div>
      <p class="muted" style="font-size:0.8rem; margin-top:0.25rem">
        Day and hour are read directly from the message.
      </p>

      <button class="btn btn-secondary btn-full" style="margin-top:1rem"
              :disabled="!hasMessage || decoding" @click="decode">
        {{ decoding ? 'Decoding…' : 'Decode & Preview' }}
      </button>
    </div>

    <!-- Step 2: Preview / Success -->
    <div v-else class="card">
      <h3 style="margin-bottom:0.75rem">Decoded Parameters</h3>

      <!-- Success state: stays on this card, shows confirmation + reset button -->
      <template v-if="submitSuccess">
        <div class="success-banner">
          <strong>SYNOP submitted successfully.</strong>
          <p>The message has been archived and queued for ingestion.</p>
        </div>
        <button class="btn btn-secondary btn-full" style="margin-top:1rem" @click="resetForm">
          Submit Another SYNOP
        </button>
      </template>

      <!-- Normal preview state -->
      <template v-else>
        <div style="margin-bottom:1rem; padding:0.75rem; background:#f8fafc; border-radius:6px">
          <p style="margin:0 0 0.5rem; font-size:0.85rem; color:#475569">
            Station ID: <strong>{{ decoded.station_id ?? 'N/A' }}</strong>
          </p>
          <p style="margin:0 0 0.5rem; font-size:0.85rem; color:#475569">
            Observation time:
            <strong v-if="observationTime">{{ observationTime }}</strong>
            <span v-else class="muted">Could not compute — day/hour not found in message.</span>
          </p>
          <p style="margin:0 0 0.5rem; font-size:0.85rem; color:#475569">
            Adjust year/month if incorrect:
          </p>

          <!-- Non-field re-decode errors -->
          <div v-if="decodeErrors.nonField.length" class="error-banner" style="margin-bottom:0.5rem">
            <p v-for="msg in decodeErrors.nonField" :key="msg">{{ msg }}</p>
          </div>

          <div style="display:flex; gap:0.5rem; align-items:flex-end">
            <label style="flex:1; margin:0">Year
              <select v-model="observationYear">
                <option v-for="y in yearChoices" :key="y" :value="y">{{ y }}</option>
              </select>
            </label>
            <label style="flex:1; margin:0">Month
              <select v-model="observationMonth">
                <option v-for="m in monthChoices" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </label>
            <button class="btn btn-secondary" :disabled="decoding" @click="callDecode">
              {{ decoding ? 'Re-decoding…' : 'Re-decode' }}
            </button>
          </div>
        </div>

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

        <!-- Submit errors -->
        <div v-if="submitErrors.nonField.length" class="error-banner" style="margin-top:1rem">
          <p v-for="msg in submitErrors.nonField" :key="msg">{{ msg }}</p>
        </div>

        <div style="display:flex; gap:0.5rem; margin-top:1rem">
          <button class="btn btn-secondary" @click="decoded = null">Edit</button>
          <button class="btn btn-primary" :disabled="!hasMessage || submitting" @click="submit">
            {{ submitting ? 'Submitting…' : 'Confirm & Submit' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import {ref, computed, onMounted} from 'vue'
import {useRoute} from 'vue-router'
import {api} from '@/api'

const route = useRoute()
const stationName = ref('')
const rawMessage = ref('')

const currentYear = new Date().getFullYear()
const observationYear = ref(currentYear)
const observationMonth = ref(new Date().getMonth() + 1)
const observationTime = ref(null)

const yearChoices = Array.from({length: 21}, (_, i) => currentYear - i)
const monthChoices = [
  {value: 1, label: 'January'}, {value: 2, label: 'February'},
  {value: 3, label: 'March'}, {value: 4, label: 'April'},
  {value: 5, label: 'May'}, {value: 6, label: 'June'},
  {value: 7, label: 'July'}, {value: 8, label: 'August'},
  {value: 9, label: 'September'}, {value: 10, label: 'October'},
  {value: 11, label: 'November'}, {value: 12, label: 'December'},
]

const emptyErrors = () => ({nonField: [], fields: {}})

const hasMessage = computed(() => rawMessage.value.trim().length > 0)

const decoding = ref(false)
const decodeErrors = ref(emptyErrors())
const decoded = ref(null)
const submitting = ref(false)
const submitErrors = ref(emptyErrors())
const submitSuccess = ref(false)

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

function resetForm() {
  rawMessage.value = ''
  decoded.value = null
  observationTime.value = null
  observationYear.value = new Date().getFullYear()
  observationMonth.value = new Date().getMonth() + 1
  decodeErrors.value = emptyErrors()
  submitErrors.value = emptyErrors()
  submitSuccess.value = false
}

onMounted(async () => {
  try {
    const sl = await api.getStationLink(route.params.id)
    stationName.value = sl.name
  } catch {
    stationName.value = `Station #${route.params.id}`
  }
})

async function callDecode() {
  decodeErrors.value = emptyErrors()
  decoding.value = true
  try {
    const res = await api.decodeSynop({
      station_link_id: Number(route.params.id),
      raw_message: rawMessage.value,
      observation_year: observationYear.value,
      observation_month: observationMonth.value,
    })
    observationTime.value = res.observation_time || null
    decoded.value = res
  } catch (e) {
    decodeErrors.value = parseErrors(e)
  } finally {
    decoding.value = false
  }
}

function decode() {
  return callDecode()
}

async function submit() {
  submitErrors.value = emptyErrors()
  submitting.value = true
  try {
    await api.submitSynop({
      raw_message: rawMessage.value,
      observation_year: observationYear.value,
      observation_month: observationMonth.value,
    })
    // Stay on Step 2 to show the success state — resetForm() returns to Step 1
    submitSuccess.value = true
  } catch (e) {
    submitErrors.value = parseErrors(e)
  } finally {
    submitting.value = false
  }
}
</script>
