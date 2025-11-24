<template>
  <div class="log-work">
    <el-container>
      <el-main>
        <el-card class="timesheet-card">
          <div class="timesheet-header">
            <h3>Log Work (Mon - Fri)</h3>
            <div class="week-navigation">
              <el-button @click="changeWeek(-1)">Previous Week</el-button>
              <span class="week-range">{{ weekRange }}</span>
              <el-button @click="changeWeek(1)" :disabled="isCurrentWeek">Next Week</el-button>
            </div>
          </div>

          <!-- Header Row -->
          <div class="header-row">
            <div class="project-info-header">Project</div>
            <div class="days-header">
              <div v-for="(day, index) in weekDays" :key="index" class="day-header-item">
                {{ day.label }}
              </div>
            </div>
            <div class="total-header">Total</div>
          </div>

          <div v-for="project in projectRows" :key="project.id" class="project-row-wrapper">
            <div class="project-row">
              <div class="project-info">
                <h4>
                  {{ project.name }} 
                  <el-tag v-if="project.is_assigned" size="small" type="success">Assigned</el-tag>
                </h4>
              </div>
              <div class="days-container">
                <div v-for="(day, index) in weekDays" :key="index" class="day-column">
                  <!-- Removed day-label here -->
                  <div class="slider-wrapper" :style="{ width: getSliderWidth(index, project.hours[index]) }">
                    <el-slider 
                      v-model="project.hours[index]" 
                      :min="0" 
                      :max="getMaxHours(index, project.hours[index])" 
                      :step="0.5" 
                      show-stops
                      @change="handleHoursChange(project.id, day.date, project.hours[index])"
                    />
                  </div>
                  <div class="hours-display">{{ project.hours[index] }}h</div>
                </div>
              </div>
              <div class="project-total">
                {{ project.hours.reduce((a, b) => a + (b || 0), 0) }}h
              </div>
            </div>
            <el-divider />
          </div>

          <div class="summary-section">
            <div class="daily-totals">
              <h4>Daily Totals</h4>
              <div class="totals-grid">
                <div class="total-label-placeholder"></div> <!-- Spacer to align with project-info -->
                <div class="days-container-totals">
                  <div v-for="(day, index) in weekDays" :key="index" class="total-item">
                    <span class="day-name">{{ day.label }}</span>
                    <span :class="['total-value', { 'warning': getDailyTotal(index) !== 8 }]">
                      {{ getDailyTotal(index) }}h
                    </span>
                  </div>
                </div>
                <div class="total-spacer"></div>
              </div>
            </div>
            
            <div class="weekly-total">
              <strong>Weekly Total: {{ getWeeklyTotal() }} / 40h</strong>
              <el-progress 
                :percentage="Math.min((getWeeklyTotal() / 40) * 100, 100)" 
                :status="getWeeklyTotal() > 40 ? 'exception' : (getWeeklyTotal() === 40 ? 'success' : '')"
              />
              <el-alert v-if="getWeeklyTotal() > 40" title="Weekly limit exceeded!" type="error" show-icon :closable="false" class="mt-2" />
            </div>
          </div>

          <div class="actions">
            <el-button type="primary" size="large" @click="saveTimesheet" :loading="saving">Save Changes</el-button>
          </div>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../api/axios'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const authStore = useAuthStore()
const saving = ref(false)

const currentDate = ref(dayjs())
const projects = ref([])
const timesheets = ref([])
const projectRows = ref([])

const weekDays = computed(() => {
  const startOfWeek = currentDate.value.startOf('week').add(1, 'day') // Monday
  // Only 5 days (Mon-Fri)
  return Array.from({ length: 5 }, (_, i) => {
    const d = startOfWeek.add(i, 'day')
    return {
      label: d.format('ddd D/M'),
      date: d.format('YYYY-MM-DD')
    }
  })
})

const weekRange = computed(() => {
  const start = weekDays.value[0].date
  const end = weekDays.value[4].date
  return `${start} - ${end}`
})

const isCurrentWeek = computed(() => {
  const today = dayjs()
  const startOfCurrentWeek = today.startOf('week').add(1, 'day')
  const startOfDisplayedWeek = currentDate.value.startOf('week').add(1, 'day')
  return startOfDisplayedWeek.isSame(startOfCurrentWeek, 'day') || startOfDisplayedWeek.isAfter(startOfCurrentWeek)
})


const changeWeek = (offset) => {
  currentDate.value = currentDate.value.add(offset, 'week')
  fetchData()
}

const fetchData = async () => {
  try {
    const [pRes, tRes] = await Promise.all([
      api.get('/projects/'),
      api.get('/timesheets/', {
        params: {
          start_date: weekDays.value[0].date,
          end_date: weekDays.value[4].date
        }
      })
    ])
    
    projects.value = pRes.data
    timesheets.value = tRes.data
    
    // Sort projects: Non-default (Assigned) > Default.
    const sortedProjects = [...projects.value].sort((a, b) => {
        if (a.is_default === b.is_default) return 0;
        return a.is_default ? 1 : -1; 
    })
    
    // Build grid
    projectRows.value = sortedProjects.map(p => {
      const hours = weekDays.value.map(day => {
        const entry = timesheets.value.find(t => t.project_id === p.id && t.date === day.date)
        return entry ? entry.hours : 0
      })
      return {
        id: p.id,
        name: p.name,
        is_assigned: !p.is_default, // Approximation for UI
        hours
      }
    })
  } catch (error) {
    ElMessage.error('Failed to load data')
  }
}

