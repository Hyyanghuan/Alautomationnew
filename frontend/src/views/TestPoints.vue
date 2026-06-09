<template>
  <div class="test-points-page">
    <h3 style="margin:0 0 8px">测试点管理</h3>
    <ProjectSelector v-model="projectId" hint="选择要关联的项目；需求文档与测试点均归属该项目" />
    <el-empty v-if="!projectId" description="请先关联项目" />
    <el-card v-else class="generate-bar" shadow="never">
      <div class="generate-bar-inner">
        <div class="generate-bar-title">
          <span class="title-text">生成测试点树</span>
          <span v-if="documents.length" class="doc-stat">
            已选 {{ selectedDocIds.length }} / {{ documents.length }} 份需求文档
          </span>
          <span v-else class="doc-stat muted">请先上传需求文档</span>
        </div>
        <div class="toolbar">
          <el-select v-model="generateTestType" placeholder="测试点类型" style="width:140px">
            <el-option label="功能测试" value="功能" />
            <el-option label="接口测试" value="接口" />
            <el-option label="Web页面" value="Web页面" />
            <el-option label="Agent测试" value="Agent测试" />
          </el-select>
          <el-select
            v-model="selectedAgentId"
            placeholder="选择测试设计 Agent（生成测试点/用例）"
            style="width:320px"
            :disabled="!designAgents.length"
            @change="onAgentChange"
          >
            <el-option
              v-for="a in designAgents"
              :key="a.id"
              :label="agentLabel(a)"
              :value="a.id"
            />
          </el-select>
          <el-select
            v-model="selectedKbIds"
            multiple
            collapse-tags
            placeholder="引用知识库（可选）"
            style="width:260px"
            @change="onKbChange"
          >
            <el-option v-for="k in knowledgeBases" :key="k.id" :label="k.name" :value="k.id" />
          </el-select>
          <el-button
            type="primary"
            :loading="generatingPoints"
            :disabled="!canGenerate"
            @click="aiGenerate"
          >
            Agent 生成测试点树
          </el-button>
        </div>
        <p v-if="!designAgents.length" class="bar-hint warn">
          暂无测试设计 Agent，请先在「Agent 管理」创建并绑定模型
        </p>
        <p v-else-if="documents.length && !selectedDocIds.length" class="bar-hint">
          请在下方需求文档列表中点选至少一份文档
        </p>
        <div v-if="generateTestType === 'Web页面'" class="web-locator-bar">
          <el-input v-model="webPageUrl" placeholder="目标页面 URL（可选）" style="width:280px" clearable />
          <el-input
            v-model="webLocatorHint"
            placeholder="元素定位提示，如：登录按钮 css:#login-btn"
            style="flex:1;min-width:240px"
            clearable
          />
        </div>
      </div>
    </el-card>
    <el-tabs v-if="projectId" v-model="activeTab">
      <el-tab-pane label="需求文档" name="docs">
        <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px">
          上传后点选需求文档，在上方选择测试设计 Agent，点击「Agent 生成测试点树」。支持 text、url、pdf、word、md、txt。
        </el-alert>
        <el-row :gutter="12" style="margin-bottom:16px">
          <el-col :span="8">
            <el-card shadow="never" header="文本录入">
              <el-input v-model="textForm.content" type="textarea" :rows="5" placeholder="粘贴需求文本" />
              <el-button type="primary" size="small" style="margin-top:8px" @click="uploadText">上传文本</el-button>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never" header="URL 链接">
              <el-input v-model="urlForm.url" placeholder="https://..." />
              <el-button type="primary" size="small" style="margin-top:8px" @click="uploadUrl">抓取 URL</el-button>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never" header="文件上传">
              <el-upload :show-file-list="false" :http-request="uploadFile">
                <el-button type="primary">选择 pdf/word/md/txt</el-button>
              </el-upload>
            </el-card>
          </el-col>
        </el-row>

        <div v-if="documents.length" class="doc-section">
          <div class="doc-section-toolbar">
            <span class="doc-section-label">已上传文档</span>
            <el-radio-group v-model="docViewMode" size="small" @change="onDocViewChange">
              <el-radio-button value="card">
                <el-icon><Grid /></el-icon> 卡片
              </el-radio-button>
              <el-radio-button value="list">
                <el-icon><List /></el-icon> 列表
              </el-radio-button>
            </el-radio-group>
            <el-button link type="primary" size="small" @click="selectAllDocs">全选</el-button>
            <el-button link size="small" :disabled="!selectedDocIds.length" @click="clearDocSelection">清空</el-button>
          </div>

          <!-- 卡片视图 -->
          <div v-if="docViewMode === 'card'" class="doc-cards">
            <div
              v-for="doc in documents"
              :key="doc.id"
              class="doc-card"
              :class="{ 'is-selected': isDocSelected(doc.id), 'is-unselected': !isDocSelected(doc.id) }"
              @click="toggleDoc(doc.id)"
            >
              <div class="doc-status-badge" :class="isDocSelected(doc.id) ? 'badge-on' : 'badge-off'">
                {{ isDocSelected(doc.id) ? '已选' : '未选' }}
              </div>
              <div class="doc-card-head">
                <span class="doc-check-box" :class="{ checked: isDocSelected(doc.id) }">
                  <el-icon><Select v-if="isDocSelected(doc.id)" /><span v-else class="check-empty" /></el-icon>
                </span>
                <span class="doc-title" :title="doc.title">{{ doc.title }}</span>
              </div>
              <div class="doc-meta">
                <el-tag size="small" :type="sourceTagType(doc.source_type)">{{ doc.source_type }}</el-tag>
                <span>{{ doc.char_count }} 字</span>
              </div>
              <div class="doc-time">{{ formatTime(doc.created_at) }}</div>
              <el-button link type="danger" size="small" class="doc-del" @click.stop="removeDoc(doc.id)">删除</el-button>
            </div>
          </div>

          <!-- 列表视图 -->
          <div v-else class="doc-list">
            <div
              v-for="doc in documents"
              :key="doc.id"
              class="doc-list-row"
              :class="{ 'is-selected': isDocSelected(doc.id), 'is-unselected': !isDocSelected(doc.id) }"
              @click="toggleDoc(doc.id)"
            >
              <span class="doc-check-box list-check" :class="{ checked: isDocSelected(doc.id) }">
                <el-icon><Select v-if="isDocSelected(doc.id)" /><span v-else class="check-empty" /></el-icon>
              </span>
              <div class="doc-list-main">
                <div class="doc-list-title-row">
                  <span class="doc-title" :title="doc.title">{{ doc.title }}</span>
                  <el-tag
                    size="small"
                    :type="isDocSelected(doc.id) ? 'primary' : 'info'"
                    effect="plain"
                    class="doc-select-tag"
                  >
                    {{ isDocSelected(doc.id) ? '已选中' : '点击选中' }}
                  </el-tag>
                </div>
                <div class="doc-meta">
                  <el-tag size="small" :type="sourceTagType(doc.source_type)">{{ doc.source_type }}</el-tag>
                  <span>{{ doc.char_count }} 字</span>
                  <span class="doc-time">{{ formatTime(doc.created_at) }}</span>
                </div>
              </div>
              <el-button link type="danger" size="small" @click.stop="removeDoc(doc.id)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无需求文档，请先上传" />
      </el-tab-pane>

      <el-tab-pane label="测试点树" name="tree">
        <div class="toolbar tree-toolbar">
          <el-button @click="saveTree">保存测试点树</el-button>
          <el-button @click="addRootNode">新增根节点</el-button>
          <el-button
            type="success"
            :loading="generatingCases"
            :disabled="!selectedIds.length || generatingCases"
            @click="generateCases"
          >
            使用当前 Agent 生成用例
          </el-button>
          <el-button
            link
            type="primary"
            :loading="generatingPoints"
            :disabled="!canGenerate || generatingPoints"
            @click="aiGenerate"
          >
            重新生成测试点
          </el-button>
          <el-radio-group v-model="treeViewMode" size="small" class="tree-view-switch">
            <el-radio-button value="tree">分叉树</el-radio-button>
            <el-radio-button value="mindmap">思维导图</el-radio-button>
          </el-radio-group>
        </div>
        <el-tree
          v-if="treeViewMode === 'tree'"
          ref="treeRef"
          :data="treeData"
          node-key="id"
          show-checkbox
          default-expand-all
          :props="{ label: 'name', children: 'children' }"
          @check="onCheck"
          draggable
        >
          <template #default="{ data }">
            <div class="tree-node-row" :class="{ 'is-active': activeNodeId === data.id }">
              <span class="tree-node-name" @click.stop="selectNode(data)">{{ data.name }}</span>
              <el-tag v-if="data.test_type" size="small" type="info" effect="plain">{{ data.test_type }}</el-tag>
              <el-tooltip v-if="data.locator?.value" :content="locatorLabel(data.locator)" placement="top">
                <el-tag size="small" type="warning" effect="plain">定位</el-tag>
              </el-tooltip>
              <span class="tree-node-actions" @click.stop>
                <el-button link type="primary" size="small" @click="editNode(data)">编辑</el-button>
                <el-button link type="primary" size="small" @click="addChildTo(data)">子节点</el-button>
                <el-button link type="danger" size="small" @click="deleteNode(data)">删除</el-button>
              </span>
            </div>
          </template>
        </el-tree>
        <MindMapView
          v-else
          :nodes="treeData"
          :active-id="activeNodeId"
          @select="selectNode"
          @edit="editNode"
          @delete="deleteNode"
          @add-child="addChildTo"
        />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="nodeEditVisible" title="编辑测试点" width="520px" destroy-on-close>
      <el-form :model="nodeEditForm" label-width="96px">
        <el-form-item label="名称" required>
          <el-input v-model="nodeEditForm.name" />
        </el-form-item>
        <el-form-item label="测试类型">
          <el-select v-model="nodeEditForm.test_type" clearable placeholder="继承上级或生成时类型" style="width:100%">
            <el-option label="功能" value="功能" />
            <el-option label="接口" value="接口" />
            <el-option label="Web页面" value="Web页面" />
            <el-option label="Agent测试" value="Agent测试" />
          </el-select>
        </el-form-item>
        <template v-if="nodeEditForm.test_type === 'Web页面'">
          <el-form-item label="定位策略">
            <el-select v-model="nodeEditForm.locator_strategy" style="width:100%">
              <el-option label="CSS 选择器" value="css" />
              <el-option label="XPath" value="xpath" />
              <el-option label="ID" value="id" />
              <el-option label="文本" value="text" />
              <el-option label="Role" value="role" />
            </el-select>
          </el-form-item>
          <el-form-item label="定位值">
            <el-input v-model="nodeEditForm.locator_value" placeholder="#login-btn 或 //button[@type='submit']" />
          </el-form-item>
          <el-form-item label="元素说明">
            <el-input v-model="nodeEditForm.locator_desc" placeholder="如：登录按钮" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="nodeEditVisible = false">取消</el-button>
        <el-button type="primary" @click="saveNodeEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid, List, Select } from '@element-plus/icons-vue'
