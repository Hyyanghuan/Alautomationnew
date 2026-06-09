<template>
  <div>
    <div class="page-header">
      <h3>测试报告</h3>
      <div class="header-actions">
        <el-button @click="openTgConfig">Telegram 配置</el-button>
        <el-button @click="load" :loading="loading">刷新</el-button>
      </div>
    </div>

    <template v-if="executionId">
      <el-page-header @back="backToList" content="报告详情" style="margin-bottom:16px" />
      <el-card v-loading="detailLoading">
        <template v-if="report">
          <el-row :gutter="16" class="stats">
            <el-col :span="6"><el-statistic title="通过率" :value="report.pass_rate" suffix="%" /></el-col>
            <el-col :span="6"><el-statistic title="通过" :value="report.passed_cases" /></el-col>
            <el-col :span="6"><el-statistic title="失败" :value="report.failed_cases" /></el-col>
            <el-col :span="6"><el-statistic title="耗时" :value="report.duration_ms" suffix="ms" /></el-col>
          </el-row>
          <el-descriptions :column="2" border style="margin-top:16px">
            <el-descriptions-item label="测试计划">{{ report.plan_name }}</el-descriptions-item>
            <el-descriptions-item label="执行人">{{ report.executor_name }}</el-descriptions-item>
            <el-descriptions-item label="执行时间">{{ formatTime(report.started_at) }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="report.status === 'passed' ? 'success' : 'danger'">{{ report.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="摘要" :span="2">{{ report.summary }}</el-descriptions-item>
          </el-descriptions>
          <div style="margin-top:16px">
            <el-button
              type="primary"
              :loading="sendingTg"
              :disabled="!tgConfig.enabled"
              @click="sendToTelegram(report.id)"
            >
              发送到 Telegram
            </el-button>
            <el-button @click="$router.push(`/executions/${executionId}/results`)">用例结果</el-button>
            <el-button @click="$router.push(`/executions/${executionId}/logs`)">执行日志</el-button>
          </div>
          <el-table :data="report.results" size="small" style="margin-top:16px">
            <el-table-column prop="case_name" label="用例" />
            <el-table-column prop="status" label="状态" width="90" />
            <el-table-column prop="executor_type" label="执行器" width="90" />
          </el-table>
        </template>
      </el-card>
    </template>

    <template v-else>
      <ProjectSelector v-model="projectId" hint="可按项目筛选报告；不选则显示全部" />
      <el-table :data="reports" v-loading="loading">
        <el-table-column prop="plan_name" label="测试计划" />
        <el-table-column prop="executor_name" label="执行人" width="100" />
        <el-table-column label="通过率" width="100">
          <template #default="{ row }">{{ row.pass_rate }}%</template>
        </el-table-column>
        <el-table-column label="结果" width="120">
          <template #default="{ row }">{{ row.passed_cases }}/{{ row.total_cases }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewReport(row.id)">查看</el-button>
            <el-button
              link
              type="success"
              :disabled="!tgConfig.enabled"
              @click="sendToTelegram(row.id)"
            >
              发 TG
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-dialog v-model="tgDialogVisible" title="Telegram 报告推送配置" width="520px" destroy-on-close>
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
        默认读取 <code>.env</code> 中的配置；在此保存后将写入运行时配置（优先于 .env）。Bot 需已加入目标群组。
      </el-alert>
      <el-form :model="tgForm" label-width="120px">
        <el-form-item label="启用推送">
          <el-switch v-model="tgForm.enabled" />
        </el-form-item>
        <el-form-item label="Bot Token">
          <el-input
            v-model="tgForm.bot_token"
            type="password"
            show-password
            :placeholder="tgConfig.bot_token_set ? `已配置 ${tgConfig.bot_token_masked}` : '输入 Bot Token'"
          />
        </el-form-item>
        <el-form-item label="群组 Chat ID">
          <el-input v-model="tgForm.chat_id" placeholder="如 -1003972980192" />
        </el-form-item>
        <el-form-item label="执行后自动推送">
          <el-switch v-model="tgForm.auto_send_after_execution" />
          <span class="form-hint">测试计划执行完成后自动发送报告</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :loading="tgTesting" @click="testTgConfig">发送测试消息</el-button>
        <el-button @click="tgDialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="tgSaving" @click="saveTgConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import ProjectSelector from '@/components/ProjectSelector.vue'
import { selectedProjectId } from '@/stores/projectContext'

const route = useRoute()
const router = useRouter()
const projectId = ref(selectedProjectId.value)
const executionId = ref(route.params.executionId as string | undefined)
const reports = ref<any[]>([])
const report = ref<any>(null)
const loading = ref(false)
const detailLoading = ref(false)
const sendingTg = ref(false)
const tgDialogVisible = ref(false)
const tgSaving = ref(false)
const tgTesting = ref(false)
const tgConfig = ref({
  enabled: false,
  chat_id: '',
  bot_token_set: false,
  bot_token_masked: '',
  auto_send_after_execution: false,
})
const tgForm = ref({
  enabled: false,
  chat_id: '',
  bot_token: '',
  auto_send_after_execution: false,
})

const formatTime = (t: string) => (t ? new Date(t).toLocaleString('zh-CN') : '-')

const loadTgConfig = async () => {
  const { data } = await http.get('/reports/telegram-config')
  tgConfig.value = data
}

const openTgConfig = async () => {
  await loadTgConfig()
  tgForm.value = {
    enabled: tgConfig.value.enabled,
    chat_id: tgConfig.value.chat_id,
    bot_token: '',
    auto_send_after_execution: tgConfig.value.auto_send_after_execution,
  }
  tgDialogVisible.value = true
}

const saveTgConfig = async () => {
  tgSaving.value = true
  try {
    const { data } = await http.put('/reports/telegram-config', {
      enabled: tgForm.value.enabled,
      chat_id: tgForm.value.chat_id,
      bot_token: tgForm.value.bot_token || undefined,
      auto_send_after_execution: tgForm.value.auto_send_after_execution,
    })
    tgConfig.value = data
    ElMessage.success('Telegram 配置已保存')
    tgDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    tgSaving.value = false
  }
}

const testTgConfig = async () => {
  tgTesting.value = true
  try {
    if (tgDialogVisible.value) {
      await http.put('/reports/telegram-config', {
        enabled: true,
        chat_id: tgForm.value.chat_id,
        bot_token: tgForm.value.bot_token || undefined,
        auto_send_after_execution: tgForm.value.auto_send_after_execution,
      })
    }
    const { data } = await http.post('/reports/telegram-config/test')
    ElMessage.success(data.message || '测试消息已发送')
    await loadTgConfig()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '测试发送失败')
  } finally {
    tgTesting.value = false
  }
}

const sendToTelegram = async (id: string) => {
  sendingTg.value = true
  try {
    const { data } = await http.post(`/reports/${id}/send-telegram`)
    ElMessage.success(data.message || '已发送到 Telegram')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sendingTg.value = false
  }
}

const load = async () => {
  loading.value = true
  const { data } = await http.get('/reports', {
    params: { project_id: projectId.value || undefined, page_size: 50 },
  })
  reports.value = data.items
  loading.value = false
}

const loadDetail = async () => {
  if (!executionId.value) return
  detailLoading.value = true
  const { data } = await http.get(`/reports/${executionId.value}`)
  report.value = data
  detailLoading.value = false
}

const viewReport = (id: string) => router.push(`/reports/${id}`)
const backToList = () => router.push('/reports')

watch(projectId, () => { if (!executionId.value) load() })
watch(() => route.params.executionId, (id) => {
  executionId.value = id as string | undefined
  id ? loadDetail() : load()
}, { immediate: true })

onMounted(loadTgConfig)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-header h3 { margin: 0; }
.header-actions { display: flex; gap: 8px; }
.stats { margin-bottom: 8px; }
.form-hint { margin-left: 8px; color: #909399; font-size: 12px; }
</style>