const getDailyTotal = (dayIndex) => {
  return projectRows.value.reduce((sum, row) => sum + (row.hours[dayIndex] || 0), 0)
}

const getWeeklyTotal = () => {
  return projectRows.value.reduce((sum, row) => sum + row.hours.reduce((a, b) => a + (b || 0), 0), 0)
}

const getMaxHours = (dayIndex, currentHours) => {
  const dailyTotal = getDailyTotal(dayIndex)
  const otherProjectsTotal = dailyTotal - currentHours
  const remainingHours = 8 - otherProjectsTotal
  return Math.max(0, Math.min(remainingHours, 8))
}

const getSliderWidth = (dayIndex, currentHours) => {
  const maxHours = getMaxHours(dayIndex, currentHours)
  // Calculate width as percentage of 8 hours
  // If max is 8, width is 100%, if max is 1, width is 12.5%
  const widthPercentage = (maxHours / 8) * 100
  return `${widthPercentage}%`
}

const handleHoursChange = (projectId, date, hours) => {
  // Optional: Real-time validation
}

const saveTimesheet = async () => {
  saving.value = true
  try {
    const promises = []
    for (const row of projectRows.value) {
      row.hours.forEach((h, index) => {
        if (h >= 0) {
           const date = weekDays.value[index].date
           if (h > 0 || timesheets.value.some(t => t.project_id === row.id && t.date === date && t.hours > 0)) {
               promises.push(api.post('/timesheets/', {
                 user_id: authStore.user.id,
                 project_id: row.id,
                 date: date,
                 hours: h
               }))
           }
        }
      })
    }
    
    await Promise.all(promises)
    ElMessage.success('Timesheet saved')
    fetchData() // Refresh
  } catch (error) {
    ElMessage.error('Failed to save: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.timesheet-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.week-range {
  margin: 0 20px;
  font-weight: bold;
  font-size: 1.1em;
}

/* New Header Row Styles */
.header-row {
  display: flex;
  align-items: center;
  background-color: #f5f7fa;
  padding: 10px 0;
  border-radius: 4px;
  margin-bottom: 10px;
  font-weight: bold;
  color: #606266;
  padding-right: 0; /* Match row padding */
}
.project-info-header {
  width: 200px; /* Match project-info width */
  padding-left: 10px;
  flex-shrink: 0;
}
.days-header {
  display: flex;
  flex: 1;
  gap: 20px;
}
.day-header-item {
  flex: 1;
  text-align: center;
  min-width: 120px;
}
.total-header {
  width: 80px;
  text-align: right;
  padding-right: 10px;
  flex-shrink: 0;
}

.project-row-wrapper {
  margin-bottom: 0;
}

.project-row {
  display: flex;
  align-items: flex-start;
  padding: 10px 0;
  /* border-bottom moved to divider */
}
.project-info {
  width: 200px;
  padding-right: 10px; /* Adjusted to match header spacing better */
  padding-left: 10px; /* Added to match header padding-left */
  display: flex;
  align-items: center;
  flex-shrink: 0;
  box-sizing: border-box; /* Ensure padding doesn't add to width if not already set globally */
}
.days-container {
  display: flex;
  flex: 1;
  gap: 20px;
}
.day-column {
  flex: 1;
  min-width: 120px;
  text-align: center;
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  align-items: flex-start; /* Changed from center to flex-start for left alignment */
}
.slider-wrapper {
  width: 100%;
  transition: width 0.3s ease;
}
.hours-display {
  margin-top: 5px;
  font-weight: bold;
  color: #409EFF;
  font-size: 0.9em;
}
.project-total {
  width: 80px;
  text-align: right;
  font-weight: bold;
  color: #67C23A;
  padding-top: 10px;
  padding-right: 10px; /* Match header padding-right */
  flex-shrink: 0;
  box-sizing: border-box;
}

.summary-section {
  background-color: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-top: 30px;
}
.totals-grid {
  display: flex;
  align-items: center;
}
.total-label-placeholder {
  width: 200px;
  flex-shrink: 0;
}
.days-container-totals {
  display: flex;
  flex: 1;
  gap: 20px;
}
.total-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: white;
  padding: 10px;
  border-radius: 4px;
  flex: 1;
  min-width: 120px;
}
.total-spacer {
  width: 80px;
  flex-shrink: 0;
}

.total-value {
  font-size: 1.2em;
  font-weight: bold;
  color: #67C23A;
}
.total-value.warning {
  color: #E6A23C;
}
.weekly-total {
  margin-top: 20px;
}
.mt-2 {
  margin-top: 10px;
}
.actions {
  margin-top: 30px;
  text-align: right;
}
</style>
