<template>
  <div>
    <h2>平台概览</h2>
    <el-row :gutter="20">
      <el-col :span="6"><el-statistic title="项目数" :value="stats.projects" /></el-col>
      <el-col :span="6"><el-statistic title="用例数" :value="stats.cases" /></el-col>
      <el-col :span="6"><el-statistic title="近20次通过率" :value="stats.passRate" suffix="%" /></el-col>
      <el-col :span="6"><el-statistic title="Agent数" :value="stats.agents" /></el-col>
    </el-row>
    <el-card style="margin-top:20px">
      <h4 style="margin:0 0 12px">推荐测试流程</h4>
      <el-steps :active="0" align-center style="margin-bottom:16px">
        <el-step title="项目管理" description="创建/启动项目" @click="$router.push('/projects')" />
        <el-step title="版本" description="规划版本" @click="$router.push('/versions')" />
        <el-step title="测试点" description="需求→测试点" @click="$router.push('/test-points')" />
        <el-step title="功能" description="自动同步" @click="$router.push('/features')" />
        <el-step title="用例" description="生成/核查" @click="$router.push('/test-cases')" />
        <el-step title="计划" description="关联用例" @click="$router.push('/test-plans')" />
        <el-step title="执行" description="运行计划" @click="$router.push('/executions')" />
        <el-step title="报告" description="查看结果" @click="$router.push('/reports')" />
      </el-steps>
      <el-button type="primary" @click="$router.push('/projects')">开始：项目管理</el-button>
      <p style="margin-top:12px;color:#909399;font-size:13px">
        各页面通过顶部「关联项目」选择器绑定项目；AI 模型 Key 在「AI模型」中单独配置。
      </p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import http from '@/api/http'

const stats = ref({ projects: 0, cases: 0, passRate: 0, agents: 0 })

onMounted(async () => {
  try {
    const { data } = await http.get('/dashboard/stats')
    stats.value = {
      projects: data.projects || 0,
      cases: data.cases || 0,
      passRate: data.pass_rate || 0,
      agents: data.agents || 0,
    }
  } catch { /* ignore */ }
})
</script>

<style scoped>
:deep(.el-step__title) { cursor: pointer; }
:deep(.el-step__description) { cursor: pointer; }
</style>
