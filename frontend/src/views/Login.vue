<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>AI自动化测试平台 V3.0</h2>
      <el-form :model="form" @submit.prevent="login">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = ref({ username: 'admin', password: 'admin123' })

const login = async () => {
  loading.value = true
  try {
    const { data } = await http.post('/auth/login', form.value)
    userStore.setAuth(data.access_token, data.username, data.role)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { display:flex; justify-content:center; align-items:center; height:100vh; background:linear-gradient(135deg,#667eea,#764ba2); }
.login-card { width:400px; }
</style>
