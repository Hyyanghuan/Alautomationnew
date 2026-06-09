<template>
  <div>
    <h3 style="margin:0 0 8px">用例管理</h3>
    <ProjectSelector v-model="projectId" hint="选择项目后查看/管理用例，可关联到测试计划" />
    <el-empty v-if="!projectId" description="请先关联项目" />
    <div v-else class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用例" style="width:200px" clearable @keyup.enter="onSearch" @clear="onSearch" />
      <el-select
        v-model="typeFilter"
        placeholder="测试类型"
        clearable
        style="width:160px"
        :loading="typesLoading"
        @change="onTypeFilterChange"
      >
        <el-option v-for="t in types" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="用例状态" clearable style="width:120px" @change="onSearch">
        <el-option label="启用" value="enabled" />
        <el-option label="停用" value="disabled" />
      </el-select>
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-select
        v-model="verifyAgentId"
        placeholder="测试设计 Agent（核查）"
        clearable
        style="width:300px"
        @change="onVerifyAgentChange"
      >
        <el-option v-for="a in designAgents" :key="a.id" :label="agentLabel(a)" :value="a.id" />
      </el-select>
    </div>
    <template v-if="projectId">
      <el-table v-loading="tableLoading" :data="items" highlight-current-row @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="用例名称" min-width="220">
          <template #default="{ row }">
            <span class="case-name-link" @click="openDrawer(row, 'view')">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status !== 'disabled'"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              :loading="row._statusLoading"
              @change="(v: boolean) => toggleStatus(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="测试类型" min-width="140">
          <template #default="{ row }">
            <el-tag v-for="n in row.type_names" :key="n" size="small" style="margin-right:4px">{{ n }}</el-tag>
            <span v-if="!row.type_names?.length" class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDrawer(row, 'view')">查看</el-button>
            <el-button link type="primary" size="small" @click="openDrawer(row, 'edit')">编辑</el-button>
            <el-button link size="small" @click="quickLinkPlan(row)">添加到计划</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination-bar"
        @change="load"
        @size-change="onPageSizeChange"
      />
      <div v-if="selected.length" style="margin-top:12px">
        <el-button @click="batchLinkPlan">批量关联计划</el-button>
        <el-button @click="batchLinkType">批量修改类型</el-button>
        <el-button type="warning" @click="verifyCases">Agent 核查用例</el-button>
      </div>

      <el-dialog v-model="planDialogVisible" :title="planDialogTitle" width="400px">
        <el-select v-model="selectedPlanId" placeholder="选择测试计划" style="width:100%">
          <el-option v-for="p in plans" :key="p.id" :label="`${p.name}（${p.case_count ?? 0} 用例）`" :value="p.id" />
        </el-select>
        <p v-if="!plans.length" class="hint">暂无计划，请先在「测试计划」页创建</p>
        <template #footer>
          <el-button @click="planDialogVisible=false">取消</el-button>
          <el-button type="primary" :disabled="!selectedPlanId" @click="confirmLinkPlan">确定</el-button>
        </template>
      </el-dialog>

      <el-drawer
        v-model="drawerVisible"
        :title="drawerMode === 'edit' ? '编辑用例' : (activeCase?.name || '用例详情')"
        size="640px"
        destroy-on-close
      >
        <div v-loading="drawerLoading" class="case-drawer">
          <!-- 查看模式 -->
          <template v-if="drawerMode === 'view' && activeCase">
            <div class="detail-meta">
              <el-tag :type="activeCase.status === 'disabled' ? 'info' : 'success'">
                {{ activeCase.status === 'disabled' ? '停用' : '启用' }}
              </el-tag>
              <el-tag :type="priorityType(activeCase.priority)">{{ activeCase.priority }}</el-tag>
              <el-tag v-for="n in activeCase.type_names" :key="n" type="info" effect="plain">{{ n }}</el-tag>
            </div>

            <section class="detail-section">
              <h4>用例名称</h4>
              <p class="detail-text">{{ activeCase.name }}</p>
            </section>

            <section class="detail-section">
              <h4>前置条件</h4>
              <p class="detail-text">{{ activeCase.precondition || '—' }}</p>
            </section>

            <section class="detail-section">
              <h4>测试步骤</h4>
              <ol v-if="formatSteps(activeCase.steps).length" class="detail-steps">
                <li v-for="(step, i) in formatSteps(activeCase.steps)" :key="i">{{ step }}</li>
              </ol>
              <p v-else class="detail-text muted">—</p>
            </section>

            <section class="detail-section">
              <h4>预期结果</h4>
              <p class="detail-text pre-wrap">{{ activeCase.expected_result || '—' }}</p>
            </section>

            <section class="detail-section">
              <h4>标签</h4>
              <template v-if="activeCase.tags?.length">
                <el-tag v-for="t in activeCase.tags" :key="t" size="small" style="margin:0 6px 6px 0">{{ t }}</el-tag>
              </template>
              <p v-else class="detail-text muted">—</p>
            </section>

            <section class="detail-section">
              <h4>自动化脚本</h4>
              <pre v-if="activeCase.script_content" class="detail-code">{{ activeCase.script_content }}</pre>
              <p v-else class="detail-text muted">—</p>
            </section>

            <section class="detail-section detail-footer">
              <div class="detail-row"><span class="label">创建时间</span>{{ formatTime(activeCase.created_at) }}</div>
              <div class="detail-row"><span class="label">更新时间</span>{{ formatTime(activeCase.updated_at) }}</div>
              <div v-if="activeCase.test_point_id" class="detail-row">
                <span class="label">关联测试点</span>
                <span class="mono">{{ activeCase.test_point_id }}</span>
              </div>
            </section>

            <div class="drawer-footer">
              <el-button type="primary" @click="switchToEdit">编辑用例</el-button>
            </div>
          </template>

          <!-- 编辑模式 -->
          <template v-else-if="drawerMode === 'edit'">
            <el-form :model="editForm" label-width="96px" class="edit-form">
              <el-form-item label="用例名称" required>
                <el-input v-model="editForm.name" maxlength="500" show-word-limit />
              </el-form-item>
              <el-form-item label="状态">
                <el-radio-group v-model="editForm.status">
                  <el-radio value="enabled">启用</el-radio>
                  <el-radio value="disabled">停用</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="优先级">
                <el-select v-model="editForm.priority" style="width:120px">
                  <el-option v-for="p in ['P0','P1','P2','P3']" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
              <el-form-item label="测试类型">
                <el-select v-model="editForm.type_ids" multiple collapse-tags placeholder="选择类型" style="width:100%">
                  <el-option v-for="t in types" :key="t.id" :label="t.name" :value="t.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="前置条件">
                <el-input v-model="editForm.precondition" type="textarea" :rows="4" placeholder="执行用例前需满足的条件" />
              </el-form-item>
              <el-form-item label="测试步骤">
                <el-input
                  v-model="editForm.stepsText"
                  type="textarea"
                  :rows="8"
                  placeholder="每行一个步骤"
                />
              </el-form-item>
              <el-form-item label="预期结果">
                <el-input v-model="editForm.expected_result" type="textarea" :rows="5" />
              </el-form-item>
              <el-form-item label="标签">
                <el-input v-model="editForm.tagsText" placeholder="多个标签用英文逗号分隔" />
              </el-form-item>
              <el-form-item label="自动化脚本">
                <el-input v-model="editForm.script_content" type="textarea" :rows="6" placeholder="可选，自动化测试脚本" />
              </el-form-item>
            </el-form>
            <div class="drawer-footer">
              <el-button @click="cancelEdit">取消</el-button>
              <el-button type="primary" :loading="saving" @click="saveCase">保存</el-button>
            </div>
          </template>
        </div>
      </el-drawer>

      <el-dialog v-model="verifyVisible" title="用例核查报告" width="560px">
        <p><strong>智能体：</strong>{{ verifyReport.agent_name }}</p>
        <p><strong>评分：</strong>{{ verifyReport.report?.score ?? '-' }} / 100</p>
        <p><strong>总结：</strong>{{ verifyReport.report?.summary }}</p>
        <el-table v-if="verifyReport.report?.issues?.length" :data="verifyReport.report.issues" size="small">
          <el-table-column prop="case_name" label="用例" />
          <el-table-column prop="problem" label="问题" />
          <el-table-column prop="suggestion" label="建议" />
        </el-table>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import ProjectSelector from '@/components/ProjectSelector.vue'
