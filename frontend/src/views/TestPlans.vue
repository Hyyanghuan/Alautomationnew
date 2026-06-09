<template>
  <div>
    <div class="page-header">
      <h3>测试计划</h3>
      <el-button type="primary" :disabled="!projectId" @click="openCreate">新建计划</el-button>
    </div>
    <ProjectSelector v-model="projectId" hint="创建计划时需选择执行测试类型，执行时将绑定对应执行器与代码规则" />
    <el-empty v-if="!projectId" description="请先关联项目" />
    <el-table v-else :data="items" style="margin-top:16px" border>
      <el-table-column prop="name" label="计划名称" min-width="160" />
      <el-table-column label="执行类型" width="150">
        <template #default="{ row }">
          <el-tag type="primary" effect="plain" size="small">{{ row.executor_name || row.executor_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="executor_tech" label="技术底座" min-width="140" show-overflow-tooltip />
      <el-table-column prop="case_count" label="关联用例" width="100">
        <template #default="{ row }">
          <el-tag :type="row.case_count ? 'success' : 'warning'" size="small">{{ row.case_count || 0 }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="strategy" label="执行策略" width="100" />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link :disabled="!row.case_count" @click="runPlan(row.id)">立即执行</el-button>
          <el-button link @click="viewRule(row.executor_type)">代码规则</el-button>
          <el-button link @click="openEdit(row)">编辑</el-button>
          <el-button link @click="$router.push('/test-cases')">关联用例</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createVisible" :title="editId ? '编辑计划' : '新建测试计划'" width="520px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-form-item label="计划名称" required>
          <el-input v-model="form.name" placeholder="如：登录回归计划" />
        </el-form-item>
        <el-form-item label="执行类型" required>
          <el-select v-model="form.executor_type" style="width:100%" @change="onExecutorChange">
            <el-option
              v-for="o in executorOptions"
              :key="o.value"
              :label="o.label"
              :value="o.value"
            >
              <span>{{ o.label }}</span>
              <span style="float:right;color:#909399;font-size:12px">{{ o.tech }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-alert v-if="selectedExecutorDesc" type="info" :closable="false" show-icon style="margin-bottom:12px">
          {{ selectedExecutorDesc }}
        </el-alert>
        <el-form-item label="执行策略">
          <el-radio-group v-model="form.strategy">
            <el-radio value="parallel">并行</el-radio>
            <el-radio value="serial">串行</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePlan">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ruleVisible" :title="`代码规则 - ${currentRule?.name}`" width="80%" top="4vh">
      <p><strong>说明：</strong>{{ currentRule?.description }}</p>
      <p><strong>技术底座：</strong>{{ currentRule?.tech }}</p>
      <el-divider />
      <p><strong>执行规则：</strong></p>
      <ul>
        <li v-for="(r, i) in currentRule?.rules || []" :key="i">{{ r }}</li>
      </ul>
      <template v-if="currentRule?.case_format">
        <el-divider />
        <p><strong>用例格式示例：</strong></p>
        <pre class="code-block">{{ JSON.stringify(currentRule.case_format, null, 2) }}</pre>
      </template>
      <el-divider />
      <p><strong>完整执行器源码：</strong></p>
      <pre class="code-block code-full">{{ currentRule?.code_sample }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import ProjectSelector from '@/components/ProjectSelector.vue'
import { selectedProjectId } from '@/stores/projectContext'

const router = useRouter()
const projectId = ref(selectedProjectId.value)
const items = ref<any[]>([])
const executorOptions = ref<any[]>([])
const createVisible = ref(false)
const editId = ref('')
const saving = ref(false)
const ruleVisible = ref(false)
const currentRule = ref<any>(null)

const form = ref({
  name: '',
  description: '',
  strategy: 'parallel',
  executor_type: 'api',
})

const selectedExecutorDesc = computed(() => {
  const o = executorOptions.value.find((x) => x.value === form.value.executor_type)
  return o?.description || ''
})

const loadOptions = async () => {
  const { data } = await http.get('/test-plans/executor-options')
  executorOptions.value = data || []
}

const load = async () => {
  if (!projectId.value) return (items.value = [])
  const { data } = await http.get('/test-plans', { params: { project_id: projectId.value } })
  items.value = data.items
}

const openCreate = () => {
  editId.value = ''
  form.value = { name: '', description: '', strategy: 'parallel', executor_type: 'api' }
  createVisible.value = true
}

const openEdit = (row: any) => {
  editId.value = row.id
  form.value = {
    name: row.name,
    description: row.description || '',
    strategy: row.strategy || 'parallel',
    executor_type: row.executor_type || 'api',
  }
  createVisible.value = true
}

const onExecutorChange = () => { /* desc via computed */ }

const savePlan = async () => {
  if (!form.value.name.trim()) return ElMessage.warning('计划名称不能为空')
  saving.value = true
  try {
    if (editId.value) {
      await http.put(`/test-plans/${editId.value}`, form.value)
      ElMessage.success('计划已更新')
    } else {
      await http.post('/test-plans', { project_id: projectId.value, ...form.value })
      ElMessage.success('计划已创建，请到用例管理关联用例')
    }
    createVisible.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const viewRule = async (type: string) => {
  const { data } = await http.get(`/executions/executors/${type}/rules`)
  currentRule.value = data
  ruleVisible.value = true
}

const runPlan = async (id: string) => {
  try {
    const { data } = await http.post(`/executions/run/${id}`, {})
    ElMessage.success(data.summary || `执行完成: 通过 ${data.passed}/${data.total}`)
    if (data.execution_id) router.push(`/reports/${data.execution_id}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '执行失败')
  }
}

watch(projectId, load, { immediate: true })
loadOptions()
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.page-header h3 { margin: 0; }
.code-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
}
.code-full { max-height: 55vh; }
</style>
