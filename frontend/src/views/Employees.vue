<template>
  <div class="employees-container">
    <div class="header">
      <h2>Employees Management</h2>
      <el-button v-if="isAdmin" type="primary" @click="openCreateDialog">Add Employee</el-button>
    </div>

    <el-table :data="users" style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="Username (Login)" min-width="120" />
      <el-table-column prop="email" label="Email" min-width="180" />
      <el-table-column prop="full_name" label="Full Name" min-width="150" />
      <el-table-column prop="cost_center" label="Cost Center" width="120" />
      <el-table-column prop="remark" label="Mark" min-width="120" />
      <el-table-column prop="start_date" label="Start Date" width="110" />
      <el-table-column prop="end_date" label="End Date" width="110" />
      <el-table-column prop="role" label="Role" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'success'">{{ scope.row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="isAdmin" label="Actions" width="280" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="openEditDialog(scope.row)">Edit</el-button>
          <el-button 
            type="primary" 
            size="small" 
            @click="openProjectDialog(scope.row)"
          >
            Projects
          </el-button>
          <el-button 
            v-if="scope.row.username !== authStore.user?.username" 
            type="danger" 
            size="small" 
            @click="handleDelete(scope.row)"
          >
            Delete
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" :title="isEditing ? 'Edit Employee' : 'Create Employee'" width="600px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="Username" required>
          <el-input v-model="form.username" :disabled="isEditing" />
        </el-form-item>
        <el-form-item label="Full Name">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="Email">
          <el-input v-model="form.email" placeholder="user@example.com" />
        </el-form-item>
        <el-form-item label="Cost Center">
          <el-select v-model="form.cost_center" placeholder="Select Cost Center">
            <el-option label="R&D-XA" value="R&D-XA" />
            <el-option label="R&D-SZ" value="R&D-SZ" />
          </el-select>
        </el-form-item>
        <el-form-item label="Mark">
          <el-input v-model="form.remark" />
        </el-form-item>
        <el-form-item label="Start Date">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="End Date">
          <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="Password" v-if="!isEditing" required>
          <el-input v-model="form.password" type="password" />
        </el-form-item>
        <el-form-item label="Role">
          <el-select v-model="form.role" placeholder="Select role">
            <el-option label="Employee" value="employee" />
            <el-option label="Team Leader" value="team_leader" />
            <el-option label="Admin" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="Team Leader" v-if="form.role === 'employee'">
          <el-select v-model="form.team_leader_id" placeholder="Select Team Leader" clearable>
            <el-option 
              v-for="tl in teamLeaders" 
              :key="tl.id" 
              :label="tl.username" 
              :value="tl.id" 
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">Cancel</el-button>
          <el-button type="primary" @click="submitUser">{{ isEditing ? 'Update' : 'Create' }}</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog v-model="showProjectDialog" title="Assign Projects">
      <p>Assign projects to <strong>{{ selectedUser?.username }}</strong></p>
      <div class="project-list">
        <el-checkbox-group v-model="selectedProjects">
          <el-checkbox 
            v-for="project in allProjects" 
            :key="project.id" 
            :label="project.id"
            :disabled="project.is_default"
          >
            {{ project.name }} <span v-if="project.is_default">(Default)</span>
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showProjectDialog = false">Cancel</el-button>
          <el-button type="primary" @click="saveProjectAssignments">Save</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../api/axios'
import { useAuthStore } from '../stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')
const users = ref([])
const teamLeaders = computed(() => users.value.filter(u => u.role === 'team_leader'))
const allProjects = ref([])
const showCreateDialog = ref(false)
const showProjectDialog = ref(false)
const isEditing = ref(false)
const selectedUser = ref(null)
const selectedProjects = ref([])

const form = ref({
  username: '',
  email: '',
  full_name: '',
  cost_center: '',
  remark: '',
  start_date: null,
  end_date: null,
  start_date: null,
  end_date: null,
  password: '',
  role: 'employee',
  team_leader_id: null
})

const fetchUsers = async () => {
  try {
    const response = await api.get('/users/')
    users.value = response.data
  } catch (error) {
    ElMessage.error('Failed to fetch users')
  }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    allProjects.value = response.data
  } catch (error) {
    console.error(error)
  }
}

const openCreateDialog = () => {
  isEditing.value = false
  form.value = {
    username: '',
    email: '',
    full_name: '',
    cost_center: '',
    remark: '',
    start_date: null,
    end_date: null,
    password: '',
    end_date: null,
    password: '',
    role: 'employee',
    team_leader_id: null
  }
  showCreateDialog.value = true
}

const openEditDialog = (user) => {
  isEditing.value = true
  form.value = { ...user, password: '' }
  showCreateDialog.value = true
}

const submitUser = async () => {
  try {
    if (isEditing.value) {
      await api.put(`/users/${form.value.id}`, form.value)
      ElMessage.success('User updated')
    } else {
      const userData = {
        username: form.value.username,
        email: form.value.email,
        full_name: form.value.full_name,
        cost_center: form.value.cost_center,
        remark: form.value.remark,
        start_date: form.value.start_date,
        end_date: form.value.end_date,
        password_hash: form.value.password,
        start_date: form.value.start_date,
        end_date: form.value.end_date,
        password_hash: form.value.password,
        role: form.value.role,
        team_leader_id: form.value.team_leader_id
      }
      await api.post('/users/', userData)
      ElMessage.success('User created')
    }
    showCreateDialog.value = false
    fetchUsers()
  } catch (error) {
    ElMessage.error('Failed to save user: ' + (error.response?.data?.detail || error.message))
  }
}

const handleDelete = (user) => {
  ElMessageBox.confirm(
    'Are you sure you want to delete this user?',
    'Warning',
    {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await api.delete(`/users/${user.id}`)
        ElMessage.success('User deleted')
        fetchUsers()
      } catch (error) {
        ElMessage.error('Failed to delete user')
      }
    })
    .catch(() => {})
}

const openProjectDialog = async (user) => {
  selectedUser.value = user
  try {
    const response = await api.get(`/users/${user.id}/projects`)
    const assigned = response.data.map(p => p.id)
    selectedProjects.value = assigned
    showProjectDialog.value = true
  } catch (error) {
    ElMessage.error('Failed to fetch user projects')
  }
}

const saveProjectAssignments = async () => {
  try {
    const currentRes = await api.get(`/users/${selectedUser.value.id}/projects`)
    const currentIds = currentRes.data.map(p => p.id)
    const newIds = selectedProjects.value
    
    const toAdd = newIds.filter(id => !currentIds.includes(id))
    const toRemove = currentIds.filter(id => !newIds.includes(id))
    
    const promises = []
    for (const id of toAdd) {
      promises.push(api.post(`/users/${selectedUser.value.id}/projects/${id}`))
    }
    for (const id of toRemove) {
      const proj = allProjects.value.find(p => p.id === id)
      if (proj && !proj.is_default) {
        promises.push(api.delete(`/users/${selectedUser.value.id}/projects/${id}`))
      }
    }
    
    await Promise.all(promises)
    ElMessage.success('Assignments updated')
    showProjectDialog.value = false
  } catch (error) {
    ElMessage.error('Failed to update assignments')
  }
}

onMounted(() => {
  fetchUsers()
  fetchProjects()
})
</script>

<style scoped>
.employees-container {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.project-list {
  max-height: 300px;
  overflow-y: auto;
  margin: 20px 0;
}
</style>
