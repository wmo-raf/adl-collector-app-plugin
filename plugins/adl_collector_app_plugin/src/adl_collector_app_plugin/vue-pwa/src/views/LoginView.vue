<template>
  <div class="card">
    <h2 style="margin-bottom:1rem">Sign In</h2>
    <form @submit.prevent="submit">
      <label>Username
        <input v-model="username" type="text" autocomplete="username" required/>
      </label>
      <label>Password
        <input v-model="password" type="password" autocomplete="current-password" required/>
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary btn-full" style="margin-top:1rem" :disabled="loading">
        {{ loading ? 'Signing in…' : 'Sign In' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import {ref} from 'vue'
import {useRouter} from 'vue-router'
import {useAuthStore} from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref(null)

async function submit() {
  loading.value = true
  error.value = null
  try {
    await auth.login(username.value, password.value)
    router.push('/stations')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>
