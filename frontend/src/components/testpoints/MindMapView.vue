<template>
  <div class="mindmap-wrap">
    <div v-if="!nodes.length" class="mindmap-empty">暂无测试点，请生成或新增根节点</div>
    <div v-else class="mindmap-scroll">
      <div class="mindmap-root-list">
        <MindMapBranch
          v-for="node in nodes"
          :key="node.id"
          :node="node"
          :active-id="activeId"
          @select="onSelect"
          @edit="onEdit"
          @delete="onDelete"
          @add-child="onAddChild"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TreeNode } from '@/utils/testPointTree'
import MindMapBranch from './MindMapBranch.vue'

defineProps<{
  nodes: TreeNode[]
  activeId?: string
}>()

const emit = defineEmits<{
  select: [node: TreeNode]
  edit: [node: TreeNode]
  delete: [node: TreeNode]
  'add-child': [node: TreeNode]
}>()

const onSelect = (node: TreeNode) => emit('select', node)
const onEdit = (node: TreeNode) => emit('edit', node)
const onDelete = (node: TreeNode) => emit('delete', node)
const onAddChild = (node: TreeNode) => emit('add-child', node)
</script>

<style scoped>
.mindmap-wrap {
  min-height: 200px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafbfc;
  padding: 16px;
}
.mindmap-scroll {
  overflow: auto;
  max-height: 560px;
}
.mindmap-root-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.mindmap-empty {
  color: #909399;
  text-align: center;
  padding: 40px 0;
}
</style>
