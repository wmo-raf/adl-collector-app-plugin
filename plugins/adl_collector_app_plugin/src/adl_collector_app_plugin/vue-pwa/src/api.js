// API base and token URL are injected by Django via data-* attributes and
// passed into the app as props (see main.js). Fall back to defaults for dev.
let _apiBase = '/api/adl-collector'
let _tokenUrl = '/api/token/'

export function configureApi({apiBase, tokenUrl}) {
    if (apiBase) _apiBase = apiBase
    if (tokenUrl) _tokenUrl = tokenUrl
}

export function getTokenUrl() {
    return _tokenUrl
}

export function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
    return match ? match[1] : null
}

function authHeaders() {
    const token = localStorage.getItem('adl_token')
    return token ? {Authorization: `Token ${token}`} : {}
}

async function request(method, path, body = null) {
    const headers = {'Content-Type': 'application/json', ...authHeaders()}
    if (method !== 'GET' && method !== 'HEAD') {
        const csrf = getCsrfToken()
        if (csrf) headers['X-CSRFToken'] = csrf
    }
    const opts = { method, headers }
    if (body) opts.body = JSON.stringify(body)
    const res = await fetch(`${_apiBase}${path}`, opts)
    if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw Object.assign(new Error(err.detail || `HTTP ${res.status}`), {status: res.status, data: err})
    }
    return res.json()
}

export const api = {
    getStationLinks: () => request('GET', '/station-link/'),
    getStationLink: (id) => request('GET', `/station-link/${id}/`),
    submitObservation: (payload) => request('POST', '/manual-obs/submit/', payload),
    decodeSynop: (payload) => request('POST', '/synop/decode/', payload),
    submitSynop: (payload) => request('POST', '/synop/submit/', payload),
}
