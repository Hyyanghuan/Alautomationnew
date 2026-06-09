<template>
  <div>
    <div class="toolbar">
      <h3 style="margin:0">Agent 管理</h3>
      <el-button type="primary" @click="openEdit()">创建智能体</el-button>
    </div>
    <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px">
      已预置测试设计/代码分析/自愈修复/缺陷预测智能体，含完整文件结构（prompts、memory、tools、workflows、skills、knowledge、configs），可在详情中编辑更新。
    </el-alert>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="agent_type" label="类型" width="120" />
      <el-table-column label="绑定模型" width="200">
        <template #default="{ row }">
          <span v-if="row.model_name">{{ row.model_provider }} / {{ row.model_name }}</span>
          <el-tag v-else type="info" size="small">未绑定</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="说明" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '-' }}</template>
      </el-table-column>
      <el-table-column label="关联功能" width="120">
        <template #default="{ row }">
          <el-button
            v-if="linkedRoute(row)"
            link
            type="primary"
            @click="goLinked(row)"
          >
            {{ linkedLabel(row) }}
          </el-button>
          <span v-else class="muted">未配置</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openProfile(row)">配置详情</el-button>
          <el-button link @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 基础编辑 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑智能体' : '创建智能体'" width="560px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.agent_type" style="width:100%">
            <el-option label="测试设计" value="design" />
            <el-option label="代码分析" value="code_analysis" />
            <el-option label="自愈修复" value="healing" />
            <el-option label="缺陷预测" value="defect_prediction" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定模型">
          <el-select v-model="form.model_id" clearable placeholder="选择 AI 模型" style="width:100%">
            <el-option v-for="m in modelOptions" :key="m.id" :label="`${m.provider} / ${m.model_name}`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联功能">
          <el-select v-model="form.linked_route" clearable placeholder="选择跳转的功能页面" style="width:100%">
            <el-option v-for="r in ROUTE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="formEnabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 完整文件结构编辑 -->
    <el-drawer v-model="showProfile" :title="`Agent 配置 - ${profileName}`" size="72%" destroy-on-close>
      <el-row :gutter="16" style="height:100%">
        <el-col :span="7" class="file-tree-col">
          <el-tree
            :data="fileTree"
            node-key="id"
            highlight-current
            default-expand-all
            @node-click="onFileSelect"
          />
        </el-col>
        <el-col :span="17">
          <div v-if="currentFile" class="editor-wrap">
            <div class="editor-title">{{ currentFile.label }}</div>
            <el-input v-model="currentContent" type="textarea" :rows="22" placeholder="Markdown / JSON / YAML 内容" />
          </div>
          <el-empty v-else description="请选择左侧文件" />
          <div class="profile-footer">
            <el-form-item label="主任务提示词" label-width="100px" style="margin-top:12px">
              <el-input v-model="profilePrompt" type="textarea" :rows="3" placeholder="test_points 等任务默认模板" />
            </el-form-item>
            <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存全部配置</el-button>
          </div>
        </el-col>
      </el-row>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'

const router = useRouter()

const ROUTE_OPTIONS = [
  { label: '测试点管理', value: '/test-points' },
  { label: '功能管理', value: '/features' },
  { label: '用例管理', value: '/test-cases' },
  { label: '测试计划', value: '/test-plans' },
  { label: '执行中心', value: '/executions' },
  { label: '测试报告', value: '/reports' },
  { label: '知识库', value: '/knowledge' },
  { label: 'Agent 管理', value: '/agents' },
]

const DEFAULT_ROUTE_BY_TYPE: Record<string, string> = {
  design: '/test-points',
  code_analysis: '/test-cases',
  healing: '/executions',
  defect_prediction: '/reports',
  intent: '/test-cases',
}

const SECTIONS = [
  { key: 'prompts', label: 'prompts/ 提示词', files: ['system-prompt.md', 'task-router.md', 'role-config.md', 'output-format.md', 'task-prompts.json'] },
  { key: 'memory', label: 'memory/ 记忆', files: ['user-profile.md', 'session-context.md', 'long-term-memory.md', 'knowledge-notes.md'] },
  { key: 'tools', label: 'tools/ 工具', files: ['browser-tool.md', 'code-executor.md', 'api-connectors.md', 'search-tool.md'] },
  { key: 'workflows', label: 'workflows/ 工作流', files: ['plan-execute.md', 'rag-pipeline.md', 'multi-agent.md', 'evaluation-loop.md'] },
  { key: 'skills', label: 'skills/ 技能', files: ['writing.md', 'coding.md', 'analysis.md', 'design.md'] },
  { key: 'knowledge', label: 'knowledge/ 知识库', files: ['domain-faq.md', 'product-docs.md', 'policy-rules.md', 'glossary.md'] },
  { key: 'configs', label: 'configs/ 配置', files: ['model-settings.yaml', 'tool-permissions.yaml', 'env.example', 'agent-profile.json'] },
]

const items = ref<any[]>([])
const modelOptions = ref<any[]>([])
const loading = ref(false)
const showDialog = ref(false)
const showProfile = ref(false)
const isEdit = ref(false)
const editId = ref('')
const profileId = ref('')
const profileName = ref('')
const formEnabled = ref(true)
const agentFiles = ref<Record<string, any>>({})
const fileTree = ref<any[]>([])
const currentFile = ref<any>(null)
const currentContent = ref('')
const profilePrompt = ref('')
const savingProfile = ref(false)

