<template>
  <div class="workday-management">
    <h2>Work Day Management</h2>
    <div class="header-actions">
      <el-alert
        title="Click on a day to toggle its status (Off Day / Half Day)."
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
      <template #date-cell="{ data }">
        <div 
          class="custom-date-cell"
          :class="getDayClass(data.day)"
          @click.stop="toggleDayStatus(data.day)"
        >
           <div class="cell-content">
             <div class="date-header">
               <div class="date-number">{{ data.day.split('-').slice(2).join('') }}</div>
               <div class="status-badge" v-if="getStatusLabel(data.day)">{{ getStatusLabel(data.day) }}</div>
             </div>
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
  if (currentType === 'work') {
    nextType = 'off'
  } else if (currentType === 'off') {
    nextType = 'half_off'
  } else if (currentType === 'half_off') {
    nextType = 'work'
  }

  try {
    await api.post('/workdays/', {
      date: dateStr,
      day_type: nextType
    })
    workDays.value = {
      ...workDays.value,
      [dateStr]: nextType
    }
    ElMessage.success(`Set ${dateStr} to ${nextType.toUpperCase()}`)
  } catch (error) {
    console.error('Failed to update workday:', error)
    const msg = error.response?.data?.detail || 'Failed to update workday status'
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
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 8px;
}
.cell-content {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.is-off {
  background-color: #fef0f0 !important; /* Soft Red */
}
.is-half {
  background-color: #fdf6ec !important; /* Soft Orange */
}
.is-work {
  background-color: transparent;
}
.custom-date-cell:hover {
  background-color: #f5f7fa !important;
}
.is-off.custom-date-cell:hover {
  background-color: #fee2e2 !important;
}
.is-half.custom-date-cell:hover {
  background-color: #faecd8 !important;
}

.date-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.date-number {
  font-size: 1.1em;
  font-weight: 500;
  color: #606266;
}
.status-badge {
  font-size: 0.75em;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.is-off .status-badge {
  background-color: #f56c6c;
  color: white;
}
.is-half .status-badge {
  background-color: #e6a23c;
  color: white;
}

/* Hide Weekends (Columns 1 and 7 when Mon is 1st day but rendering forces Sun start) */
:deep(.el-calendar-table thead th:nth-child(1)),
:deep(.el-calendar-table thead th:nth-child(7)),
:deep(.el-calendar-table__row td:nth-child(1)),
:deep(.el-calendar-table__row td:nth-child(7)) {
  display: none !important;
}

/* Override default selected style */
:deep(.el-calendar-table td.is-selected) {
  background-color: transparent !important;
  color: inherit !important;
}
:deep(.el-calendar-table td.is-selected .el-calendar-day) {
   background-color: transparent !important;
}
:deep(.el-calendar-table td.is-selected:hover) {
  background-color: transparent !important;
}

/* Remove default padding to make entire cell clickable */
:deep(.el-calendar-day) {
  padding: 0 !important;
  height: 85px; /* Adjust height as needed */
  display: flex;
  flex-direction: column;
}
</style>