import type { UploadRequestOptions } from 'element-plus'
import http from '@/api/http'
import ProjectSelector from '@/components/ProjectSelector.vue'
import MindMapView from '@/components/testpoints/MindMapView.vue'
import {
  addChildNode,
  cloneTree,
  ensureNodeIds,
  newNodeId,
  removeNode,
  updateNode,
  updateNodeName,
  type TreeNode,
} from '@/utils/testPointTree'
import { selectedProjectId } from '@/stores/projectContext'
import { AGENT_KEYS, getStoredAgent, getStoredKbIds, setStoredAgent, setStoredKbIds } from '@/stores/agentContext'

const router = useRouter()
const projectId = ref(selectedProjectId.value)
const activeTab = ref('docs')
const treeData = ref<TreeNode[]>([])
const selectedIds = ref<string[]>([])
const treeViewMode = ref<'tree' | 'mindmap'>('tree')
const activeNodeId = ref('')
const documents = ref<any[]>([])
const selectedDocIds = ref<string[]>([])
const designAgents = ref<any[]>([])
const knowledgeBases = ref<any[]>([])
const selectedAgentId = ref(getStoredAgent(AGENT_KEYS.designTestPoints))
const selectedKbIds = ref<string[]>(getStoredKbIds())
const agentLabel = (a: any) => `${a.name} · ${a.model_provider || ''}/${a.model_name || '默认模型'}`
const onAgentChange = (id: string) => setStoredAgent(AGENT_KEYS.designTestPoints, id)
const onKbChange = (ids: string[]) => setStoredKbIds(ids)
const textForm = ref({ content: '' })
const urlForm = ref({ url: '' })
const generatingPoints = ref(false)
const generatingCases = ref(false)
const generateTestType = ref('功能')
const webPageUrl = ref('')
const webLocatorHint = ref('')
const nodeEditVisible = ref(false)
const nodeEditId = ref('')
const nodeEditForm = ref({
  name: '',
  test_type: '' as string | undefined,
  locator_strategy: 'css',
  locator_value: '',
  locator_desc: '',
})
const DOC_VIEW_KEY = 'aitest_doc_view_mode'
const docViewMode = ref<'card' | 'list'>(
  (localStorage.getItem(DOC_VIEW_KEY) as 'card' | 'list') || 'card',
)