import { selectedProjectId } from '@/stores/projectContext'
import { AGENT_KEYS, getStoredAgent, setStoredAgent } from '@/stores/agentContext'

const projectId = ref(selectedProjectId.value)
const items = ref<any[]>([])
const types = ref<any[]>([])
const plans = ref<any[]>([])
const selected = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const typesLoading = ref(false)
const tableLoading = ref(false)
const designAgents = ref<any[]>([])
const verifyAgentId = ref(getStoredAgent(AGENT_KEYS.designVerify))
const agentLabel = (a: any) => `${a.name} · ${a.model_provider || ''}/${a.model_name || '默认模型'}`
const onVerifyAgentChange = (id: string) => { if (id) setStoredAgent(AGENT_KEYS.designVerify, id) }
const verifyVisible = ref(false)
const verifyReport = ref<any>({})
const planDialogVisible = ref(false)
const planDialogTitle = ref('关联到计划')
const selectedPlanId = ref('')
const pendingCaseIds = ref<string[]>([])
const drawerVisible = ref(false)
const drawerLoading = ref(false)
const drawerMode = ref<'view' | 'edit'>('view')
const activeCase = ref<any>(null)
const saving = ref(false)
const editForm = ref({
  name: '',
  priority: 'P2',
  status: 'enabled',
  type_ids: [] as string[],
  precondition: '',
  stepsText: '',
  expected_result: '',
  tagsText: '',
  script_content: '',
})

