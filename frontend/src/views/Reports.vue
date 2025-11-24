<template>
  <div class="reports-container">
    <h2>Reports & Statistics</h2>
    
    <el-row v-if="isAdmin" :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>Total Users</template>
          <div class="stat-value">{{ stats.total_users }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>Total Projects</template>
          <div class="stat-value">{{ stats.total_projects }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="report-card">
      <template #header>
        <div class="card-header">
          <span>Report</span>
          <el-button type="primary" @click="exportReport">Export Excel</el-button>
        </div>
      </template>
      
      <el-table :data="reportData.users" border stripe max-height="600">
        <el-table-column prop="full_name" label="Full Name" width="150" fixed />
        <el-table-column prop="cost_center" label="Cost Center" width="120" />
        
        <!-- Dynamic project columns with multi-line headers -->
        <el-table-column 
          v-for="project in reportData.projects" 
          :key="project.id" 
          width="120"
          align="center"
        >
          <template #header>
            <!-- Default project: single line -->
            <div v-if="project.is_default" class="project-header">
              <div class="project-header-line">{{ project.name }}</div>
            </div>
            <!-- Custom project: four lines with borders -->
            <div v-else class="project-header custom-project">
              <div class="project-header-line with-border">{{ project.full_name || project.name }}</div>
              <div class="project-header-line with-border">{{ project.chinese_name }}</div>
              <div class="project-header-line with-border">{{ project.custom_id || project.id }}</div>
              <div class="project-header-line time-range">
                {{ formatDateRange(project.start_date, project.plan_closed_date) }}
              </div>
            </div>
          </template>
          <template #default="scope">
            {{ scope.row.projects[project.name] || 0 }}h
          </template>
        </el-table-column>
        
        <el-table-column prop="total_hours" label="Total Hours" width="100" sortable align="center">
          <template #default="scope">
            <strong>{{ scope.row.total_hours }}h</strong>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="Mark" width="100" />
        <el-table-column prop="start_date" label="Start Date" width="110" />
        <el-table-column prop="end_date" label="End Date" width="110" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../api/axios'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import dayjs from 'dayjs'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')

const stats = ref({ total_users: 0, total_projects: 0 })
const reportData = ref({ users: [], projects: [] })

const formatDateRange = (startDate, endDate) => {
  if (!startDate && !endDate) return ''
  if (!startDate) return `~ ${endDate}`
  if (!endDate) return `${startDate} ~`
  return `${startDate} ~ ${endDate}`
}

const fetchStats = async () => {
  try {
    const response = await api.get('/reports/stats')
    stats.value = response.data
  } catch (error) {
    console.error(error)
  }
}

const fetchReport = async () => {
  try {
    // Fetch all data without date filtering
    const response = await api.get('/reports/weekly', {
      params: {
        start_date: '2000-01-01',
        end_date: '2099-12-31'
      }
    })
    reportData.value = response.data
  } catch (error) {
    ElMessage.error('Failed to fetch report')
  }
}

const exportReport = async () => {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet('Report');

  // Define columns widths without setting worksheet.columns (which creates a header row)
  const setColWidth = (colIndex, width) => {
    worksheet.getColumn(colIndex).width = width;
  };

  setColWidth(1, 20); // Full Name
  setColWidth(2, 15); // Cost Center
  
  let colIdx = 3;
  reportData.value.projects.forEach(p => {
    setColWidth(colIdx, 20); // Project columns
    colIdx++;
  });
  
  setColWidth(colIdx, 12); // Total Hours
  setColWidth(colIdx + 1, 15); // Mark
  setColWidth(colIdx + 2, 12); // Start Date
  setColWidth(colIdx + 3, 12); // End Date


  // --- Header Construction ---
  // We have 6 header rows
  // Row 1: Full Name, Cost Center, [Project Names/Full Names], Total Hours...
  // Row 2: [Chinese Names]
  // Row 3: [Chinese Names continued/merged]
  // Row 4: [IDs]
  // Row 5: [Date Ranges]
  // Row 6: [Date Ranges continued/merged]

  // Initialize 6 empty rows
  for(let i=0; i<6; i++) {
    worksheet.addRow([]);
  }

  // Helper to set cell value and style
  const setCell = (row, col, value, style = {}) => {
    const cell = worksheet.getCell(row, col);
    cell.value = value;
    cell.style = {
      alignment: { vertical: 'top', horizontal: 'center', wrapText: true },
      font: { size: 10 },
      border: {
        top: { style: 'thin' },
        left: { style: 'thin' },
        bottom: { style: 'thin' },
        right: { style: 'thin' }
      },
      ...style
    };
  };

  // 1. Fixed Columns (Full Name, Cost Center) - Merge 1-6
  setCell(1, 1, 'Full Name');
  worksheet.mergeCells(1, 1, 6, 1);
  
  setCell(1, 2, 'Cost Center');
  worksheet.mergeCells(1, 2, 6, 2);

  // 2. Project Columns
  colIdx = 3;
  reportData.value.projects.forEach(project => {
    if (project.is_default) {
      // Default: Merge 1-6, show name
      setCell(1, colIdx, project.name);
      worksheet.mergeCells(1, colIdx, 6, colIdx);
    } else {
      // Custom: 
      // Row 1: Full Name/Name
      setCell(1, colIdx, project.full_name || project.name);
      
      // Row 2-3: Chinese Name (Merge)
      setCell(2, colIdx, project.chinese_name || '');
      worksheet.mergeCells(2, colIdx, 3, colIdx);
      
      // Row 4: ID
      setCell(4, colIdx, `${project.custom_id || project.id}`);
      
      // Row 5-6: Date Range (Merge)
      setCell(5, colIdx, formatDateRange(project.start_date, project.plan_closed_date));
      worksheet.mergeCells(5, colIdx, 6, colIdx);

      // Apply styles to the merged/unmerged cells in this column to ensure borders
      for(let r=1; r<=6; r++) {
         // Re-apply border to ensure merged cells look right
         const cell = worksheet.getCell(r, colIdx);
         cell.border = {
            top: { style: 'thin' },
            left: { style: 'thin' },
            bottom: { style: 'thin' },
            right: { style: 'thin' }
         };
         cell.alignment = { vertical: 'top', horizontal: 'center', wrapText: true };
      }
    }
    colIdx++;
  });

  // 3. Trailing Columns (Total Hours, etc.) - Merge 1-6
  const trailingHeaders = ['Total Hours', 'Mark', 'Start Date', 'End Date'];
  trailingHeaders.forEach((text, i) => {
    const c = colIdx + i;
    setCell(1, c, text);
    worksheet.mergeCells(1, c, 6, c);
  });

  // --- Data Rows ---
  reportData.value.users.forEach(user => {
    const rowValues = [];
    rowValues[1] = user.full_name || '';
    rowValues[2] = user.cost_center || '';
    
    let c = 3;
    reportData.value.projects.forEach(project => {
      rowValues[c] = user.projects[project.name] || 0;
      c++;
    });
    
    rowValues[c] = user.total_hours;
    rowValues[c+1] = user.remark || '';
    rowValues[c+2] = user.start_date || '';
    rowValues[c+3] = user.end_date || '';

    const row = worksheet.addRow(rowValues);
    // Style data rows
    row.eachCell((cell) => {
      cell.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };
      cell.border = {
        top: { style: 'thin' },
        left: { style: 'thin' },
        bottom: { style: 'thin' },
        right: { style: 'thin' }
      };
    });
  });

  // Generate buffer
  const buffer = await workbook.xlsx.writeBuffer();
  
  // Download
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'report.xlsx';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}


onMounted(() => {
  fetchStats()
  fetchReport()
})
</script>

<style scoped>
.reports-container {
  padding: 20px;
  box-sizing: border-box;
}
.stats-row {
  margin-bottom: 20px;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filters {
  display: flex;
  gap: 10px;
}
.report-card {
  /* width: 100%; Removed to prevent overflow if padding is involved */
}
.report-card :deep(.el-card__body) {
  padding: 20px;
  overflow-x: auto;
}
.project-header {
  line-height: 1.3;
  font-size: 12px;
  padding: 0;
  margin: -8px -10px;
  padding-top: 8px;
  padding-bottom: 8px;
}
.project-header-line {
  margin: 0;
  padding: 3px 10px;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
.project-header-line.with-border {
  border-bottom: 1px solid #DCDFE6;
}
.project-header-line.time-range {
  font-size: 11px;
  color: #909399;
}
</style>
