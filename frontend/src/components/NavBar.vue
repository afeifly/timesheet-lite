<template>
  <el-menu
    :default-active="activeIndex"
    class="el-menu-demo"
    mode="horizontal"
    :ellipsis="false"
    router
  >
    <el-menu-item index="/">
      <span class="logo">SUTO Timesheet</span>
    </el-menu-item>
    
    <div class="flex-grow" />
    
    <el-menu-item index="/">Dashboard</el-menu-item>
    <el-menu-item index="/log-work">Log Work</el-menu-item>
    
    <el-menu-item index="/projects">Projects</el-menu-item>
    <el-menu-item index="/employees">Employees</el-menu-item>
    <el-menu-item index="/reports">Reports</el-menu-item>
    
    <template v-if="authStore.isAdmin">
      <el-menu-item index="/logs">Activity Logs</el-menu-item>
    </template>

    <el-sub-menu index="user" v-if="authStore.user">
      <template #title>{{ authStore.user.username }}</template>
      <el-menu-item @click="showPasswordDialog = true">Change Password</el-menu-item>
      <template v-if="authStore.isAdmin">
        <el-menu-item index="/email-settings">Email Settings</el-menu-item>
      </template>
      <el-menu-item @click="handleLogout">Logout</el-menu-item>
    </el-sub-menu>

    <el-dialog v-model="showPasswordDialog" title="Change Password" width="400px">
      <el-form :model="passwordForm" label-width="140px">
        <el-form-item label="Current Password">
          <el-input v-model="passwordForm.current_password" type="password" />
        </el-form-item>
        <el-form-item label="New Password">
          <el-input v-model="passwordForm.new_password" type="password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showPasswordDialog = false">Cancel</el-button>
          <el-button type="primary" @click="changePassword">Change</el-button>
        </span>
      </template>
    </el-dialog>
  </el-menu>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api/axios'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeIndex = computed(() => route.path)
const showPasswordDialog = ref(false)
const passwordForm = ref({
  current_password: '',
  new_password: ''
})

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

const changePassword = async () => {
  if (passwordForm.value.new_password.length < 6 || passwordForm.value.new_password.length > 16) {
    ElMessage.error('Password must be between 6 and 16 characters')
    return
  }
  try {
    await api.put('/users/me/password', passwordForm.value)
    ElMessage.success('Password changed successfully')
    showPasswordDialog.value = false
    passwordForm.value = { current_password: '', new_password: '' }
  } catch (error) {
    ElMessage.error('Failed to change password: ' + (error.response?.data?.detail || error.message))
  }
}
</script>

<style scoped>
.flex-grow {
  flex-grow: 1;
}
.logo {
  font-weight: bold;
  font-size: 1.2em;
  color: #409EFF;
}
</style>