const canGenerate = computed(
  () => !!selectedDocIds.value.length && !!selectedAgentId.value && designAgents.value.length > 0,
)

const pid = () => projectId.value
const formatTime = (t?: string) => (t ? new Date(t).toLocaleString('zh-CN') : '')
const isDocSelected = (id: string) => selectedDocIds.value.includes(id)
const onDocViewChange = (mode: 'card' | 'list') => localStorage.setItem(DOC_VIEW_KEY, mode)
const sourceTagType = (type: string) => {
  const map: Record<string, string> = { text: '', url: 'success', file: 'warning', pdf: 'warning', word: 'warning' }
  return (map[type] || 'info') as '' | 'success' | 'warning' | 'info'
}
const selectAllDocs = () => { selectedDocIds.value = documents.value.map((d: any) => d.id) }
const clearDocSelection = () => { selectedDocIds.value = [] }

const loadDocs = async () => {
  if (!pid()) return (documents.value = [], (selectedDocIds.value = []))
  const { data } = await http.get(`/requirements/${pid()}`)
  documents.value = data
  selectedDocIds.value = selectedDocIds.value.filter((id) => data.some((d: any) => d.id === id))
}

const loadAgents = async () => {
  if (!pid()) return
  const { data } = await http.get('/agents', {
    params: { page: 1, page_size: 50, project_id: pid(), agent_type: 'design' },
  })
  let items = data.items || []
  if (!items.length) {
    const g = await http.get('/agents', { params: { page: 1, page_size: 50, agent_type: 'design' } })
    items = g.data.items || []
  }
  designAgents.value = items
  const valid = items.some((a: any) => a.id === selectedAgentId.value)
  if (!valid && items.length) selectedAgentId.value = items[0].id
  if (selectedAgentId.value) setStoredAgent(AGENT_KEYS.designTestPoints, selectedAgentId.value)
}

