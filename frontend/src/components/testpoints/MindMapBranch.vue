<template>
  <div class="mm-branch">
    <div class="mm-row">
      <MindMapNode
        :node="node"
        :active-id="activeId"
        @select="$emit('select', $event)"
        @edit="$emit('edit', $event)"
        @delete="$emit('delete', $event)"
        @add-child="$emit('add-child', $event)"
      />
      <div v-if="node.children?.length" class="mm-connector" />
      <div v-if="node.children?.length" class="mm-children">
        <div v-for="child in node.children" :key="child.id" class="mm-child-line">
          <MindMapBranch
            :node="child"
            :active-id="activeId"
            @select="$emit('select', $event)"
            @edit="$emit('edit', $event)"
            @delete="$emit('delete', $event)"
            @add-child="$emit('add-child', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TreeNode } from '@/utils/testPointTree'
import MindMapNode from './MindMapNode.vue'

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
.mm-branch { display: flex; flex-direction: column; }
.mm-row {
  display: flex;
  align-items: center;
  gap: 0;
}
.mm-connector {
  width: 32px;
  height: 2px;
  background: #c0c4cc;
  flex-shrink: 0;
}
.mm-children {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-left: 8px;
  border-left: 2px solid #dcdfe6;
  margin-left: 4px;
}
.mm-child-line { position: relative; }
.mm-child-line::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 50%;
  width: 10px;
  height: 2px;
  background: #dcdfe6;
}
</style>
