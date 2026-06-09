<template>
  <div>
    <div class="page-header">
      <h3>测试执行</h3>
      <el-button @click="$router.push('/executor-rules')">执行器与代码规则</el-button>
    </div>
    <ProjectSelector v-model="projectId" hint="选择项目后筛选计划与执行记录；不选则显示全部" />
    <el-tabs v-model="tab">
      <el-tab-pane label="执行计划" name="plans">
        <el-table :data="plans" v-loading="planLoading">
          <el-table-column prop="project_name" label="项目" width="140" />
          <el-table-column prop="name" label="计划名称" />
          <el-table-column prop="case_count" label="用例数" width="80" />
          <el-table-column prop="strategy" label="策略" width="90" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                :disabled="!row.case_count"
                :loading="runningId === row.id"
                @click="runPlan(row)"
              >执行</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="执行记录" name="history">
        <el-table :data="history" v-loading="historyLoading">
          <el-table-column prop="plan_name" label="计划" />
          <el-table-column prop="executor_name" label="执行人" width="100" />
          <el-table-column label="结果" width="140">
            <template #default="{ row }">
              <el-tag :type="row.status === 'passed' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
              {{ row.passed_cases }}/{{ row.total_cases }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220">
            <template #default="{ row }">
              <el-button link @click="goResults(row.id)">结果</el-button>
              <el-button link @click="goLogs(row.id)">日志</el-button>
              <el-button link type="primary" @click="goReport(row.id)">报告</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import ProjectSelector from '@/components/ProjectSelector.vue'
import { selectedProjectId } from '@/stores/projectContext'

const router = useRouter()
const projectId = ref(selectedProjectId.value)
const tab = ref('plans')
const plans = ref<any[]>([])
const history = ref<any[]>([])
const planLoading = ref(false)
const historyLoading = ref(false)
const runningId = ref('')

const loadPlans = async () => {
  planLoading.value = true
  const { data } = await http.get('/executions/plans', {
    params: { project_id: projectId.value || undefined, page_size: 100 },
  })
  plans.value = data.items
  planLoading.value = false
}

const loadHistory = async () => {
  historyLoading.value = true
  const { data } = await http.get('/executions/history', {
    params: { project_id: projectId.value || undefined, page_size: 100 },
  })
  history.value = data.items
  historyLoading.value = false
}

const runPlan = async (row: any) => {
  runningId.value = row.id
  try {
    const { data } = await http.post(`/executions/run/${row.id}`, {})
    ElMessage.success(data.summary || '执行完成')
    router.push(`/reports/${data.execution_id}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '执行失败')
  } finally {
    runningId.value = ''
    loadPlans()
    loadHistory()
  }
}

const goResults = (id: string) => router.push(`/executions/${id}/results`)
const goLogs = (id: string) => router.push(`/executions/${id}/logs`)
const goReport = (id: string) => router.push(`/reports/${id}`)

watch(projectId, () => {
  loadPlans()
  loadHistory()
}, { immediate: true })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.page-header h3 { margin: 0; }
</style>
