<template>
  <div v-loading="loading">
    <el-page-header @back="goBack" content="测试执行日志" />
    <el-card v-if="detail" style="margin-top:16px">
      <p><strong>计划：</strong>{{ detail.plan_name }} &nbsp;
        <el-button link type="primary" @click="$router.push(`/executions/${executionId}/results`)">测试结果</el-button>
      </p>
    </el-card>

    <div class="toolbar">
      <el-select v-model="levelFilter" placeholder="日志级别" clearable style="width:120px" @change="load">
        <el-option label="INFO" value="info" />
        <el-option label="WARN" value="warn" />
        <el-option label="ERROR" value="error" />
      </el-select>
      <el-button @click="load">刷新</el-button>
    </div>

    <div class="log-list">
      <div v-for="item in logs" :key="item.id" :class="['log-line', `log-${item.level}`]">
        <span class="log-time">{{ formatTime(item.created_at) }}</span>
        <el-tag size="small" :type="levelTag(item.level)">{{ item.level }}</el-tag>
        <span class="log-msg">{{ item.message }}</span>
      </div>
      <el-empty v-if="!logs.length && !loading" description="暂无日志" />
    </div>
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
const logs = ref<any[]>([])
const levelFilter = ref('')

const formatTime = (t: string) => new Date(t).toLocaleString('zh-CN')
const levelTag = (l: string) => (l === 'error' ? 'danger' : l === 'warn' ? 'warning' : 'info')

const load = async () => {
  loading.value = true
  try {
    const [d, l] = await Promise.all([
      http.get(`/executions/detail/${executionId}`),
      http.get(`/executions/${executionId}/logs`, {
        params: { page_size: 500, level: levelFilter.value || undefined },
      }),
    ])
    detail.value = d.data
    logs.value = l.data.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin: 12px 0; display: flex; gap: 8px; }
.log-list { max-height: calc(100vh - 280px); overflow-y: auto; font-family: Consolas, monospace; font-size: 13px; }
.log-line { padding: 6px 8px; border-bottom: 1px solid #eee; display: flex; gap: 8px; align-items: flex-start; }
.log-time { color: #888; white-space: nowrap; min-width: 160px; }
.log-msg { flex: 1; white-space: pre-wrap; word-break: break-all; }
.log-error { background: #fef0f0; }
.log-warn { background: #fdf6ec; }
</style>
