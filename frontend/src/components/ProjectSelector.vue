<template>
  <el-card shadow="never" class="project-selector">
    <el-form :inline="true">
      <el-form-item label="关联项目">
        <el-select
          v-model="model"
          filterable
          remote
          clearable
          :remote-method="onSearch"
          :loading="loading"
          placeholder="请选择已创建的项目"
          style="width: 320px"
          popper-class="project-select-dropdown"
          @visible-change="onVisibleChange"
          @change="onChange"
        >
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id">
            <div class="option-row">
              <span class="option-name">{{ p.name }}</span>
              <span class="option-time">{{ formatTime(p.created_at) }}</span>
            </div>
          </el-option>
          <template v-if="loadingMore" #footer>
            <div class="select-footer">加载中...</div>
          </template>
          <template v-else-if="hasMore && projects.length" #footer>
            <div class="select-footer">向下滚动加载更多（{{ projects.length }}/{{ total }}）</div>
          </template>
        </el-select>
      </el-form-item>
      <el-form-item v-if="hint">
        <span class="hint">{{ hint }}</span>
      </el-form-item>
      <slot name="extra" />
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import http from '@/api/http'
import { selectedProjectId, setSelectedProject } from '@/stores/projectContext'

const PAGE_SIZE = 10

withDefaults(
  defineProps<{
    hint?: string
    required?: boolean
  }>(),
  { hint: '各模块独立管理，通过此处关联项目', required: false }
)

const model = defineModel<string>({ default: '' })

interface ProjectItem {
  id: string
  name: string
  created_at?: string
}

const projects = ref<ProjectItem[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const page = ref(1)
const total = ref(0)
const keyword = ref('')
let scrollEl: HTMLElement | null = null
let searchTimer: ReturnType<typeof setTimeout> | null = null

const hasMore = computed(() => projects.value.length < total.value)

const formatTime = (t?: string) => (t ? new Date(t).toLocaleString('zh-CN') : '')

const mergeItems = (incoming: ProjectItem[], append: boolean) => {
  const map = new Map<string, ProjectItem>()
  if (append) projects.value.forEach((p) => map.set(p.id, p))
  incoming.forEach((p) => map.set(p.id, p))
  projects.value = Array.from(map.values())
}

const loadPage = async (append = false) => {
  if (append) {
    if (!hasMore.value || loadingMore.value) return
    loadingMore.value = true
  } else {
    loading.value = true
    page.value = 1
  }
  try {
    const reqPage = append ? page.value + 1 : 1
    const { data } = await http.get('/projects', {
      params: {
        page: reqPage,
        page_size: PAGE_SIZE,
        keyword: keyword.value || undefined,
      },
    })
    const items: ProjectItem[] = (data.items || []).map((p: ProjectItem) => ({
      id: p.id,
      name: p.name,
      created_at: p.created_at,
    }))
    total.value = data.total ?? items.length
    mergeItems(items, append)
    page.value = reqPage
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const ensureSelectedInList = async () => {
  const id = model.value || selectedProjectId.value
  if (!id || projects.value.some((p) => p.id === id)) return
  try {
    const { data } = await http.get(`/projects/${id}`)
    if (data) mergeItems([{ id: data.id, name: data.name, created_at: data.created_at }], true)
  } catch {
    /* 项目可能已删除 */
  }
}

const onSearch = (query: string) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    keyword.value = query.trim()
    loadPage(false)
  }, 300)
}

const onScroll = () => {
  if (!scrollEl || loadingMore.value || !hasMore.value) return
  const { scrollTop, clientHeight, scrollHeight } = scrollEl
  if (scrollTop + clientHeight >= scrollHeight - 12) loadPage(true)
}

const bindScroll = () => {
  scrollEl = document.querySelector('.project-select-dropdown .el-select-dropdown__wrap') as HTMLElement
  scrollEl?.addEventListener('scroll', onScroll, { passive: true })
}

const unbindScroll = () => {
  scrollEl?.removeEventListener('scroll', onScroll)
  scrollEl = null
}

const onVisibleChange = (visible: boolean) => {
  if (visible) {
    if (!projects.value.length) loadPage(false)
    nextTick(bindScroll)
  } else {
    unbindScroll()
  }
}

const onChange = (id: string) => setSelectedProject(id || '')

watch(model, (id) => setSelectedProject(id || ''))

onMounted(async () => {
  if (!model.value && selectedProjectId.value) model.value = selectedProjectId.value
  await loadPage(false)
  await ensureSelectedInList()
})

onBeforeUnmount(() => {
  unbindScroll()
  if (searchTimer) clearTimeout(searchTimer)
})

defineExpose({ projects, reload: () => loadPage(false) })
</script>

<style scoped>
.project-selector { margin-bottom: 16px; }
.hint { color: #909399; font-size: 13px; }
.option-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  width: 100%;
}
.option-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.option-time { color: #909399; font-size: 12px; flex-shrink: 0; }
.select-footer {
  padding: 8px 12px;
  text-align: center;
  color: #909399;
  font-size: 12px;
}
</style>
