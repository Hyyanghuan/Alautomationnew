import { ref, watch } from 'vue'

const STORAGE_KEY = 'aitest_selected_project_id'

/** 各独立页面人工关联的当前项目（本地记忆，非强制） */
export const selectedProjectId = ref<string>(localStorage.getItem(STORAGE_KEY) || '')

watch(selectedProjectId, (id) => {
  if (id) localStorage.setItem(STORAGE_KEY, id)
  else localStorage.removeItem(STORAGE_KEY)
})

export function setSelectedProject(id: string) {
  selectedProjectId.value = id
}