const loadKnowledgeBases = async () => {
  if (!pid()) return (knowledgeBases.value = [])
  const { data } = await http.get('/knowledge', { params: { project_id: pid() } })
  knowledgeBases.value = data || []
}

const loadTree = async () => {
  if (!pid()) return (treeData.value = [], (activeNodeId.value = ''))
  const { data } = await http.get(`/test-points/tree/${pid()}`)
  treeData.value = data.tree?.length ? ensureNodeIds(data.tree) : []
}

const selectNode = (node: TreeNode) => {
  activeNodeId.value = node.id || ''
}

const promptNodeName = async (title: string, defaultValue = '') => {
  const { value } = await ElMessageBox.prompt('请输入测试点名称', title, {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputValue: defaultValue,
    inputValidator: (v) => !!(v?.trim()) || '名称不能为空',
  })
  return value.trim()
}

const locatorLabel = (loc?: { strategy?: string; value?: string; description?: string }) => {
  if (!loc?.value) return ''
  const parts = [loc.strategy || 'css', loc.value]
  if (loc.description) parts.push(`(${loc.description})`)
  return parts.join(' ')
}

const editNode = (node: TreeNode) => {
  nodeEditId.value = node.id || ''
  nodeEditForm.value = {
    name: node.name,
    test_type: node.test_type || generateTestType.value,
    locator_strategy: node.locator?.strategy || 'css',
    locator_value: node.locator?.value || '',
    locator_desc: node.locator?.description || '',
  }
  nodeEditVisible.value = true
}

const saveNodeEdit = async () => {
  if (!nodeEditForm.value.name.trim()) return ElMessage.warning('名称不能为空')
  const patch: Partial<TreeNode> = {
    name: nodeEditForm.value.name.trim(),
    test_type: nodeEditForm.value.test_type || undefined,
  }
  if (nodeEditForm.value.test_type === 'Web页面' && nodeEditForm.value.locator_value.trim()) {
    patch.locator = {
      strategy: nodeEditForm.value.locator_strategy,
      value: nodeEditForm.value.locator_value.trim(),
      description: nodeEditForm.value.locator_desc.trim() || undefined,
    }
  } else {
    patch.locator = undefined
  }
  treeData.value = updateNode(cloneTree(treeData.value), nodeEditId.value, patch)
  nodeEditVisible.value = false
  await saveTree('已更新测试点')
}

