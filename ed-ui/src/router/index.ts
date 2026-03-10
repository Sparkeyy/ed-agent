import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Lobby',
      component: () => import('../views/LobbyView.vue'),
    },
    {
      path: '/game/:id',
      name: 'Game',
      component: () => import('../views/GameView.vue'),
    },
    {
      path: '/scores/:id',
      name: 'ScoreScreen',
      component: () => import('../views/ScoreView.vue'),
    },
    {
      path: '/profile/:username',
      name: 'Profile',
      component: () => import('../views/ProfileView.vue'),
    },
    {
      path: '/leaderboard',
      name: 'Leaderboard',
      component: () => import('../views/LeaderboardView.vue'),
    },
    {
      path: '/training',
      name: 'Training',
      component: () => import('../views/TrainingView.vue'),
    },
  ],
})

export default router
