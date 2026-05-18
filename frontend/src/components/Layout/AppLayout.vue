<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': collapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="logo-icon">
          <el-icon size="20"><Connection /></el-icon>
        </div>
        <transition name="label-fade">
          <span v-if="!collapsed" class="logo-text gradient-text">AI Gateway</span>
        </transition>
      </div>

      <!-- Nav -->
      <nav class="sidebar-nav">
        <div class="nav-group">
          <span v-if="!collapsed" class="nav-group-label">主菜单</span>
          <router-link
            v-for="item in mainMenuItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
            :title="collapsed ? item.label : ''"
          >
            <el-icon :size="18"><component :is="item.icon" /></el-icon>
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </router-link>
        </div>

        <div v-if="auth.isAdmin" class="nav-group">
          <span v-if="!collapsed" class="nav-group-label">管理员</span>
          <router-link
            v-for="item in adminMenuItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
            :title="collapsed ? item.label : ''"
          >
            <el-icon :size="18"><component :is="item.icon" /></el-icon>
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </router-link>
        </div>
      </nav>

      <!-- Collapse button -->
      <div class="sidebar-footer">
        <button class="nav-item collapse-btn" @click="collapsed = !collapsed">
          <el-icon :size="18"><DArrowLeft v-if="!collapsed" /><DArrowRight v-else /></el-icon>
          <span v-if="!collapsed" class="nav-label">收起</span>
        </button>
      </div>
    </aside>

    <!-- Mobile overlay -->
    <div v-if="mobileOpen" class="sidebar-overlay" @click="mobileOpen = false" />

    <!-- Main -->
    <div class="main-wrapper">
      <!-- Header -->
      <header class="app-header">
        <div class="header-left">
          <!-- Mobile hamburger -->
          <button class="mobile-menu-btn" @click="mobileOpen = !mobileOpen">
            <el-icon :size="22"><Fold /></el-icon>
          </button>
          <h2 class="header-title">{{ currentTitle }}</h2>
        </div>

        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-btn">
              <div class="user-avatar">{{ userInitial }}</div>
              <div class="user-info-text">
                <span class="user-name">{{ displayName }}</span>
                <el-tag size="small" :type="roleTagType" effect="plain">{{ roleLabel }}</el-tag>
              </div>
              <el-icon size="14" color="#94a3b8"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人资料
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Page content -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Connection, DataLine, Key, TrendCharts, UserFilled,
  Setting, DataAnalysis, User, SwitchButton, Fold,
  DArrowLeft, DArrowRight, ArrowDown, List, DocumentAdd, DocumentChecked, ChatDotSquare
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const mobileOpen = ref(false)

const mainMenuItems = [
  { path: '/dashboard', label: '仪表盘', icon: DataLine },
  { path: '/keys', label: 'API Keys', icon: Key },
  { path: '/usage', label: '用量统计', icon: TrendCharts },
  { path: '/applications', label: '我的申请', icon: DocumentAdd },
  { path: '/playground', label: 'API 测试', icon: ChatDotSquare },
]

const adminMenuItems = [
  { path: '/admin/analytics', label: '全局分析', icon: DataAnalysis },
  { path: '/admin/users', label: '用户管理', icon: UserFilled },
  { path: '/admin/providers', label: '数据源管理', icon: Connection },
  { path: '/admin/models', label: '模型管理', icon: List },
  { path: '/admin/keys', label: '密钥管理', icon: Setting },
  { path: '/admin/applications', label: '审批管理', icon: DocumentChecked },
]

function isActive(path: string) {
  return route.path.startsWith(path)
}

const currentTitle = computed(() => (route.meta.title as string) || 'AI Gateway')

const displayName = computed(() => {
  const u = auth.user
  return u?.display_name || u?.email?.split('@')[0] || '用户'
})

const userInitial = computed(() => displayName.value.charAt(0).toUpperCase())

const roleLabel = computed(() => {
  const map: Record<string, string> = { superadmin: '超级管理员', admin: '管理员', user: '用户' }
  return map[auth.user?.role ?? 'user'] || '用户'
})

const roleTagType = computed(() => {
  const map: Record<string, string> = { superadmin: 'danger', admin: 'warning', user: 'info' }
  return map[auth.user?.role ?? 'user'] || 'info'
})

async function handleCommand(command: string) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
      confirmButtonText: '确定退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
    auth.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
/* ── Layout shell ──────────────────────────────────────────── */
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg);
}

/* ── Sidebar ───────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  background: #fff;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 200;
  transition: width 0.25s ease;
  overflow: hidden;
}

.app-layout.sidebar-collapsed .sidebar {
  width: var(--sidebar-collapsed-width);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  height: var(--header-height);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--gradient-primary);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: -0.01em;
}

/* ── Navigation ────────────────────────────────────────────── */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-group {
  margin-bottom: 8px;
}

.nav-group-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 8px 10px 4px;
  white-space: nowrap;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: var(--transition);
  cursor: pointer;
  border: none;
  background: none;
  width: 100%;
  white-space: nowrap;
  font-family: var(--font-sans);
}

.nav-item:hover {
  background: var(--color-bg-subtle);
  color: var(--color-text-primary);
}

.nav-item.active {
  background: var(--color-primary-bg);
  color: var(--color-primary-dark);
  font-weight: 600;
}

.nav-item.active .el-icon {
  color: var(--color-primary);
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Sidebar Footer ────────────────────────────────────────── */
.sidebar-footer {
  padding: 8px;
  border-top: 1px solid var(--color-border);
}

.collapse-btn {
  font-family: var(--font-sans);
}

/* ── Mobile sidebar overlay ────────────────────────────────── */
.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 190;
}

/* ── Main wrapper ──────────────────────────────────────────── */
.main-wrapper {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left 0.25s ease;
  min-width: 0;
}

.app-layout.sidebar-collapsed .main-wrapper {
  margin-left: var(--sidebar-collapsed-width);
}

/* ── Header ────────────────────────────────────────────────── */
.app-header {
  height: var(--header-height);
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-sm);
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.mobile-menu-btn:hover {
  background: var(--color-bg-subtle);
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  transition: var(--transition);
}

.user-btn:hover {
  background: var(--color-bg-subtle);
}

.user-avatar {
  width: 34px;
  height: 34px;
  background: var(--gradient-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.user-info-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Main Content ──────────────────────────────────────────── */
.main-content {
  flex: 1;
  padding: 24px;
}

/* ── Transitions ───────────────────────────────────────────── */
.label-fade-enter-active,
.label-fade-leave-active { transition: opacity 0.15s ease; }
.label-fade-enter-from,
.label-fade-leave-to { opacity: 0; }

.page-enter-active,
.page-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; transform: translateY(-6px); }

/* ── Responsive ────────────────────────────────────────────── */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    width: var(--sidebar-width) !important;
    transition: transform 0.25s ease;
  }

  .sidebar.mobile-open,
  .app-layout.mobile-sidebar-open .sidebar {
    transform: translateX(0);
  }

  .sidebar-overlay { display: block; }
  .main-wrapper { margin-left: 0 !important; }
  .mobile-menu-btn { display: flex; }
  .user-info-text { display: none; }
  .main-content { padding: 16px; }
  .app-header { padding: 0 16px; }
}

@media (max-width: 480px) {
  .header-title { font-size: 15px; }
}
</style>