const addChildTo = async (node: TreeNode) => {
  try {
    const name = await promptNodeName('新增子测试点')
    treeData.value = addChildNode(cloneTree(treeData.value), node.id!, name)
    await saveTree('已添加子测试点')
  } catch {
    /* cancelled */
  }
}

const addRootNode = async () => {
  try {
    const name = await promptNodeName('新增根测试点')
    treeData.value = [...cloneTree(treeData.value), { id: newNodeId(), name, children: [] }]
    await saveTree('已添加根测试点')
  } catch {
    /* cancelled */
  }
}

const deleteNode = async (node: TreeNode) => {
  try {
    await ElMessageBox.confirm(
      `确定删除「${node.name}」及其所有子测试点？`,
      '删除测试点',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    treeData.value = removeNode(cloneTree(treeData.value), node.id!)
    if (activeNodeId.value === node.id) activeNodeId.value = ''
    selectedIds.value = selectedIds.value.filter((id) => id !== node.id)
    await saveTree('已删除测试点')
  } catch {
    /* cancelled */
  }
}

const toggleDoc = (id: string) => {
  const i = selectedDocIds.value.indexOf(id)
  if (i >= 0) selectedDocIds.value.splice(i, 1)
  else selectedDocIds.value.push(id)
}

const selectUploadedDoc = (id?: string) => {
  if (id && !selectedDocIds.value.includes(id)) {
    selectedDocIds.value = [...selectedDocIds.value, id]
  }
}

const uploadText = async () => {
  if (!textForm.value.content.trim()) return ElMessage.warning('请输入文本')
  const { data } = await http.post('/requirements/text', { project_id: pid(), content: textForm.value.content })
  ElMessage.success('文本需求已上传，可点选文档后生成测试点')
  textForm.value.content = ''
  await loadDocs()
  selectUploadedDoc(data.id)
}

const uploadUrl = async () => {
  if (!urlForm.value.url) return ElMessage.warning('请输入 URL')
  const { data } = await http.post('/requirements/url', { project_id: pid(), url: urlForm.value.url })
  ElMessage.success('URL 需求已抓取，可点选文档后生成测试点')
  await loadDocs()
  selectUploadedDoc(data.id)
}

const uploadFile = async (opt: UploadRequestOptions) => {
  const fd = new FormData()
  fd.append('project_id', pid())
  fd.append('file', opt.file)
  const { data } = await http.post('/requirements/file', fd)
  ElMessage.success('文件已上传，可点选文档后生成测试点')
  await loadDocs()
  selectUploadedDoc(data.id)
}

const removeDoc = async (id: string) => {
  await http.delete(`/requirements/${id}`)
  selectedDocIds.value = selectedDocIds.value.filter((x) => x !== id)
  loadDocs()
}

const aiGenerate = async () => {
  if (!selectedDocIds.value.length) {
    activeTab.value = 'docs'
    return ElMessage.warning('请先在需求文档列表中点选至少一份文档')
  }
  if (!selectedAgentId.value) {
    return ElMessage.warning('请选择测试设计 Agent')
  }
  generatingPoints.value = true
  try {
    const { data } = await http.post('/test-points/generate', {
      project_id: pid(),
      agent_id: selectedAgentId.value,
      document_ids: selectedDocIds.value,
      kb_ids: selectedKbIds.value.length ? selectedKbIds.value : undefined,
      test_point_type: generateTestType.value,
      web_page_url: generateTestType.value === 'Web页面' ? webPageUrl.value || undefined : undefined,
      web_locator_hint: generateTestType.value === 'Web页面' ? webLocatorHint.value || undefined : undefined,
    })
    treeData.value = data.tree?.length ? ensureNodeIds(data.tree) : []
    activeTab.value = 'tree'
    const featMsg = data.features_sync?.message
    ElMessage.success(featMsg ? `${data.message}；${featMsg}` : data.message)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '生成失败')
  } finally {
    generatingPoints.value = false
  }
}

const saveTree = async (hint?: string) => {
  const { data } = await http.post('/test-points/tree/save', { project_id: pid(), tree: treeData.value })
  const featMsg = data.features_sync?.message
  ElMessage.success(hint || featMsg || '已保存')
  await loadTree()
}

const onCheck = (_: any, { checkedKeys }: any) => { selectedIds.value = checkedKeys }

