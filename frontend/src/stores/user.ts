import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')

  function setAuth(t: string, u: string, r: string) {
    token.value = t
    username.value = u
    role.value = r
    localStorage.setItem('token', t)
    localStorage.setItem('username', u)
    localStorage.setItem('role', r)
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.clear()
  }

  const isAdmin = () => ['super_admin', 'admin'].includes(role.value)

  return { token, username, role, setAuth, logout, isAdmin }
})
