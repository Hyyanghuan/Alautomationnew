<template>
  <div>
    <div class="toolbar">
      <h3 style="margin:0">AI 模型管理</h3>
      <div>
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">添加模型</el-button>
      </div>
    </div>
    <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px">
      平台已预置 OpenAI / 通义千问 / DeepSeek 常用模型；各模型 <strong>API Key 可单独配置</strong>（优先使用此处配置，其次 .env）。
    </el-alert>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="label" label="模型" min-width="180">
        <template #default="{ row }">{{ row.provider }} / {{ row.model_name }}</template>
      </el-table-column>
      <el-table-column prop="api_endpoint" label="API 地址" show-overflow-tooltip />
      <el-table-column label="API Key" width="140">
        <template #default="{ row }">
          <el-tag v-if="row.has_api_key" type="success" size="small">{{ row.api_key_masked }}</el-tag>
          <el-tag v-else type="warning" size="small">未配置</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch v-model="row.is_enabled" @change="toggleEnabled(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openKey(row)">配置 Key</el-button>
          <el-button link @click="openEdit(row)">编辑</el-button>
          <el-button link @click="testConn(row.id)">测试</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="添加 AI 模型" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="快速选择">
          <el-select v-model="presetId" placeholder="常用模型" style="width:100%" @change="applyPreset">
            <el-option v-for="p in presets" :key="`${p.provider}-${p.model_name}`" :label="p.label" :value="`${p.provider}::${p.model_name}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="供应商"><el-input v-model="form.provider" /></el-form-item>
        <el-form-item label="模型名"><el-input v-model="form.model_name" /></el-form-item>
        <el-form-item label="API 地址"><el-input v-model="form.api_endpoint" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.api_key" type="password" show-password placeholder="可留空稍后单独配置" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate=false">取消</el-button>
        <el-button type="primary" @click="create">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" title="编辑模型" width="520px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="供应商"><el-input v-model="editForm.provider" /></el-form-item>
        <el-form-item label="模型名"><el-input v-model="editForm.model_name" /></el-form-item>
        <el-form-item label="API 地址"><el-input v-model="editForm.api_endpoint" /></el-form-item>
        <el-form-item label="限流/分"><el-input-number v-model="editForm.rate_limit" :min="1" :max="1000" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit=false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showKey" title="单独配置 API Key" width="480px">
      <p class="key-hint">模型：{{ keyForm.provider }} / {{ keyForm.model_name }}</p>
      <p v-if="keyForm.api_key_masked" class="key-hint">当前：{{ keyForm.api_key_masked }}</p>
      <el-input v-model="keyInput" type="password" show-password placeholder="输入新的 API Key" />
      <template #footer>
        <el-button @click="showKey=false">取消</el-button>
        <el-button type="primary" @click="saveKey">保存 Key</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api/http'

const items = ref<any[]>([])
const presets = ref<any[]>([])
const loading = ref(false)
const showCreate = ref(false)
const showEdit = ref(false)
const showKey = ref(false)
const presetId = ref('')
const keyInput = ref('')
const form = ref({ provider: 'openai', model_name: 'gpt-4o', api_endpoint: '', api_key: '' })
const editForm = ref<any>({})
const keyForm = ref<any>({})

const load = async () => {
  loading.value = true
  try {
    const { data } = await http.get('/ai-models')
    items.value = data
  } finally {
    loading.value = false
  }
}

const loadPresets = async () => {
  const { data } = await http.get('/ai-models/presets')
  presets.value = data
}

const applyPreset = () => {
  const p = presets.value.find((x) => `${x.provider}::${x.model_name}` === presetId.value)
  if (p) {
    form.value.provider = p.provider
    form.value.model_name = p.model_name
    form.value.api_endpoint = p.api_endpoint || ''
  }
}

const openCreate = () => {
  presetId.value = ''
  form.value = { provider: 'openai', model_name: 'gpt-4o', api_endpoint: '', api_key: '' }
  showCreate.value = true
  loadPresets()
}

const create = async () => {
  await http.post('/ai-models', form.value)
  ElMessage.success('已添加')
  showCreate.value = false
  load()
}

const openEdit = (row: any) => {
  editForm.value = { ...row }
  showEdit.value = true
}

const saveEdit = async () => {
  await http.put(`/ai-models/${editForm.value.id}`, {
    provider: editForm.value.provider,
    model_name: editForm.value.model_name,
    api_endpoint: editForm.value.api_endpoint,
    rate_limit: editForm.value.rate_limit,
  })
  ElMessage.success('已保存')
  showEdit.value = false
  load()
}

const openKey = (row: any) => {
  keyForm.value = row
  keyInput.value = ''
  showKey.value = true
}

const saveKey = async () => {
  if (!keyInput.value.trim()) return ElMessage.warning('请输入 API Key')
  await http.patch(`/ai-models/${keyForm.value.id}/api-key`, { api_key: keyInput.value })
  ElMessage.success('API Key 已更新')
  showKey.value = false
  load()
}

const toggleEnabled = async (row: any) => {
  await http.put(`/ai-models/${row.id}`, { is_enabled: row.is_enabled })
}

const testConn = async (id: string) => {
  const { data } = await http.post(`/ai-models/${id}/test-connection`)
  ElMessage.success(data.response?.slice(0, 80) || '连接成功')
}

onMounted(() => { load(); loadPresets() })
</script>

<style scoped>
.toolbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.key-hint { color:#909399; font-size:13px; margin:0 0 8px; }
</style>
