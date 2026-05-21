import {defineStore} from 'pinia'
import {getTokenUrl, getCsrfToken} from '@/api'

export const useAuthStore = defineStore('auth', {
    state: () => ({
        token: localStorage.getItem('adl_token') || null,
        username: localStorage.getItem('adl_username') || null,
        error: null,
    }),
    getters: {
        isLoggedIn: (s) => !!s.token,
    },
    actions: {
        async login(username, password) {
            this.error = null
            const csrf = getCsrfToken()
            const res = await fetch(getTokenUrl(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(csrf ? {'X-CSRFToken': csrf} : {}),
                },
                body: JSON.stringify({username, password}),
            })
            const data = await res.json()
            if (!data.access) {
                this.error = data.non_field_errors?.[0] || 'Login failed'
                throw new Error(this.error)
            }
            this.token = data.access
            this.username = username
            localStorage.setItem('adl_token', data.access)
            localStorage.setItem('adl_username', username)
        },
        logout() {
            this.token = null
            this.username = null
            localStorage.removeItem('adl_token')
            localStorage.removeItem('adl_username')
        },
    },
})