const form = ref({
  name: '',
  agent_type: 'design',
  model_id: '' as string | undefined,
  project_id: undefined as string | undefined,
  linked_route: '' as string | undefined,
})

const linkedRoute = (row: any) => row.config?.linked_route || DEFAULT_ROUTE_BY_TYPE[row.agent_type] || ''
const linkedLabel = (row: any) => {
  const route = linkedRoute(row)
  return ROUTE_OPTIONS.find((r) => r.value === route)?.label || '前往'
}
const goLinked = (row: any) => {
  const route = linkedRoute(row)
  if (route) router.push(route)
}

const buildTree = (files: Record<string, any>) => {
  const tree = SECTIONS.map((s) => ({
    id: s.key,
    label: s.label,
    children: s.files.map((f) => ({ id: `${s.key}/${f}`, label: f, section: s.key, file: f })),
  }))
  tree.push({ id: 'README.md', label: 'README.md', section: '_root', file: 'README.md' })
  tree.push({ id: 'agent-index.md', label: 'agent-index.md', section: '_root', file: 'agent-index.md' })
  fileTree.value = tree
  if (!currentFile.value && tree[0]?.children?.[0]) {
    onFileSelect(tree[0].children[0])
  }
}

const onFileSelect = (node: any) => {
  if (!node.section) return
  currentFile.value = node
  if (node.section === '_root') {
    currentContent.value = agentFiles.value[node.file] || ''
  } else {
    const sec = agentFiles.value[node.section] || {}
    const val = sec[node.file]
    currentContent.value = typeof val === 'object' ? JSON.stringify(val, null, 2) : (val || '')
  }
}

const persistCurrentFile = () => {
  if (!currentFile.value) return
  const { section, file } = currentFile.value
  if (section === '_root') {
    agentFiles.value[file] = currentContent.value
  } else {
    if (!agentFiles.value[section]) agentFiles.value[section] = {}
    if (file.endsWith('.json')) {
      try {
        agentFiles.value[section][file] = JSON.parse(currentContent.value || '{}')
      } catch {
        agentFiles.value[section][file] = currentContent.value
      }
    } else {
      agentFiles.value[section][file] = currentContent.value
    }
  }
}

const load = async () => {
  loading.value = true
  const { data } = await http.get('/agents', { params: { page: 1, page_size: 100 } })
  items.value = data.items
  loading.value = false
}

const loadModels = async () => {
  try {
    const { data } = await http.get('/agents/model-options')
    modelOptions.value = data
  } catch {
    modelOptions.value = []
  }
}

const openEdit = (row?: any) => {
  loadModels()
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = {
      name: row.name,
      agent_type: row.agent_type,
      model_id: row.model_id || undefined,
      project_id: row.project_id,
      linked_route: row.config?.linked_route || DEFAULT_ROUTE_BY_TYPE[row.agent_type] || undefined,
    }
    formEnabled.value = row.status === 'enabled'
  } else {
    isEdit.value = false
    editId.value = ''
    form.value = {
      name: '',
      agent_type: 'design',
      model_id: undefined,
      project_id: undefined,
      linked_route: DEFAULT_ROUTE_BY_TYPE.design,
    }
    formEnabled.value = true
  }
  showDialog.value = true
}

const save = async () => {
  const existing = isEdit.value ? items.value.find((a) => a.id === editId.value) : null
  const config = { ...(existing?.config || {}) }
  if (form.value.linked_route) {
    config.linked_route = form.value.linked_route
  } else {
    delete config.linked_route
  }
  const body = {
    name: form.value.name,
    agent_type: form.value.agent_type,
    model_id: form.value.model_id || null,
    project_id: form.value.project_id,
    config,
    status: formEnabled.value ? 'enabled' : 'disabled',
  }
  if (isEdit.value) {
    await http.put(`/agents/${editId.value}`, body)
    ElMessage.success('已更新')
  } else {
    await http.post('/agents', body)
    ElMessage.success('已创建')
  }
  showDialog.value = false
  load()
}

const openProfile = async (row: any) => {
  profileId.value = row.id
  profileName.value = row.name
  const { data } = await http.get(`/agents/${row.id}/profile`)
  agentFiles.value = JSON.parse(JSON.stringify(data.agent_files || {}))
  profilePrompt.value = data.prompt_template || ''
  currentFile.value = null
  buildTree(agentFiles.value)
  showProfile.value = true
}

const saveProfile = async () => {
  persistCurrentFile()
  savingProfile.value = true
  try {
    await http.put(`/agents/${profileId.value}/profile`, {
      agent_files: agentFiles.value,
      prompt_template: profilePrompt.value || null,
    })
    ElMessage.success('Agent 配置已保存')
    showProfile.value = false
    load()
  } finally {
    savingProfile.value = false
  }
}

const remove = async (id: string) => {
  await ElMessageBox.confirm('确定删除该智能体？', '提示')
  await http.delete(`/agents/${id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.file-tree-col { border-right:1px solid #eee; max-height:calc(100vh - 120px); overflow:auto; }
.editor-title { font-weight:600; margin-bottom:8px; color:#303133; }
.editor-wrap { margin-bottom:12px; }
.profile-footer { border-top:1px solid #eee; padding-top:12px; }
.muted { color:#909399; font-size:13px; }
</style>
