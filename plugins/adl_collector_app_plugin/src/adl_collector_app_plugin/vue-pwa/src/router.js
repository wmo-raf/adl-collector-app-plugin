import {createRouter, createWebHashHistory} from 'vue-router'
import {useAuthStore} from '@/stores/auth'

import LoginView from '@/views/LoginView.vue'
import StationListView from '@/views/StationListView.vue'
import ObservationFormView from '@/views/ObservationFormView.vue'
import SynopFormView from '@/views/SynopFormView.vue'
import PendingView from '@/views/PendingView.vue'

const routes = [
    {path: '/', redirect: '/stations'},
    {path: '/login', component: LoginView, meta: {public: true}},
    {path: '/stations', component: StationListView},
    {path: '/stations/:id/observe', component: ObservationFormView},
    {path: '/stations/:id/synop', component: SynopFormView},
    {path: '/pending', component: PendingView},
]

const router = createRouter({
    history: createWebHashHistory(),
    routes,
})

router.beforeEach((to) => {
    const auth = useAuthStore()
    if (!to.meta.public && !auth.isLoggedIn) return '/login'
})

export default router
