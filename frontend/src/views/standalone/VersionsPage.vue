<template>
  <div>
    <div class="page-header">
      <h3>版本管理</h3>
      <el-button type="primary" :disabled="!projectId" @click="addVersion">新增版本</el-button>
    </div>
    <ProjectSelector v-model="projectId" hint="选择项目后管理版本状态" />
    <el-empty v-if="!projectId" description="请先关联项目" />
    <el-table v-else :data="versions" v-loading="loading" border>
      <el-table-column prop="version_number" label="版本号" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="versionStatusMeta(row.status).type" size="small">
            {{ versionStatusMeta(row.status).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="140" show-overflow-tooltip />
      <el-table-column prop="start_date" label="开始日期" width="110" />
      <el-table-column prop="release_date" label="发布日期" width="110" />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canVStart(row)" link type="success" @click="changeVStatus(row, 'start')">启动</el-button>
          <el-button v-if="canVSuspend(row)" link type="warning" @click="changeVStatus(row, 'suspend')">挂起</el-button>
          <el-button v-if="canVComplete(row)" link type="primary" @click="changeVStatus(row, 'complete')">完成</el-button>
          <el-button link @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showEdit" title="编辑版本" width="480px" destroy-on-close>
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="版本号" required>
          <el-input v-model="editForm.version_number" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="editForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-date-picker v-model="editForm.release_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'
import ProjectSelector from '@/components/ProjectSelector.vue'
import { selectedProjectId } from '@/stores/projectContext'

type VersionStatus = 'planning' | 'developing' | 'testing' | 'suspended' | 'released'
type VAction = 'start' | 'suspend' | 'complete'

const VERSION_LABELS: Record<VersionStatus, { label: string; type: '' | 'success' | 'warning' | 'info' }> = {
  planning: { label: '规划中', type: 'info' },
  developing: { label: '开发中', type: 'success' },
  testing: { label: '测试中', type: 'warning' },
  suspended: { label: '已挂起', type: 'warning' },
  released: { label: '已发布', type: '' },
}

const ACTION_LABELS: Record<VAction, string> = { start: '启动', suspend: '挂起', complete: '完成' }

const projectId = ref(selectedProjectId.value)
const versions = ref<any[]>([])
const loading = ref(false)
const showEdit = ref(false)
const editForm = ref({ id: '', version_number: '', description: '', start_date: null as string | null, release_date: null as string | null })

const versionStatusMeta = (s: VersionStatus) => VERSION_LABELS[s] || { label: s, type: 'info' as const }
const canVStart = (row: any) => ['planning', 'suspended'].includes(row.status)
const canVSuspend = (row: any) => ['developing', 'testing'].includes(row.status)
const canVComplete = (row: any) => row.status !== 'released'

const load = async () => {
  if (!projectId.value) return (versions.value = [])
  loading.value = true
  const { data } = await http.get(`/projects/${projectId.value}/versions`)
  versions.value = data
  loading.value = false
}

const addVersion = async () => {
  const { value } = await ElMessageBox.prompt('版本号，如 V1.0.0', '新增版本')
  if (value) {
    await http.post(`/projects/${projectId.value}/versions`, { version_number: value })
    ElMessage.success('已添加')
    load()
  }
}

const openEdit = (row: any) => {
  editForm.value = {
    id: row.id,
    version_number: row.version_number,
    description: row.description || '',
    start_date: row.start_date || null,
    release_date: row.release_date || null,
  }
  showEdit.value = true
}

const saveEdit = async () => {
  await http.put(`/projects/versions/${editForm.value.id}`, {
    version_number: editForm.value.version_number,
    description: editForm.value.description || null,
    start_date: editForm.value.start_date || null,
    release_date: editForm.value.release_date || null,
  })
  ElMessage.success('已保存')
  showEdit.value = false
  load()
}

const changeVStatus = async (row: any, action: VAction) => {
  try {
    await ElMessageBox.confirm(`确定将版本「${row.version_number}」${ACTION_LABELS[action]}吗？`, '确认', { type: 'warning' })
    await http.post(`/projects/versions/${row.id}/status`, { action })
    ElMessage.success(`已${ACTION_LABELS[action]}`)
    load()
  } catch { /* cancel */ }
}

watch(projectId, load, { immediate: true })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.page-header h3 { margin: 0; }
</style>
