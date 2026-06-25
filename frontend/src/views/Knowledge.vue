<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h3>知识库管理</h3>
      <el-button type="primary" @click="openKbDialog()">新建知识库</el-button>
    </div>
    <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
      预置「测试平台规范知识库」供测试设计 Agent 引用；可编辑条目、上传文档。测试点生成时可选择引用。
    </el-alert>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="范围" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_global ? 'success' : 'info'" size="small">
            {{ row.is_global ? '全局' : '项目' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="条目/文档" width="110">
        <template #default="{ row }">{{ row.entry_count ?? 0 }} / {{ row.document_count ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEntries(row)">管理条目</el-button>
          <el-upload :show-file-list="false" :http-request="(opt: UploadRequestOptions) => onUpload(row.id, opt)" style="display:inline">
            <el-button link>上传</el-button>
          </el-upload>
          <el-button link @click="openKbDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="removeKb(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="kbDialogVisible" :title="kbForm.id ? '编辑知识库' : '新建知识库'" width="480px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="kbForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="kbForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="全局库">
          <el-switch v-model="kbForm.is_global" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveKb">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="entryDrawerVisible" :title="`知识条目 - ${currentKb?.name || ''}`" size="720px">
      <div class="drawer-toolbar">
        <el-button type="primary" size="small" @click="openEntryDialog()">新增条目</el-button>
        <el-input v-model="searchQuery" placeholder="检索测试" style="width:200px" clearable @keyup.enter="runSearch" />
        <el-button size="small" @click="runSearch">检索</el-button>
      </div>
      <el-table :data="entries" size="small" border style="margin-top:12px">
        <el-table-column prop="title" label="标题" min-width="140" />
        <el-table-column prop="category" label="分类" width="90" />
        <el-table-column label="内容" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.content?.slice(0, 80) }}...</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button link size="small" @click="openEntryDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="removeEntry(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-if="searchResults.length" :data="searchResults" size="small" style="margin-top:16px">
        <el-table-column prop="title" label="检索命中" />
        <el-table-column prop="score" label="相关度" width="80" />
        <el-table-column prop="snippet" label="片段" show-overflow-tooltip />
      </el-table>
    </el-drawer>

    <el-dialog v-model="entryDialogVisible" :title="entryForm.id ? '编辑条目' : '新增条目'" width="640px">
      <el-form label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="entryForm.title" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="entryForm.category" style="width:100%">
            <el-option label="规范策略" value="policy" />
            <el-option label="设计方法" value="design" />
            <el-option label="术语表" value="glossary" />
            <el-option label="FAQ" value="faq" />
            <el-option label="上传文档" value="upload" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input v-model="entryForm.content" type="textarea" :rows="12" placeholder="支持 Markdown" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="entryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEntry">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type UploadRequestOptions } from 'element-plus'
import http from '@/api/http'

const items = ref<any[]>([])
const loading = ref(false)
const kbDialogVisible = ref(false)
const kbForm = ref<any>({ name: '', description: '', is_global: true })
const entryDrawerVisible = ref(false)
const currentKb = ref<any>(null)
const entries = ref<any[]>([])
const entryDialogVisible = ref(false)
const entryForm = ref<any>({ title: '', category: 'custom', content: '' })
const searchQuery = ref('')
const searchResults = ref<any[]>([])

const load = async () => {
  loading.value = true
  try {
    const { data } = await http.get('/knowledge/manage')
    items.value = data
  } finally {
    loading.value = false
  }
}

const openKbDialog = (row?: any) => {
  kbForm.value = row
    ? { id: row.id, name: row.name, description: row.description || '', is_global: row.is_global }
    : { name: '', description: '', is_global: true }
  kbDialogVisible.value = true
}

const saveKb = async () => {
  if (!kbForm.value.name?.trim()) return ElMessage.warning('请输入名称')
  if (kbForm.value.id) {
    await http.put(`/knowledge/${kbForm.value.id}`, {
      name: kbForm.value.name,
      description: kbForm.value.description,
      is_global: kbForm.value.is_global,
    })
    ElMessage.success('已更新')
  } else {
    await http.post('/knowledge', kbForm.value)
    ElMessage.success('已创建')
  }
  kbDialogVisible.value = false
  load()
}

const removeKb = async (row: any) => {
  await ElMessageBox.confirm(`确定删除知识库「${row.name}」？`, '确认')
  await http.delete(`/knowledge/${row.id}`)
  ElMessage.success('已删除')
  load()
}

const openEntries = async (row: any) => {
  currentKb.value = row
  searchResults.value = []
  searchQuery.value = ''
  const { data } = await http.get(`/knowledge/${row.id}/entries`)
  entries.value = data
  entryDrawerVisible.value = true
}

const openEntryDialog = (row?: any) => {
  entryForm.value = row
    ? { id: row.id, title: row.title, category: row.category, content: row.content }
    : { title: '', category: 'custom', content: '' }
  entryDialogVisible.value = true
}

const saveEntry = async () => {
  if (!entryForm.value.title?.trim() || !entryForm.value.content?.trim()) {
    return ElMessage.warning('请填写标题和内容')
  }
  const kbId = currentKb.value.id
  if (entryForm.value.id) {
    await http.put(`/knowledge/${kbId}/entries/${entryForm.value.id}`, entryForm.value)
  } else {
    await http.post(`/knowledge/${kbId}/entries`, entryForm.value)
  }
  ElMessage.success('已保存')
  entryDialogVisible.value = false
  const { data } = await http.get(`/knowledge/${kbId}/entries`)
  entries.value = data
  load()
}

const removeEntry = async (row: any) => {
  await ElMessageBox.confirm(`删除条目「${row.title}」？`, '确认')
  await http.delete(`/knowledge/${currentKb.value.id}/entries/${row.id}`)
  entries.value = entries.value.filter((e) => e.id !== row.id)
  load()
}

const onUpload = async (kbId: string, opt: UploadRequestOptions) => {
  const fd = new FormData()
  fd.append('file', opt.file)
  await http.post(`/knowledge/${kbId}/upload`, fd)
  ElMessage.success('上传成功，已解析为知识条目')
  if (currentKb.value?.id === kbId) {
    const { data } = await http.get(`/knowledge/${kbId}/entries`)
    entries.value = data
  }
  load()
}

const runSearch = async () => {
  if (!currentKb.value) return
  const { data } = await http.post('/knowledge/search', {
    kb_id: currentKb.value.id,
    query: searchQuery.value,
    top_k: 8,
  })
  searchResults.value = data.results || []
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-header h3 { margin: 0; }
.drawer-toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
</style>
