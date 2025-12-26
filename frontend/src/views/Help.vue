<template>
  <div class="help-container">
    <el-card class="help-card">
      <template #header>
        <div class="card-header">
          <div class="header-content">
            <h2>TimeSheet-lite</h2>
            <span class="version">V1.0.0</span>
          </div>
        </div>
      </template>
      
      <div class="help-content">
        <section>
          <h3>Introduction</h3>
          <p>Welcome to SUTO Timesheet Lite, a comprehensive tool for managing employee time, projects, and reports.</p>
        </section>

        <el-divider />

        <section>
          <h3>User Roles</h3>
          <el-descriptions border :column="1">
            <el-descriptions-item label="Admin">
              Full system access. Can manage Projects, Employees, view all Reports, and configure System Settings (Email, Activity Logs).
            </el-descriptions-item>
            <el-descriptions-item label="Team Leader">
              Can manage timesheets for their assigned team members via the "Team Timesheets" page.
            </el-descriptions-item>
            <el-descriptions-item label="Employee">
              Standard access. Can log daily work via "Log Work", view assigned projects, and see personal dashboard statistics.
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <el-divider />

        <section>
          <h3>Key Features</h3>
          <el-collapse v-model="activeNames">
            <el-collapse-item title="Dashboard" name="1">
              <div>
                Provides a quick overview of system statistics. For Admins, it shows total users and projects. For Employees, it shows personal project time distribution.
              </div>
            </el-collapse-item>
            <el-collapse-item title="Log Work" name="2">
              <div>
                The primary interface for employees to record their daily work hours against assigned projects.
              </div>
            </el-collapse-item>
            <el-collapse-item title="Projects" name="3">
              <div>
                (Admin only) Create, edit, and manage projects. Set project status (RUN, CLOSE, NOT START) and details.
              </div>
            </el-collapse-item>
            <el-collapse-item title="Reports" name="4">
              <div>
                Generate weekly or monthly reports. Admins can view reports for all users. Supports Excel export with custom headers.
              </div>
            </el-collapse-item>
            <el-collapse-item title="Team Timesheets" name="5">
              <div>
                (Team Leader only) View and verify timesheets for team members.
              </div>
            </el-collapse-item>
          </el-collapse>
        </section>

        <el-divider />

        <section>
          <h3>System Diagrams</h3>
          <el-collapse>
            <el-collapse-item title="Employee Workflow" name="7">
              <div class="diagram-container">
                <img src="/static/empoyee_workflow_s.jpeg" alt="Employee Workflow" />
              </div>
            </el-collapse-item>
            <el-collapse-item title="Team Leader Workflow" name="8">
              <div class="diagram-container">
                <img src="/static/teamleader_workflow_s.jpeg" alt="Team Leader Workflow" />
              </div>
            </el-collapse-item>
          </el-collapse>
        </section>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const activeNames = ref(['1', '2', '3', '4', '5'])
</script>

<style scoped>
.help-container {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}
.help-card {
  margin-bottom: 20px;
}
.header-content {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.header-content h2 {
  margin: 0;
}
.version {
  font-size: 0.8em;
  color: #909399;
}
.help-content h3 {
  margin-top: 0;
  color: #409EFF;
}
section {
  margin-bottom: 20px;
}
.diagram-container {
  text-align: center;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 4px;
}
.diagram-container img {
  max-width: 100%;
  height: auto;
}
</style>