const formatTime = (t?: string) => (t ? new Date(t).toLocaleString('zh-CN') : '—')

const priorityType = (p: string) => {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    P0: 'danger', P1: 'warning', P2: '', P3: 'info',
  }
  return map[p] || 'info'
}

const formatSteps = (steps: unknown): string[] => {
  if (!steps) return []
  if (Array.isArray(steps)) {
    return steps.map((s) => {
      if (typeof s === 'string') return s
      if (s && typeof s === 'object') {
        const o = s as Record<string, unknown>
        return String(o.action || o.step || o.desc || o.description || JSON.stringify(s))
      }
      return String(s)
    })
  }
  if (typeof steps === 'string') return steps.split('\n').filter(Boolean)
  return [String(steps)]
}

const stepsToText = (steps: unknown) => formatSteps(steps).join('\n')

const textToSteps = (text: string) => text.split('\n').map((s) => s.trim()).filter(Boolean)

const textToTags = (text: string) =>
  text.split(/[,，]/).map((s) => s.trim()).filter(Boolean)

const fillEditForm = (c: any) => {
  editForm.value = {
    name: c.name || '',
    priority: c.priority || 'P2',
    status: c.status || 'enabled',
    type_ids: c.type_ids || [],
    precondition: c.precondition || '',
    stepsText: stepsToText(c.steps),
    expected_result: c.expected_result || '',
    tagsText: (c.tags || []).join(', '),
    script_content: c.script_content || '',
  }
}

const fetchCaseDetail = async (id: string) => {
  const { data } = await http.get(`/test-cases/${id}`)
  return data
}

const openDrawer = async (row: any, mode: 'view' | 'edit') => {
  drawerVisible.value = true
  drawerLoading.value = true
  drawerMode.value = mode
  activeCase.value = null
  try {
    const data = await fetchCaseDetail(row.id)
    activeCase.value = data
    if (mode === 'edit') fillEditForm(data)
  } catch {
    ElMessage.error('加载用例详情失败')
    drawerVisible.value = false
  } finally {
    drawerLoading.value = false
  }
}

const switchToEdit = () => {
  if (!activeCase.value) return
  fillEditForm(activeCase.value)
  drawerMode.value = 'edit'
}

const cancelEdit = () => {
  if (activeCase.value) {
    drawerMode.value = 'view'
  } else {
    drawerVisible.value = false
  }
}

