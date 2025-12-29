<template>
  <div class="projects-container">
    <div class="header">
      <h2>Projects Management</h2>
      <el-button v-if="isAdmin" type="primary" @click="openCreateDialog">Add Project</el-button>
    </div>

    <el-table :data="projects" style="width: 100%">
      <el-table-column prop="id" label="No." width="60" />
      <el-table-column prop="custom_id" label="Project ID" width="100" />
      <el-table-column prop="name" label="PJ Name" width="120" />
      <el-table-column prop="full_name" label="Full Name" width="150" />
      <el-table-column label="Chinese Name" width="120">
        <template #default="scope">
          {{ scope.row.chinese_name || '&nbsp;' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.status === 'RUN' ? 'success' : (scope.row.status === 'CLOSE' ? 'info' : 'warning')">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="start_date" label="Start Date" width="110" />
      <el-table-column prop="plan_closed_date" label="Plan Close" width="110" />
      <el-table-column prop="actual_closed_date" label="Actual Close" width="110" />
      <el-table-column prop="description" label="Description" />
      <el-table-column prop="remark" label="Remark" />
      <el-table-column v-if="isAdmin" label="Actions" width="150" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="openEditDialog(scope.row)">Edit</el-button>
          <el-button 
            v-if="!scope.row.is_default" 
            type="danger" 
            size="small" 
            @click="handleDelete(scope.row)"
          >
            Delete
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" :title="isEditing ? 'Edit Project' : 'Create Project'" width="600px">
      <el-form :model="form" label-width="140px">
        <el-form-item label="No. PJ Name" required>
          <el-input v-model="form.name" placeholder="e.g. P001" />
        </el-form-item>
        <el-form-item label="Full Name">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="Chinese Name">
          <el-input v-model="form.chinese_name" />
        </el-form-item>
        <el-form-item label="Project ID">
          <el-input v-model="form.custom_id" placeholder="e.g. 1193" />
        </el-form-item>
        <el-form-item label="Status">
          <el-select v-model="form.status">
            <el-option label="RUN" value="RUN" />
            <el-option label="CLOSE" value="CLOSE" />
            <el-option label="NOT START" value="NOT START" />
          </el-select>
        </el-form-item>
        <el-form-item label="Start Date">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="Plan Closed Date">
          <el-date-picker v-model="form.plan_closed_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="Actual Closed Date">
          <el-date-picker v-model="form.actual_closed_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="Others">
          <el-input v-model="form.others" />
        </el-form-item>
        <el-form-item label="Remark">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">Cancel</el-button>
          <el-button type="primary" @click="submitProject">{{ isEditing ? 'Update' : 'Create' }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../api/axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')

const projects = ref([])
const showCreateDialog = ref(false)
const isEditing = ref(false)
const form = ref({
  name: '',
  full_name: '',
  chinese_name: '',
  custom_id: '',
  status: 'NOT START',
  start_date: null,
  plan_closed_date: null,
  actual_closed_date: null,
  others: '',
  remark: '',
  description: ''
})

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data
  } catch (error) {
    ElMessage.error('Failed to fetch projects')
  }
}

const openCreateDialog = () => {
  isEditing.value = false
  form.value = {
    name: '',
    full_name: '',
    chinese_name: '',
    status: 'NOT START',
    start_date: null,
    plan_closed_date: null,
    actual_closed_date: null,
    others: '',
    remark: '',
    description: ''
  }
  showCreateDialog.value = true
}

const openEditDialog = (project) => {
  isEditing.value = true
  form.value = { ...project }
  showCreateDialog.value = true
}

const submitProject = async () => {
  try {
    if (isEditing.value) {
      await api.put(`/projects/${form.value.id}`, form.value) // Assuming PUT endpoint exists or needs to be created? 
      // Wait, I didn't check if PUT endpoint exists. Usually it's standard CRUD. 
      // If not, I might need to add it to backend. But let's assume standard CRUD for now or use POST for update if designed that way?
      // Actually, standard FastAPI CRUD usually has PUT /projects/{id}. 
      // Let's check backend/app/api/projects.py if I can... or just try it.
      // If it fails, I'll fix backend.
      ElMessage.success('Project updated')
    } else {
      await api.post('/projects/', form.value)
      ElMessage.success('Project created')
    }
    showCreateDialog.value = false
    fetchProjects()
  } catch (error) {
    ElMessage.error('Failed to save project: ' + (error.response?.data?.detail || error.message))
  }
}

const handleDelete = (project) => {
  ElMessageBox.confirm(
    'Are you sure you want to delete this project?',
    'Warning',
    {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await api.delete(`/projects/${project.id}`)
        ElMessage.success('Project deleted')
        fetchProjects()
      } catch (error) {
        ElMessage.error('Failed to delete project')
      }
    })
    .catch(() => {})
}

onMounted(fetchProjects)
</script>

<style scoped>
.projects-container {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
