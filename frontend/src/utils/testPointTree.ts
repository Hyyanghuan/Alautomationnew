export type ElementLocator = {
  strategy: string
  value: string
  description?: string
}

export type TreeNode = {
  id?: string
  name: string
  children?: TreeNode[]
  feature_id?: string
  parent_id?: string
  sort_order?: number
  test_type?: string
  locator?: ElementLocator
}

export function newNodeId(): string {
  return crypto.randomUUID()
}

export function ensureNodeIds(nodes: TreeNode[]): TreeNode[] {
  return nodes.map((n) => ({
    ...n,
    id: n.id || newNodeId(),
    children: n.children?.length ? ensureNodeIds(n.children) : [],
  }))
}

export function findNode(nodes: TreeNode[], id: string): TreeNode | null {
  for (const n of nodes) {
    if (n.id === id) return n
    if (n.children?.length) {
      const found = findNode(n.children, id)
      if (found) return found
    }
  }
  return null
}

export function removeNode(nodes: TreeNode[], id: string): TreeNode[] {
  return nodes
    .filter((n) => n.id !== id)
    .map((n) => ({
      ...n,
      children: n.children?.length ? removeNode(n.children, id) : [],
    }))
}

export function updateNodeName(nodes: TreeNode[], id: string, name: string): TreeNode[] {
  return nodes.map((n) => {
    if (n.id === id) return { ...n, name }
    if (n.children?.length) {
      return { ...n, children: updateNodeName(n.children, id, name) }
    }
    return n
  })
}

export function updateNode(
  nodes: TreeNode[],
  id: string,
  patch: Partial<Pick<TreeNode, 'name' | 'test_type' | 'locator'>>,
): TreeNode[] {
  return nodes.map((n) => {
    if (n.id === id) return { ...n, ...patch }
    if (n.children?.length) {
      return { ...n, children: updateNode(n.children, id, patch) }
    }
    return n
  })
}

export function addChildNode(nodes: TreeNode[], parentId: string | null, name: string): TreeNode[] {
  const child: TreeNode = { id: newNodeId(), name, children: [] }
  if (!parentId) return [...nodes, child]
  return nodes.map((n) => {
    if (n.id === parentId) {
      return { ...n, children: [...(n.children || []), child] }
    }
    if (n.children?.length) {
      return { ...n, children: addChildNode(n.children, parentId, name) }
    }
    return n
  })
}

export function cloneTree(nodes: TreeNode[]): TreeNode[] {
  return JSON.parse(JSON.stringify(nodes))
}
