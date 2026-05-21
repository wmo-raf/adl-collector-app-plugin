/**
 * Offline submission queue backed by IndexedDB via the `idb` library.
 * Queued submissions are retried automatically when the app goes online.
 */
import {openDB} from 'idb'

const DB_NAME = 'adl-observer'
const STORE = 'pending-submissions'
const DB_VERSION = 1

let _db = null

async function getDb() {
    if (_db) return _db
    _db = await openDB(DB_NAME, DB_VERSION, {
        upgrade(db) {
            db.createObjectStore(STORE, {keyPath: 'localId', autoIncrement: true})
        },
    })
    return _db
}

export async function enqueue(payload) {
    const db = await getDb()
    return db.add(STORE, {...payload, queuedAt: new Date().toISOString()})
}

export async function listPending() {
    const db = await getDb()
    return db.getAll(STORE)
}

export async function dequeue(localId) {
    const db = await getDb()
    return db.delete(STORE, localId)
}

export async function flushQueue(submitFn) {
    const pending = await listPending()
    const results = []
    for (const item of pending) {
        try {
            const res = await submitFn(item)
            await dequeue(item.localId)
            results.push({localId: item.localId, status: 'ok', res})
        } catch (err) {
            results.push({localId: item.localId, status: 'error', err})
        }
    }
    return results
}
