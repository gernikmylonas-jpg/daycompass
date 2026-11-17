import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import HomeView from '../views/HomeView.vue'
import CalendarView from '../views/CalendarView.vue'
import PomodoroView from '../views/PomodoroView.vue'
import GroupsView from '../views/GroupsView.vue'
import WellnessView from '../views/WellnessView.vue'
import ProgressView from '../views/ProgressView.vue'
import ProfileView from '../views/ProfileView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView, meta: { requiresAuth: true } },
    { path: '/calendar', component: CalendarView, meta: { requiresAuth: true } },
    { path: '/pomodoro', component: PomodoroView, meta: { requiresAuth: true } },
    { path: '/groups', component: GroupsView, meta: { requiresAuth: true } },
    { path: '/wellness', component: WellnessView, meta: { requiresAuth: true } },
    { path: '/progress', component: ProgressView, meta: { requiresAuth: true } },
    { path: '/profile', component: ProfileView, meta: { requiresAuth: true } },
    { path: '/login', component: LoginView },
    { path: '/register', component: RegisterView },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) return '/login'
})

export default router
