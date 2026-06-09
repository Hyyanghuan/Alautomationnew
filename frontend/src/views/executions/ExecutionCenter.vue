<template>
  <div class="execution-center">
    <el-tabs v-model="tab" @tab-change="onTabChange">
      <el-tab-pane label="执行器与代码规则" name="rules">
        <el-table :data="executors" highlight-current-row @row-click="showRule">
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="tech" label="技术底座" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click.stop="showRule(row)">查看代码规则</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="测试计划执行" name="plans">
        <div class="toolbar">
          <el-input v-model="planKeyword" placeholder="搜索计划" clearable style="width:220px" @keyup.enter="loadPlans" />
          <el-button type="primary" @click="loadPlans">刷新</el-button>
        </div>
        <el-table :data="plans" v-loading="planLoading">
          <el-table-column prop="project_name" label="项目" width="140" />
          <el-table-column prop="name" label="计划名称" />
          <el-table-column label="执行类型" width="130">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.executor_name || row.executor_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="case_count" label="用例数" width="80" />
          <el-table-column prop="strategy" label="策略" width="90" />
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="上次执行" width="180">
            <template #default="{ row }">
              <span v-if="row.last_execution_at">{{ row.last_execution_status }} @ {{ formatTime(row.last_execution_at) }}</span>
              <span v-else class="muted">未执行</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                :disabled="!row.case_count"
                :loading="runningId === row.id"
                @click="runPlan(row)"
              >立即执行</el-button>
              <el-button v-if="row.last_execution_id" link @click="goResults(row.last_execution_id)">上次结果</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="planPage"
          :total="planTotal"
          layout="total, prev, pager, next"
          @current-change="loadPlans"
          style="margin-top:12px"
        />
      </el-tab-pane>

      <el-tab-pane label="执行历史" name="history">
        <el-table :data="history" v-loading="historyLoading">
          <el-table-column prop="plan_name" label="测试计划" />
          <el-table-column prop="executor_name" label="执行人" width="100" />
          <el-table-column prop="trigger_type" label="触发" width="80" />
          <el-table-column label="结果" width="160">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
              {{ row.passed_cases }}/{{ row.total_cases }}
            </template>
          </el-table-column>
          <el-table-column prop="duration_ms" label="耗时(ms)" width="100" />
          <el-table-column label="执行时间" width="170">
            <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="goResults(row.id)">测试结果</el-button>
              <el-button link @click="goLogs(row.id)">执行日志</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="historyPage"
          :total="historyTotal"
          layout="total, prev, pager, next"
          @current-change="loadHistory"
          style="margin-top:12px"
        />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="ruleVisible" :title="`代码规则 - ${currentRule?.name}`" width="82%" top="4vh">
      <p><strong>说明：</strong>{{ currentRule?.description }}</p>
      <p><strong>技术底座：</strong>{{ currentRule?.tech }}</p>
      <el-divider />
      <p><strong>执行规则：</strong></p>
      <ul>
        <li v-for="(r, i) in currentRule?.rules || []" :key="i">{{ r }}</li>
      </ul>
      <template v-if="currentRule?.case_format">
        <el-divider />
        <p><strong>用例格式示例：</strong></p>
        <pre class="code-block">{{ JSON.stringify(currentRule.case_format, null, 2) }}</pre>
      </template>
      <el-divider />
      <p><strong>完整执行器源码：</strong></p>
      <pre class="code-block code-full">{{ currentRule?.code_sample }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'

const router = useRouter()
const route = useRoute()
const tab = ref((route.query.tab as string) || 'plans')
const executors = ref<any[]>([])
const ruleVisible = ref(false)
const currentRule = ref<any>(null)

const plans = ref<any[]>([])
const planLoading = ref(false)
const planKeyword = ref('')
const planPage = ref(1)
const planTotal = ref(0)
const runningId = ref('')

const history = ref<any[]>([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyTotal = ref(0)

const formatTime = (t: string) => (t ? new Date(t).toLocaleString('zh-CN') : '-')
const statusTag = (s: string) => (s === 'passed' ? 'success' : s === 'failed' ? 'danger' : 'info')

const loadExecutors = async () => {
  const { data } = await http.get('/executions/executors')
  executors.value = data
}

const showRule = async (row: any) => {
  const { data } = await http.get(`/executions/executors/${row.type}/rules`)
  currentRule.value = data
  ruleVisible.value = true
}

const loadPlans = async () => {
  planLoading.value = true
  try {
    const { data } = await http.get('/executions/plans', {
      params: { page: planPage.value, page_size: 20, keyword: planKeyword.value || undefined },
    })
    plans.value = data.items
    planTotal.value = data.total
  } finally {
    planLoading.value = false
  }
}

const loadHistory = async () => {
  historyLoading.value = true
  try {
    const { data } = await http.get('/executions/history', {
      params: { page: historyPage.value, page_size: 20 },
    })
    history.value = data.items
    historyTotal.value = data.total
  } finally {
    historyLoading.value = false
  }
}

const runPlan = async (row: any) => {
  runningId.value = row.id
  try {
    const { data } = await http.post(`/executions/run/${row.id}`, {})
    ElMessage.success(data.summary || '执行完成')
    goResults(data.execution_id)
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

const onTabChange = (name: string) => {
  if (name === 'plans') loadPlans()
  if (name === 'history') loadHistory()
}

onMounted(() => {
  if (route.query.tab && typeof route.query.tab === 'string') {
    tab.value = route.query.tab
  }
  loadExecutors()
  if (tab.value === 'plans') loadPlans()
  if (tab.value === 'history') loadHistory()
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
.muted { color: #999; }
.code-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.5;
  max-height: 400px;
}
.code-full { max-height: 55vh; }
</style>