const generateCases = async () => {
  if (!treeData.value.length) return ElMessage.warning('请先生成或编辑测试点树')
  if (!selectedIds.value.length) return ElMessage.warning('请勾选要生成用例的测试点（叶子节点）')
  if (!selectedAgentId.value) return ElMessage.warning('请选择测试设计 Agent')
  generatingCases.value = true
  try {
    await http.post('/test-points/tree/save', { project_id: pid(), tree: treeData.value })
    const docIds = selectedDocIds.value.length
      ? selectedDocIds.value
      : documents.value.map((d: any) => d.id)
    const { data } = await http.post(
      '/test-points/generate-cases',
      {
        project_id: pid(),
        test_point_ids: selectedIds.value,
        agent_id: selectedAgentId.value,
        document_ids: docIds.length ? docIds : undefined,
      },
      { timeout: 300000 },
    )
    ElMessage.success(data.message || `已生成 ${data.created_count} 条用例`)
    router.push('/test-cases')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '生成用例失败')
  } finally {
    generatingCases.value = false
  }
}

watch(projectId, () => {
  loadDocs()
  loadAgents()
  loadKnowledgeBases()
  loadTree()
}, { immediate: true })
</script>

<style scoped>
.generate-bar { margin-bottom: 16px; }
.generate-bar-inner { display: flex; flex-direction: column; gap: 10px; }
.generate-bar-title { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-text { font-weight: 600; font-size: 15px; }
.doc-stat { font-size: 13px; color: #409eff; }
.doc-stat.muted { color: #909399; }
.bar-hint { margin: 0; font-size: 13px; color: #909399; }
.bar-hint.warn { color: #e6a23c; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.doc-section { margin-top: 4px; }
.doc-section-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.doc-section-label { font-size: 14px; font-weight: 600; color: #303133; }
.doc-section-toolbar :deep(.el-radio-button__inner) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* 共用：选中勾选框 */
.doc-check-box {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 2px solid #c0c4cc;
  background: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}
.doc-check-box .el-icon { font-size: 14px; color: #fff; }
.doc-check-box .check-empty { width: 8px; height: 8px; border-radius: 2px; background: transparent; }
.doc-check-box.checked {
  border-color: #409eff;
  background: #409eff;
}

.doc-title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.4;
  word-break: break-all;
}
.doc-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
  flex-wrap: wrap;
}
.doc-time { font-size: 12px; color: #c0c4cc; }

/* 卡片视图 */
.doc-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.doc-card {
  border-radius: 10px;
  padding: 14px 14px 36px;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
}
.doc-card.is-unselected {
  border: 1px dashed #dcdfe6;
  background: #fafafa;
}
.doc-card.is-unselected:hover {
  border-color: #b3d8ff;
  background: #f5f9ff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.08);
}
.doc-card.is-selected {
  border: 2px solid #409eff;
  background: linear-gradient(135deg, #ecf5ff 0%, #f0f9ff 100%);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.18);
}
.doc-status-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.doc-status-badge.badge-off {
  color: #909399;
  background: #f0f2f5;
}
.doc-status-badge.badge-on {
  color: #fff;
  background: #409eff;
}
.doc-card-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
  padding-right: 48px;
}
.doc-card .doc-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.doc-card .doc-meta { margin-bottom: 6px; }
.doc-del { position: absolute; right: 10px; bottom: 8px; }

/* 列表视图 */
.doc-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.doc-list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.doc-list-row.is-unselected {
  border: 1px solid #ebeef5;
  background: #fff;
}
.doc-list-row.is-unselected:hover {
  border-color: #c6e2ff;
  background: #f5f9ff;
}
.doc-list-row.is-selected {
  border: 2px solid #409eff;
  background: #ecf5ff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
}
.doc-list-main { flex: 1; min-width: 0; }
.doc-list-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.doc-list .doc-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-select-tag { flex-shrink: 0; }

.tree-toolbar { margin-bottom: 12px; }
.tree-view-switch { margin-left: auto; }
.tree-node-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  padding: 2px 4px;
  border-radius: 4px;
}
.tree-node-row.is-active { background: #ecf5ff; }
.tree-node-name {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}
.tree-node-actions {
  display: none;
  flex-shrink: 0;
}
.tree-node-row:hover .tree-node-actions,
.tree-node-row.is-active .tree-node-actions {
  display: inline-flex;
  gap: 2px;
}
.web-locator-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
