<template>
  <div>
    <div class="toolbar">
      <h3 style="margin:0">项目管理</h3>
      <div>
        <el-input
          v-model="keyword"
          placeholder="搜索项目"
          style="width:240px;margin-right:8px"
          clearable
          @keyup.enter="load"
          @clear="load"
        />
        <el-button @click="load">查询</el-button>
        <el-button type="primary" @click="openCreate">新建项目</el-button>
      </div>
    </div>
    <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px">
      管理项目状态（启动/暂停/挂起/完成/重启）及描述、计划起止时间；各模块通过「关联项目」选择器绑定项目。
    </el-alert>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="name" label="项目名称" min-width="140" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMeta(row.status).type" size="small">{{ statusMeta(row.status).label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
      <el-table-column label="开始时间" width="120">
        <template #default="{ row }">{{ row.start_date || '-' }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="120">
        <template #default="{ row }">{{ row.end_date || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="360" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canStart(row)" link type="success" @click="changeStatus(row, 'start')">启动</el-button>
          <el-button v-if="canPause(row)" link type="warning" @click="changeStatus(row, 'pause')">暂停</el-button>
          <el-button v-if="canSuspend(row)" link type="warning" @click="changeStatus(row, 'suspend')">挂起</el-button>
          <el-button v-if="canComplete(row)" link type="primary" @click="changeStatus(row, 'complete')">完成</el-button>
          <el-button v-if="canRestart(row)" link type="success" @click="changeStatus(row, 'restart')">重启</el-button>
          <el-button link @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @change="load"
      layout="total, sizes, prev, pager, next"
      :page-sizes="[10, 20, 50]"
      style="margin-top:16px"
    />

    <el-dialog v-model="showCreate" title="新建项目" width="520px" destroy-on-close>
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="项目描述" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="createForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="计划开始" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="createForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="计划结束" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="create">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" title="编辑项目" width="520px" destroy-on-close>
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="项目名称" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" placeholder="修改项目描述" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="editForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="editForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="当前状态">
          <el-tag :type="statusMeta(editForm.status).type">{{ statusMeta(editForm.status).label }}</el-tag>
          <span class="edit-hint">状态请通过列表操作按钮变更</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'

type ProjectStatus = 'planning' | 'active' | 'paused' | 'suspended' | 'completed' | 'archived'
type StatusAction = 'start' | 'pause' | 'suspend' | 'complete' | 'restart'

interface ProjectRow {
  id: string
  name: string
  description?: string
  status: ProjectStatus
  start_date?: string | null
  end_date?: string | null
  created_at?: string
}

const STATUS_LABELS: Record<ProjectStatus, { label: string; type: '' | 'success' | 'warning' | 'info' | 'danger' }> = {
  planning: { label: '规划中', type: 'info' },
  active: { label: '进行中', type: 'success' },
  paused: { label: '已暂停', type: 'warning' },
  suspended: { label: '已挂起', type: 'warning' },
  completed: { label: '已完成', type: '' },
  archived: { label: '已归档', type: 'info' },
}

const ACTION_LABELS: Record<StatusAction, string> = {
  start: '启动',
  pause: '暂停',
  suspend: '挂起',
  complete: '完成',
  restart: '重启',
}

const items = ref<ProjectRow[]>([])
const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')
const showCreate = ref(false)
const showEdit = ref(false)

const emptyForm = () => ({
  id: '',
  name: '',
  description: '',
  start_date: null as string | null,
  end_date: null as string | null,
  status: 'planning' as ProjectStatus,
})

const createForm = ref(emptyForm())
const editForm = ref(emptyForm())

const statusMeta = (s: ProjectStatus) => STATUS_LABELS[s] || { label: s, type: 'info' as const }
const formatTime = (t?: string) => (t ? new Date(t).toLocaleString('zh-CN') : '-')
const isTerminal = (row: ProjectRow) => row.status === 'archived'

const canStart = (row: ProjectRow) => !isTerminal(row) && ['planning', 'paused', 'suspended'].includes(row.status)
const canPause = (row: ProjectRow) => row.status === 'active'
const canSuspend = (row: ProjectRow) => ['active', 'paused'].includes(row.status)
const canComplete = (row: ProjectRow) => !isTerminal(row) && row.status !== 'completed'
const canRestart = (row: ProjectRow) => ['paused', 'suspended', 'completed'].includes(row.status)

const validateDates = (start?: string | null, end?: string | null) => {
  if (start && end && start > end) {
    ElMessage.warning('开始时间不能晚于结束时间')
    return false
  }
  return true
}

const load = async () => {
  loading.value = true
  try {
    const { data } = await http.get('/projects', {
      params: { page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined },
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  createForm.value = { name: '', description: '', start_date: null, end_date: null, id: '', status: 'planning' }
  showCreate.value = true
}

const create = async () => {
  if (!createForm.value.name.trim()) return ElMessage.warning('请输入项目名称')
  if (!validateDates(createForm.value.start_date, createForm.value.end_date)) return
  await http.post('/projects', {
    name: createForm.value.name,
    description: createForm.value.description || undefined,
    start_date: createForm.value.start_date || undefined,
    end_date: createForm.value.end_date || undefined,
  })
  ElMessage.success('创建成功')
  showCreate.value = false
  load()
}

const openEdit = (row: ProjectRow) => {
  editForm.value = {
    id: row.id,
    name: row.name,
    description: row.description || '',
    start_date: row.start_date || null,
    end_date: row.end_date || null,
    status: row.status,
  }
  showEdit.value = true
}

const saveEdit = async () => {
  if (!editForm.value.name.trim()) return ElMessage.warning('请输入项目名称')
  if (!validateDates(editForm.value.start_date, editForm.value.end_date)) return
  saving.value = true
  try {
    await http.put(`/projects/${editForm.value.id}`, {
      name: editForm.value.name,
      description: editForm.value.description || null,
      start_date: editForm.value.start_date || null,
      end_date: editForm.value.end_date || null,
    })
    ElMessage.success('已保存')
    showEdit.value = false
    load()
  } finally {
    saving.value = false
  }
}

const changeStatus = async (row: ProjectRow, action: StatusAction) => {
  try {
    await ElMessageBox.confirm(`确定将项目「${row.name}」${ACTION_LABELS[action]}吗？`, '确认操作', { type: 'warning' })
    await http.post(`/projects/${row.id}/status`, { action })
    ElMessage.success(`已${ACTION_LABELS[action]}`)
    load()
  } catch {
    /* 取消 */
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.edit-hint {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
