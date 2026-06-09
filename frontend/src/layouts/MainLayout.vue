<template>
  <el-container class="layout">
    <el-aside width="220px">
      <div class="logo">AI测试平台 V3</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon>仪表盘</el-menu-item>
        <el-menu-item index="/projects"><el-icon><Folder /></el-icon>项目管理</el-menu-item>
        <el-menu-item index="/versions"><el-icon><CollectionTag /></el-icon>版本管理</el-menu-item>
        <el-menu-item index="/test-points"><el-icon><Share /></el-icon>测试点</el-menu-item>
        <el-menu-item index="/features"><el-icon><Grid /></el-icon>功能管理</el-menu-item>
        <el-menu-item index="/test-cases"><el-icon><Document /></el-icon>用例管理</el-menu-item>
        <el-menu-item index="/test-plans"><el-icon><Calendar /></el-icon>测试计划</el-menu-item>
        <el-menu-item index="/executions"><el-icon><VideoPlay /></el-icon>测试执行</el-menu-item>
        <el-menu-item index="/reports"><el-icon><DataAnalysis /></el-icon>测试报告</el-menu-item>
        <el-divider />
        <el-menu-item index="/agents"><el-icon><Cpu /></el-icon>Agent管理</el-menu-item>
        <el-menu-item v-if="userStore.isAdmin()" index="/ai-models"><el-icon><Connection /></el-icon>AI模型</el-menu-item>
        <el-menu-item v-if="userStore.isAdmin()" index="/knowledge"><el-icon><Collection /></el-icon>知识库</el-menu-item>
        <el-menu-item index="/executor-rules"><el-icon><Setting /></el-icon>执行器规则</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <span>{{ userStore.username }} ({{ userStore.role }})</span>
        <el-button type="danger" link @click="logout">退出</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const activeMenu = computed(() => {
  const p = route.path
  if (p.startsWith('/reports')) return '/reports'
  if (p.startsWith('/executions/')) return '/executions'
  return p
})

const logout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100vh; }
.logo { padding: 20px; font-weight: bold; color: #409eff; border-bottom: 1px solid #eee; }
.el-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }
:deep(.el-divider) { margin: 8px 16px; }
</style>
