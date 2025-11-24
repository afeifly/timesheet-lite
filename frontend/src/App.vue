<template>
  <NavBar v-if="!isLoginPage" />
  <router-view />
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import NavBar from './components/NavBar.vue'

const route = useRoute()
const authStore = useAuthStore()
const isLoginPage = computed(() => route.name === 'login')

onMounted(() => {
  if (authStore.token) {
    authStore.decodeToken()
  }
})
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>
