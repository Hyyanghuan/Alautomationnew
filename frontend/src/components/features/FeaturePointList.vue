<template>
  <div v-if="!points.length" class="fp-empty">该功能下暂无子测试点</div>
  <ul v-else class="fp-list">
    <li v-for="pt in points" :key="pt.id || pt.name" class="fp-item">
      <div class="fp-row">
        <span class="fp-name">{{ pt.name }}</span>
        <span class="fp-actions">
          <el-button link type="primary" size="small" @click="$emit('edit', pt)">编辑</el-button>
          <el-button
            v-if="pt.id"
            link
            type="danger"
            size="small"
            @click="$emit('delete', pt)"
          >
            删除
          </el-button>
        </span>
      </div>
      <FeaturePointList
        v-if="pt.children?.length"
        :points="pt.children"
        @edit="$emit('edit', $event)"
        @delete="$emit('delete', $event)"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
export type FeaturePoint = {
  id?: string
  name: string
  children?: FeaturePoint[]
}

defineProps<{
  points: FeaturePoint[]
}>()

defineEmits<{
  edit: [pt: FeaturePoint]
  delete: [pt: FeaturePoint]
}>()
</script>

<style scoped>
.fp-list {
  list-style: none;
  margin: 0;
  padding: 0 0 0 16px;
}
.fp-item { margin: 6px 0; }
.fp-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f5f7fa;
}
.fp-row:hover { background: #ecf5ff; }
.fp-name { flex: 1; font-size: 13px; }
.fp-actions { flex-shrink: 0; }
.fp-empty { color: #909399; font-size: 13px; padding: 8px 0; }
</style>
