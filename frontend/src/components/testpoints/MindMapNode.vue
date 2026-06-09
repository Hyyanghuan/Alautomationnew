<template>
  <div
    class="mm-node"
    :class="{ 'is-active': node.id === activeId }"
    @click.stop="$emit('select', node)"
  >
    <span class="mm-name" :title="node.name">{{ node.name }}</span>
    <div class="mm-actions" @click.stop>
      <el-button link type="primary" size="small" @click="$emit('edit', node)">编辑</el-button>
      <el-button link type="primary" size="small" @click="$emit('add-child', node)">子节点</el-button>
      <el-button link type="danger" size="small" @click="$emit('delete', node)">删除</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TreeNode } from '@/utils/testPointTree'

defineProps<{
  node: TreeNode
  activeId?: string
}>()

defineEmits<{
  select: [node: TreeNode]
  edit: [node: TreeNode]
  delete: [node: TreeNode]
  'add-child': [node: TreeNode]
}>()
</script>

<style scoped>
.mm-node {
  min-width: 120px;
  max-width: 220px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #b3d8ff;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.1);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.mm-node:hover,
.mm-node.is-active {
  border-color: #409eff;
  background: #ecf5ff;
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.2);
}
.mm-name {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  word-break: break-all;
  margin-bottom: 4px;
}
.mm-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}
.mm-actions :deep(.el-button) {
  padding: 0 4px;
  font-size: 12px;
}
</style>
