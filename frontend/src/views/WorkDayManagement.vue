<template>
  <div class="workday-management">
    <h2>Work Day Management</h2>
    <div class="header-actions">
      <el-alert
        title="White: Work Day | Red: Off Day | Orange: Half Day. Click to toggle."
        type="info"
        show-icon
        :closable="false"
      />
    </div>

    <el-calendar v-model="currentDate" ref="calendar" :first-day-of-week="1">
      <template #header="{ date }">
        <span>{{ date }}</span>
        <el-button-group>
          <el-button size="small" @click="changeMonth(-1)">Previous Month</el-button>
          <el-button size="small" @click="changeMonth(1)">Next Month</el-button>
        </el-button-group>
      </template>
      <template #dateCell="{ data }">
        <div 
          class="custom-date-cell"
          :class="getDayClass(data.day)"
          @click.stop="toggleDayStatus(data.day)"
        >
           <div class="date-header">
             <div class="date-number">{{ data.day.split('-').slice(2).join('') }}</div>
             <div class="status-badge" v-if="getStatusLabel(data.day)">{{ getStatusLabel(data.day) }}</div>
           </div>
        </div>
      </template>
    </el-calendar>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api/axios'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const currentDate = ref(new Date())
const workDays = ref({})
const loading = ref(false)

const loadWorkDays = async () => {
  loading.value = true
  try {
    const start = dayjs(currentDate.value).startOf('month').format('YYYY-MM-01')
    const end = dayjs(currentDate.value).endOf('month').format('YYYY-MM-DD')
    
    // We add some buffer to cover the calendar view grid (usually covers part of prev/next month)
    const viewStart = dayjs(currentDate.value).startOf('month').subtract(7, 'day').format('YYYY-MM-DD')
    const viewEnd = dayjs(currentDate.value).endOf('month').add(7, 'day').format('YYYY-MM-DD')

    const response = await api.get('/workdays/', {
      params: { start_date: viewStart, end_date: viewEnd }
    })
    
    // Map response to object for easy lookup
    const map = {}
    response.data.forEach(item => {
      map[item.date] = item.day_type
    })
    workDays.value = map
  } catch (error) {
    ElMessage.error('Failed to load work days')
  } finally {
    loading.value = false
  }
}

const getDayClass = (dateStr) => {
  const type = workDays.value[dateStr] || 'work'
  return {
    'is-off': type === 'off',
    'is-half': type === 'half_off',
    'is-work': type === 'work'
  }
}

const shouldShowDay = (data) => {
  // Hide Sat (6) and Sun (0)
  // Element plus calendar data.date is a Date object
  const day = dayjs(data.date).day()
  return day !== 0 && day !== 6
}

const getStatusLabel = (dateStr) => {
  const type = workDays.value[dateStr] || 'work'
  if (type === 'off') return 'OFF'
  if (type === 'half_off') return 'HALF'
  return '' 
}

const toggleDayStatus = async (dateStr) => {
  const currentType = workDays.value[dateStr] || 'work'
  let nextType = 'work'
  if (currentType === 'work') nextType = 'off'
  else if (currentType === 'off') nextType = 'half_off'
  else if (currentType === 'half_off') nextType = 'work'

  try {
    await api.post('/workdays/', {
      date: dateStr,
      day_type: nextType
    })
    // Update local state immediately with new object reference for reactivity
    workDays.value = { ...workDays.value, [dateStr]: nextType }
    ElMessage.success(`Set ${dateStr} to ${nextType.toUpperCase()}`)
  } catch (error) {
     const msg = error.response?.data?.detail || 'Failed to update status'
     ElMessage.error(msg)
  }
}

const changeMonth = (delta) => {
  const newDate = dayjs(currentDate.value).add(delta, 'month').toDate()
  currentDate.value = newDate
}

watch(currentDate, () => {
  loadWorkDays()
})

onMounted(() => {
  loadWorkDays()
})
</script>

<style scoped>
.workday-management {
  padding: 20px;
}
.custom-date-cell {
  height: 100%;
  padding: 8px;
  cursor: pointer;
  position: relative;
  transition: background-color 0.2s;
}
.custom-date-cell:hover {
  background-color: #f0f9eb; /* Light green hover for better feedback */
}

/* Status Colors */
.is-off {
  background-color: #fef0f0 !important; /* Light Red */
  color: #f56c6c;
}
.custom-date-cell.is-off:hover {
  background-color: #fab6b6 !important; 
}

.is-half {
  background-color: #faecd8 !important; /* Light Orange */
  color: #e6a23c;
}
.custom-date-cell.is-half:hover {
  background-color: #f5dab1 !important; 
}

.is-work {
  background-color: #ffffff;
}
.custom-date-cell.is-work:hover {
  background-color: #f0f9eb;
}

.date-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.status-badge {
  font-size: 0.8em;
  font-weight: bold;
  padding: 2px 4px;
  border-radius: 4px;
  border: 1px solid currentColor;
}

/* Hide Weekends (Columns 6 and 7 when Mon is 1st day) */
:deep(.el-calendar-table thead th:nth-child(6)),
:deep(.el-calendar-table thead th:nth-child(7)),
:deep(.el-calendar-table__row td:nth-child(6)),
:deep(.el-calendar-table__row td:nth-child(7)) {
  display: none !important;
}

/* Remove default padding to make entire cell clickable */
:deep(.el-calendar-day) {
  padding: 0 !important;
  height: 85px; /* Adjust height as needed */
}
</style>
