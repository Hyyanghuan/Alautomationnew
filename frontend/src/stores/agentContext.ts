const STORAGE_KEY = 'aitest_agent_selection'

type SelectionMap = Record<string, string | string[]>

function readAll(): SelectionMap {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeAll(data: SelectionMap) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

export function getStoredAgent(key: string): string {
  const v = readAll()[key]
  return typeof v === 'string' ? v : ''
}

export function setStoredAgent(key: string, agentId: string) {
  const data = readAll()
  data[key] = agentId
  writeAll(data)
}

export function getStoredKbIds(): string[] {
  const v = readAll().kb_ids
  return Array.isArray(v) ? v : []
}

export function setStoredKbIds(ids: string[]) {
  const data = readAll()
  data.kb_ids = ids
  writeAll(data)
}

export const AGENT_KEYS = {
  designTestPoints: 'design_test_points',
  designVerify: 'design_verify',
} as const