const saveCase = async () => {
  if (!activeCase.value?.id) return
  if (!editForm.value.name.trim()) return ElMessage.warning('用例名称不能为空')
  saving.value = true
  try {
    const { data } = await http.put(`/test-cases/${activeCase.value.id}`, {
      name: editForm.value.name.trim(),
      status: editForm.value.status,
      priority: editForm.value.priority,
      type_ids: editForm.value.type_ids,
      precondition: editForm.value.precondition || null,
      steps: textToSteps(editForm.value.stepsText),
      expected_result: editForm.value.expected_result || null,
      tags: textToTags(editForm.value.tagsText),
      script_content: editForm.value.script_content || null,
    })
    activeCase.value = data
    drawerMode.value = 'view'
    ElMessage.success('用例已保存')
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const toggleStatus = async (row: any, enabled: boolean) => {
  const newStatus = enabled ? 'enabled' : 'disabled'
  row._statusLoading = true
  try {
    await http.put(`/test-cases/${row.id}`, { status: newStatus })
    row.status = newStatus
    ElMessage.success(enabled ? '已启用' : '已停用')
    if (activeCase.value?.id === row.id) activeCase.value.status = newStatus
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '状态更新失败')
  } finally {
    row._statusLoading = false
  }
}

const onSelectionChange = (rows: any[]) => { selected.value = rows }

const loadPlans = async () => {
  if (!projectId.value) return (plans.value = [])
  const { data } = await http.get('/test-plans', { params: { project_id: projectId.value, page_size: 100 } })
  plans.value = data.items || []
}

const loadAgents = async () => {
  if (!projectId.value) return (designAgents.value = [])
  const { data } = await http.get('/agents', {
    params: { page: 1, page_size: 50, project_id: projectId.value, agent_type: 'design' },
  })
  let list = data.items || []
  if (!list.length) {
    const g = await http.get('/agents', { params: { page: 1, page_size: 50, agent_type: 'design' } })
    list = g.data.items || []
  }
  designAgents.value = list
  const valid = list.some((a: any) => a.id === verifyAgentId.value)
  if (!valid && list.length) verifyAgentId.value = list[0].id
}

const loadTypes = async () => {
  typesLoading.value = true
  try {
    const { data } = await http.get('/test-cases/types')
    types.value = data || []
  } catch {
    types.value = []
    ElMessage.error('加载测试类型失败')
  } finally {
    typesLoading.value = false
  }
}

const onSearch = () => {
  page.value = 1
  load()
}

const onTypeFilterChange = () => {
  page.value = 1
  load()
}

const onPageSizeChange = () => {
  page.value = 1
  load()
}

const load = async () => {
  if (!projectId.value) return
  tableLoading.value = true
  try {
    const { data } = await http.get('/test-cases', {
      params: {
        project_id: projectId.value,
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value || undefined,
        type_id: typeFilter.value || undefined,
        status: statusFilter.value || undefined,
      },
    })
    items.value = (data.items || []).map((item: any) => ({ ...item, status: item.status || 'enabled' }))
    total.value = data.total
  } finally {
    tableLoading.value = false
  }
}

const openPlanDialog = (caseIds: string[], title: string) => {
  pendingCaseIds.value = caseIds
  planDialogTitle.value = title
  selectedPlanId.value = plans.value[0]?.id || ''
  planDialogVisible.value = true
}

const confirmLinkPlan = async () => {
  if (!selectedPlanId.value) return
  const { data } = await http.post('/test-cases/batch-link-plan', { case_ids: pendingCaseIds.value, plan_id: selectedPlanId.value })
  ElMessage.success(data.message || '已关联')
  planDialogVisible.value = false
  loadPlans()
}

const quickLinkPlan = (row: any) => openPlanDialog([row.id], `添加「${row.name}」到计划`)
const batchLinkPlan = () => openPlanDialog(selected.value.map((c: any) => c.id), `批量关联 ${selected.value.length} 条用例`)

const verifyCases = async () => {
  const { data } = await http.post('/test-cases/verify', {
    project_id: projectId.value,
    case_ids: selected.value.map((c: any) => c.id),
    agent_id: verifyAgentId.value || undefined,
  })
  verifyReport.value = data
  verifyVisible.value = true
  ElMessage.success(`核查完成，评分 ${data.report?.score ?? '-'}`)
}

const batchLinkType = async () => {
  const typeId = typeFilter.value
  if (!typeId) return ElMessage.warning('请先选择类型筛选器中的类型')
  await http.post('/test-cases/batch-link-type', { case_ids: selected.value.map((c: any) => c.id), type_ids: [typeId] })
  ElMessage.success('批量关联类型完成')
  load()
}

watch(projectId, () => {
  if (projectId.value) {
    page.value = 1
    load()
    loadAgents()
    loadPlans()
  } else {
    items.value = []
    total.value = 0
  }
}, { immediate: true })

onMounted(loadTypes)
</script>

<style scoped>
.toolbar { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; align-items:center; }
.pagination-bar { margin-top: 16px; justify-content: flex-end; }
.hint { color:#909399; font-size:13px; margin-top:8px; }
.muted { color: #c0c4cc; font-size: 13px; }
.case-name-link {
  color: #409eff;
  cursor: pointer;
}
.case-name-link:hover { text-decoration: underline; }
.case-drawer { min-height: 200px; padding-bottom: 72px; position: relative; }
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}
.detail-section { margin-bottom: 20px; }
.detail-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.detail-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #606266;
  white-space: pre-wrap;
}
.detail-text.muted { color: #c0c4cc; }
.detail-steps {
  margin: 0;
  padding-left: 20px;
  font-size: 14px;
  line-height: 1.8;
  color: #606266;
}
.detail-code {
  margin: 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  max-height: 240px;
  white-space: pre-wrap;
  word-break: break-all;
}
.detail-footer { border-top: 1px solid #ebeef5; padding-top: 16px; }
.detail-row {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}
.detail-row .label {
  flex-shrink: 0;
  width: 72px;
  color: #909399;
}
.detail-row .mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  word-break: break-all;
}
.pre-wrap { white-space: pre-wrap; }
.drawer-footer {
  position: sticky;
  bottom: 0;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  background: #fff;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.edit-form { padding-right: 8px; }
</style>
