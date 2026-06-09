<template>
  <div v-loading="loading">
    <el-page-header @back="goBack" content="测试结果" />
    <el-card v-if="detail" style="margin-top:16px">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="计划">{{ detail.plan_name }}</el-descriptions-item>
        <el-descriptions-item label="执行人">{{ detail.executor_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detail.status === 'passed' ? 'success' : 'danger'">{{ detail.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="通过">{{ detail.passed_cases }}/{{ detail.total_cases }}</el-descriptions-item>
        <el-descriptions-item label="失败">{{ detail.failed_cases }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ detail.duration_ms }} ms</el-descriptions-item>
        <el-descriptions-item label="开始">{{ formatTime(detail.started_at) }}</el-descriptions-item>
        <el-descriptions-item label="结束">{{ formatTime(detail.finished_at) }}</el-descriptions-item>
        <el-descriptions-item label="触发">{{ detail.trigger_type }}</el-descriptions-item>
        <el-descriptions-item label="摘要" :span="3">{{ detail.summary }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top:12px">
        <el-button @click="$router.push(`/executions/${executionId}/logs`)">查看执行日志</el-button>
        <el-button type="primary" @click="$router.push(`/reports/${executionId}`)">查看测试报告</el-button>
      </div>
    </el-card>

    <el-table :data="results" style="margin-top:16px">
      <el-table-column prop="case_name" label="用例" />
      <el-table-column prop="executor_type" label="执行器" width="90" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'passed' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="duration_ms" label="耗时(ms)" width="90" />
      <el-table-column prop="healed" label="自愈" width="70">
        <template #default="{ row }">{{ row.healed ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link @click="showLog(row)">详细日志</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="logVisible" title="用例执行日志" width="640px">
      <p><strong>{{ logDetail.case_name }}</strong> — {{ logDetail.status }}</p>
      <pre class="log-pre">{{ logDetail.log || logDetail.error_message || '无' }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/api/http'

const route = useRoute()
const router = useRouter()
const executionId = route.params.executionId as string

const goBack = () => router.push('/executions')
const loading = ref(false)
const detail = ref<any>(null)
const results = ref<any[]>([])
const logVisible = ref(false)
const logDetail = ref<any>({})

const formatTime = (t: string) => (t ? new Date(t).toLocaleString('zh-CN') : '-')

const load = async () => {
  loading.value = true
  try {
    const [d, r] = await Promise.all([
      http.get(`/executions/detail/${executionId}`),
      http.get(`/executions/${executionId}/results`, { params: { page_size: 200 } }),
    ])
    detail.value = d.data
    results.value = r.data.items
  } finally {
    loading.value = false
  }
}

const showLog = async (row: any) => {
  const { data } = await http.get(`/executions/result/${row.id}/log`)
  logDetail.value = data
  logVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.log-pre {
  background: #f5f5f5;
  padding: 12px;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 13px;
}
</style>
