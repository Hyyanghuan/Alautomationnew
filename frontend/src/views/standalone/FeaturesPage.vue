<template>
  <div class="features-page">
    <div class="page-header">
      <h3>功能管理</h3>
      <div class="header-actions">
        <el-button :disabled="!projectId" :loading="syncing" @click="syncFeatures">从测试点同步</el-button>
      </div>
    </div>
    <ProjectSelector v-model="projectId" hint="功能由测试点树自动同步；展开功能可查看测试点与测试用例" />
    <el-alert v-if="projectId" type="info" :closable="false" show-icon style="margin-bottom:12px">
      展开功能行可查看下属测试点与测试用例。单击用例名右侧展开详情；双击用例名可编辑。
    </el-alert>
    <el-empty v-if="!projectId" description="请先关联项目" />
    <el-row v-else :gutter="16">
      <el-col :span="casePanelVisible ? 15 : 24">
        <el-table :data="features" v-loading="loading" border row-key="feature_name">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-box">
                <el-tabs>
                  <el-tab-pane :label="`测试点（${countPoints(row.test_points)}）`">
                    <FeaturePointList
                      :points="row.test_points || []"
                      @edit="(pt) => editTestPoint(pt)"
                      @delete="(pt) => deleteTestPoint(row, pt)"
                    />
                  </el-tab-pane>
                  <el-tab-pane :label="`测试用例（${(row.test_cases || []).length}）`">
                    <el-table
                      v-if="row.test_cases?.length"
                      :data="row.test_cases"
                      size="small"
                      border
                      highlight-current-row
                      :row-class-name="caseRowClass"
                      @row-click="onCaseClick"
                    >
                      <el-table-column prop="name" label="用例名称" min-width="200">
                        <template #default="{ row: c }">
                          <span
                            class="case-name-cell"
                            :class="{ active: selectedCase?.id === c.id }"
                            @click.stop="selectCase(c)"
                            @dblclick.stop="editCase(c)"
                          >
                            {{ c.name }}
                          </span>
                          <el-icon v-if="selectedCase?.id === c.id" class="case-expand-icon"><ArrowRight /></el-icon>
                        </template>
                      </el-table-column>
                      <el-table-column prop="priority" label="优先级" width="80" />
                      <el-table-column label="状态" width="80">
                        <template #default="{ row: c }">
                          <el-tag :type="c.status === 'disabled' ? 'info' : 'success'" size="small">
                            {{ c.status === 'disabled' ? '停用' : '启用' }}
                          </el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column label="类型" min-width="120">
                        <template #default="{ row: c }">
                          <el-tag v-for="n in c.type_names" :key="n" size="small" style="margin-right:4px">{{ n }}</el-tag>
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-empty v-else description="该功能下暂无测试用例" :image-size="64" />
                  </el-tab-pane>
                </el-tabs>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="feature_name" label="功能名称" min-width="160" />
          <el-table-column prop="description" label="描述" show-overflow-tooltip min-width="180" />
          <el-table-column prop="introduced_version" label="引入版本" width="110" />
          <el-table-column prop="removed_version" label="废弃版本" width="110" />
          <el-table-column label="用例数" width="80">
            <template #default="{ row }">{{ row.test_cases?.length || 0 }}</template>
          </el-table-column>
          <el-table-column label="更新时间" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at || row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" :disabled="!row.id" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="deleteFeature(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-col>

      <el-col v-if="casePanelVisible" :span="9">
        <el-card shadow="never" class="case-panel" v-loading="caseLoading">
          <template #header>
            <div class="case-panel-head">
              <span>{{ casePanelMode === 'edit' ? '编辑用例' : '用例详情' }}</span>
              <el-button link @click="closeCasePanel">关闭</el-button>
            </div>
          </template>

          <template v-if="casePanelMode === 'view' && activeCase">
            <div class="detail-meta">
              <el-tag :type="activeCase.status === 'disabled' ? 'info' : 'success'">
                {{ activeCase.status === 'disabled' ? '停用' : '启用' }}
              </el-tag>
              <el-tag>{{ activeCase.priority }}</el-tag>
              <el-tag v-for="n in activeCase.type_names" :key="n" type="info" effect="plain">{{ n }}</el-tag>
            </div>
            <section class="detail-section">
              <h4>用例名称</h4>
              <p>{{ activeCase.name }}</p>
            </section>
            <section class="detail-section">
              <h4>前置条件</h4>
              <p class="pre-wrap">{{ activeCase.precondition || '—' }}</p>
            </section>
            <section class="detail-section">
              <h4>测试步骤</h4>
              <ol v-if="formatSteps(activeCase.steps).length" class="detail-steps">
                <li v-for="(step, i) in formatSteps(activeCase.steps)" :key="i">{{ step }}</li>
              </ol>
              <p v-else class="muted">—</p>
            </section>
            <section class="detail-section">
              <h4>预期结果</h4>
              <p class="pre-wrap">{{ activeCase.expected_result || '—' }}</p>
            </section>
            <div class="panel-footer">
              <el-button type="primary" size="small" @click="switchCaseToEdit">编辑</el-button>
            </div>
          </template>

          <template v-else-if="casePanelMode === 'edit'">
            <el-form :model="caseEditForm" label-width="80px" size="small">
              <el-form-item label="名称" required>
                <el-input v-model="caseEditForm.name" />
              </el-form-item>
              <el-form-item label="状态">
                <el-radio-group v-model="caseEditForm.status">
                  <el-radio value="enabled">启用</el-radio>
                  <el-radio value="disabled">停用</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="优先级">
                <el-select v-model="caseEditForm.priority" style="width:100px">
                  <el-option v-for="p in ['P0','P1','P2','P3']" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
              <el-form-item label="测试类型">
                <el-select v-model="caseEditForm.type_ids" multiple collapse-tags style="width:100%">
                  <el-option v-for="t in caseTypes" :key="t.id" :label="t.name" :value="t.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="前置条件">
                <el-input v-model="caseEditForm.precondition" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="测试步骤">
                <el-input
                  v-model="caseEditForm.stepsText"
                  type="textarea"
                  :rows="8"
                  placeholder="JSON 步骤数组，或每行一个文本步骤"
                />
              </el-form-item>
              <el-form-item label="预期结果">
                <el-input v-model="caseEditForm.expected_result" type="textarea" :rows="4" />
              </el-form-item>
            </el-form>
            <div class="panel-footer">
              <el-button size="small" @click="cancelCaseEdit">取消</el-button>
              <el-button type="primary" size="small" :loading="caseSaving" @click="saveCase">保存</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="editVisible" title="编辑功能" width="480px" destroy-on-close>
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="功能名称" required>
          <el-input v-model="editForm.feature_name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="引入版本">
          <el-input v-model="editForm.introduced_version" placeholder="如 v1.0" />
        </el-form-item>
        <el-form-item label="废弃版本">
          <el-input v-model="editForm.removed_version" placeholder="如 v2.0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveFeature">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import http from '@/api/http'
import ProjectSelector from '@/components/ProjectSelector.vue'
import FeaturePointList, { type FeaturePoint } from '@/components/features/FeaturePointList.vue'
import { selectedProjectId } from '@/stores/projectContext'

type CaseSummary = {
  id: string
  name: string
  priority: string
  status: string
  type_names?: string[]
  type_ids?: string[]
  precondition?: string
  steps?: unknown
  expected_result?: string
  tags?: string[]
  script_content?: string
  test_point_id?: string
  created_at?: string
  updated_at?: string
}

type FeatureRow = {
  id?: string
  feature_name: string
  description?: string
  introduced_version?: string
  removed_version?: string
  created_at?: string
  updated_at?: string
  test_points?: FeaturePoint[]
  test_cases?: CaseSummary[]
  root_point_id?: string
}

const projectId = ref(selectedProjectId.value)
const features = ref<FeatureRow[]>([])
const loading = ref(false)
const syncing = ref(false)
const editVisible = ref(false)
const saving = ref(false)
const editForm = ref({
  id: '',
  feature_name: '',
  description: '',
  introduced_version: '',
  removed_version: '',
})

const selectedCase = ref<CaseSummary | null>(null)
const activeCase = ref<CaseSummary | null>(null)
const casePanelMode = ref<'view' | 'edit'>('view')
const caseLoading = ref(false)
const caseSaving = ref(false)
const caseTypes = ref<any[]>([])
const caseEditForm = ref({
  name: '',
  priority: 'P2',
  status: 'enabled',
  type_ids: [] as string[],
  precondition: '',
  stepsText: '',
  expected_result: '',
})

const casePanelVisible = computed(() => !!selectedCase.value)

const formatTime = (t?: string) => (t ? new Date(t).toLocaleString('zh-CN') : '-')

const countPoints = (points: FeaturePoint[] = []): number => {
  let n = 0
  const walk = (list: FeaturePoint[]) => {
    for (const p of list) {
      n += 1
      if (p.children?.length) walk(p.children)
    }
  }
  walk(points)
  return n
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

const stepsToText = (steps: unknown) => {
  if (!steps) return ''
  if (Array.isArray(steps) && steps.some((s) => s && typeof s === 'object')) {
    return JSON.stringify(steps, null, 2)
  }
  return formatSteps(steps).join('\n')
}

const textToSteps = (text: string) => {
  const trimmed = text.trim()
  if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
    try {
      return JSON.parse(trimmed)
    } catch {
      /* 回退为逐行文本 */
    }
  }
  return trimmed.split('\n').map((s) => s.trim()).filter(Boolean)
}

const loadCaseTypes = async () => {
  try {
    const { data } = await http.get('/test-cases/types')
    caseTypes.value = data || []
  } catch {
    caseTypes.value = []
  }
}

const load = async () => {
  if (!projectId.value) return (features.value = [])
  loading.value = true
  try {
    const { data } = await http.get(`/projects/${projectId.value}/features/detail`)
    features.value = data
  } finally {
    loading.value = false
  }
}

const syncFeatures = async () => {
  syncing.value = true
  try {
    const { data } = await http.post(`/projects/${projectId.value}/features/sync-from-test-points`)
    ElMessage.success(data.message || '同步完成')
    await load()
  } finally {
    syncing.value = false
  }
}

const openEdit = (row: FeatureRow) => {
  if (!row.id) return ElMessage.warning('请先从测试点同步后再编辑元数据')
  editForm.value = {
    id: row.id,
    feature_name: row.feature_name,
    description: row.description || '',
    introduced_version: row.introduced_version || '',
    removed_version: row.removed_version || '',
  }
  editVisible.value = true
}

const saveFeature = async () => {
  if (!editForm.value.feature_name.trim()) return ElMessage.warning('功能名称不能为空')
  saving.value = true
  try {
    await http.put(`/projects/features/${editForm.value.id}`, {
      feature_name: editForm.value.feature_name.trim(),
      description: editForm.value.description || null,
      introduced_version: editForm.value.introduced_version || null,
      removed_version: editForm.value.removed_version || null,
    })
    ElMessage.success('功能已更新')
    editVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

const deleteFeature = async (row: FeatureRow) => {
  try {
    await ElMessageBox.confirm(
      `确定删除功能「${row.feature_name}」及其全部测试点？`,
      '删除功能',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    if (row.id) {
      const { data } = await http.delete(`/projects/features/${row.id}`)
      ElMessage.success(data.message || '已删除')
    } else if (row.root_point_id) {
      const { data } = await http.delete(`/test-points/node/${row.root_point_id}`, {
        params: { project_id: projectId.value },
      })
      ElMessage.success(data.message || '已删除')
    } else {
      return ElMessage.warning('无法定位该功能对应的测试点')
    }
    if (selectedCase.value) closeCasePanel()
    await load()
  } catch {
    /* cancelled */
  }
}

const editTestPoint = async (pt: FeaturePoint) => {
  if (!pt.id) return ElMessage.warning('该测试点尚未保存')
  try {
    const { value } = await ElMessageBox.prompt('请输入测试点名称', '编辑测试点', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: pt.name,
      inputValidator: (v) => !!(v?.trim()) || '名称不能为空',
    })
    const { data: treeRes } = await http.get(`/test-points/tree/${projectId.value}`)
    const tree = treeRes.tree || []
    const rename = (nodes: any[]): any[] =>
      nodes.map((n) => ({
        ...n,
        name: n.id === pt.id ? value.trim() : n.name,
        children: n.children?.length ? rename(n.children) : [],
      }))
    const { data } = await http.post('/test-points/tree/save', {
      project_id: projectId.value,
      tree: rename(tree),
      remark: '编辑测试点',
    })
    ElMessage.success(data.features_sync?.message || '测试点已更新')
    await load()
  } catch {
    /* cancelled */
  }
}

const deleteTestPoint = async (row: FeatureRow, pt: FeaturePoint) => {
  if (!pt.id) return
  try {
    await ElMessageBox.confirm(
      `确定删除测试点「${pt.name}」及其子节点？`,
      '删除测试点',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    const { data } = await http.delete(`/test-points/node/${pt.id}`, {
      params: { project_id: projectId.value },
    })
    ElMessage.success(data.message || '已删除')
    await load()
  } catch {
    /* cancelled */
  }
}

const fetchCaseDetail = async (id: string) => {
  const { data } = await http.get(`/test-cases/${id}`)
  return data
}

const fillCaseEditForm = (c: CaseSummary & { type_ids?: (string | { toString(): string })[] }) => {
  caseEditForm.value = {
    name: c.name || '',
    priority: c.priority || 'P2',
    status: c.status || 'enabled',
    type_ids: (c.type_ids || []).map((id) => String(id)),
    precondition: c.precondition || '',
    stepsText: stepsToText(c.steps),
    expected_result: c.expected_result || '',
  }
}

const selectCase = async (c: CaseSummary) => {
  selectedCase.value = c
  casePanelMode.value = 'view'
  caseLoading.value = true
  activeCase.value = null
  try {
    activeCase.value = await fetchCaseDetail(c.id)
  } catch {
    ElMessage.error('加载用例详情失败')
    closeCasePanel()
  } finally {
    caseLoading.value = false
  }
}

const onCaseClick = (row: CaseSummary) => selectCase(row)

const editCase = async (c: CaseSummary) => {
  selectedCase.value = c
  casePanelMode.value = 'edit'
  caseLoading.value = true
  try {
    const data = await fetchCaseDetail(c.id)
    activeCase.value = data
    fillCaseEditForm(data)
  } catch {
    ElMessage.error('加载用例失败')
    closeCasePanel()
  } finally {
    caseLoading.value = false
  }
}

const switchCaseToEdit = () => {
  if (!activeCase.value) return
  fillCaseEditForm(activeCase.value)
  casePanelMode.value = 'edit'
}

const cancelCaseEdit = () => {
  if (activeCase.value) {
    casePanelMode.value = 'view'
  } else {
    closeCasePanel()
  }
}

const saveCase = async () => {
  if (!activeCase.value?.id) return
  if (!caseEditForm.value.name.trim()) return ElMessage.warning('用例名称不能为空')
  caseSaving.value = true
  try {
    const { data } = await http.put(`/test-cases/${activeCase.value.id}`, {
      name: caseEditForm.value.name.trim(),
      status: caseEditForm.value.status,
      priority: caseEditForm.value.priority,
      type_ids: caseEditForm.value.type_ids,
      precondition: caseEditForm.value.precondition || null,
      steps: textToSteps(caseEditForm.value.stepsText),
      expected_result: caseEditForm.value.expected_result || null,
    })
    activeCase.value = data
    selectedCase.value = { ...selectedCase.value!, name: data.name, priority: data.priority, status: data.status }
    casePanelMode.value = 'view'
    ElMessage.success('用例已保存')
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    caseSaving.value = false
  }
}

const closeCasePanel = () => {
  selectedCase.value = null
  activeCase.value = null
  casePanelMode.value = 'view'
}

const caseRowClass = ({ row }: { row: CaseSummary }) =>
  selectedCase.value?.id === row.id ? 'case-row-active' : ''

watch(projectId, () => {
  closeCasePanel()
  load()
}, { immediate: true })

onMounted(loadCaseTypes)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.page-header h3 { margin: 0; }
.header-actions { display: flex; gap: 8px; }
.expand-box { padding: 8px 16px 12px; }
.case-name-cell {
  cursor: pointer;
  color: #303133;
}
.case-name-cell.active {
  color: #409eff;
  font-weight: 600;
}
.case-expand-icon {
  margin-left: 6px;
  color: #409eff;
  vertical-align: middle;
}
.case-panel { position: sticky; top: 12px; }
.case-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.detail-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.detail-section { margin-bottom: 14px; }
.detail-section h4 {
  margin: 0 0 6px;
  font-size: 13px;
  color: #606266;
}
.detail-section p { margin: 0; font-size: 14px; line-height: 1.6; }
.detail-steps { margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.6; }
.pre-wrap { white-space: pre-wrap; }
.muted { color: #909399; }
.panel-footer { margin-top: 12px; display: flex; gap: 8px; justify-content: flex-end; }
:deep(.case-row-active) {
  background: #ecf5ff !important;
}
</style>
