<template>
  <div class="analytics animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">全局分析</h1>
        <p class="page-subtitle">平台整体用量统计与分析</p>
      </div>
      <el-select v-model="days" style="width: 120px" @change="fetchAll">
        <el-option label="近 7 天" :value="7" />
        <el-option label="近 30 天" :value="30" />
        <el-option label="近 90 天" :value="90" />
      </el-select>
    </div>

    <!-- Summary Cards -->
    <div class="stats-grid">
      <div v-for="card in summaryCards" :key="card.label" class="stat-card">
        <div class="stat-icon" :style="{ background: card.gradient }">
          <el-icon size="22"><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-row">
      <div class="chart-card glass-card">
        <h3 class="chart-title">全平台 Token 趋势</h3>
        <v-chart :option="trendOption" autoresize style="height: 260px" :loading="loading" />
      </div>
      <div class="chart-card glass-card">
        <h3 class="chart-title">模型使用分布</h3>
        <v-chart :option="pieOption" autoresize style="height: 260px" :loading="loading" />
      </div>
    </div>

    <!-- Tables -->
    <div class="charts-row">
      <!-- Top Keys Table -->
      <div class="glass-card">
        <div class="table-header-row">
          <h3 class="chart-title">Top Keys 排行</h3>
        </div>
        <el-table :data="topKeys" v-loading="loading" empty-text="暂无数据">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column label="Key" min-width="140">
            <template #default="{ row }">
              <div>
                <div class="key-name">{{ row.key_name }}</div>
                <code class="key-prefix-sm">{{ row.key_prefix }}••••••</code>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="总 Token 用量" min-width="140">
            <template #default="{ row }">
              <div class="progress-cell">
                <span class="token-value">{{ formatNum(row.total_tokens) }}</span>
                <el-progress
                  :percentage="maxTokens ? Math.round((row.total_tokens / maxTokens) * 100) : 0"
                  :show-text="false"
                  :stroke-width="6"
                  style="flex: 1"
                />
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Top Users Table -->
      <div class="glass-card">
        <div class="table-header-row">
          <h3 class="chart-title">用户用量排行</h3>
        </div>
        <el-table :data="topUsers" v-loading="loading" empty-text="暂无数据">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column label="用户" min-width="140">
            <template #default="{ row }">
              <div>
                <div class="key-name">{{ row.display_name || row.email.split('@')[0] }}</div>
                <div class="meta-text" style="font-size: 12px">{{ row.email }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="总 Token 用量" min-width="140">
            <template #default="{ row }">
              <div class="progress-cell">
                <span class="token-value">{{ formatNum(row.total_tokens) }}</span>
                <el-progress
                  :percentage="maxUserTokens ? Math.round((row.total_tokens / maxUserTokens) * 100) : 0"
                  :show-text="false"
                  :stroke-width="6"
                  style="flex: 1"
                  color="#10b981"
                />
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { UserFilled, Key, Coin, TrendCharts } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import type { AdminStatsSummary, DailyUsage, ModelUsage, KeyUsageSummary, UserTokenRankingItem } from '@/types'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(true)
const days = ref(30)
const summary = ref<AdminStatsSummary | null>(null)
const daily = ref<DailyUsage[]>([])
const models = ref<ModelUsage[]>([])
const topKeys = ref<KeyUsageSummary[]>([])
const topUsers = ref<UserTokenRankingItem[]>([])

const chartColors = ['#9ab856', '#0d759f', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function formatNum(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return n.toString()
}

const maxTokens = computed(() => topKeys.value[0]?.total_tokens ?? 0)
const maxUserTokens = computed(() => topUsers.value[0]?.total_tokens ?? 0)

const summaryCards = computed(() => [
  { label: '注册用户', value: summary.value?.total_users ?? 0, icon: UserFilled, gradient: 'linear-gradient(135deg, #9ab856, #7c9b3d)' },
  { label: '活跃 Keys', value: summary.value?.active_keys ?? 0, icon: Key, gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  { label: '今日 Tokens', value: formatNum(summary.value?.today_tokens ?? 0), icon: Coin, gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' },
  { label: '累计请求', value: formatNum(summary.value?.total_requests_all_time ?? 0), icon: TrendCharts, gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)' },
])

const trendOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', backgroundColor: '#111827', borderColor: '#1e2d45', textStyle: { color: '#f1f5f9' } },
  grid: { top: 20, right: 20, bottom: 20, left: 50, containLabel: true },
  xAxis: { type: 'category', data: daily.value.map(d => d.date.slice(5)), axisLabel: { color: '#475569', fontSize: 11 }, axisLine: { lineStyle: { color: '#1e2d45' } }, splitLine: { show: false } },
  yAxis: { type: 'value', axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#1e2d4520' } } },
  series: [
    {
      name: '总 Tokens', type: 'line', data: daily.value.map(d => d.total_tokens), smooth: true,
      lineStyle: { color: '#9ab856', width: 2 }, itemStyle: { color: '#9ab856' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(154, 184, 86, 0.3)' }, { offset: 1, color: 'rgba(154, 184, 86, 0)' }] } },
    },
  ],
}))

const pieOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', backgroundColor: '#111827', borderColor: '#1e2d45', textStyle: { color: '#f1f5f9' }, formatter: '{b}: {c} ({d}%)' },
  legend: { orient: 'vertical', right: '5%', top: 'center', textStyle: { color: '#94a3b8', fontSize: 12 } },
  series: [{
    type: 'pie', radius: ['40%', '68%'], center: ['38%', '50%'],
    data: models.value.map((m, i) => ({
      name: m.provider_name ? `${m.provider_name} | ${m.model}` : m.model,
      value: m.total_tokens,
      itemStyle: { color: chartColors[i % chartColors.length] }
    })),
    label: { show: false },
  }],
}))

async function fetchAll() {
  loading.value = true
  try {
    const [s, d, m, k, u] = await Promise.all([
      adminApi.getSummary(),
      adminApi.getDailyUsage(days.value),
      adminApi.getModelUsage(days.value),
      adminApi.getTopKeys(days.value),
      adminApi.getUserTokenRanking(50),
    ])
    summary.value = s.data
    daily.value = d.data
    models.value = m.data
    topKeys.value = k.data
    topUsers.value = u.data.items
  } finally { loading.value = false }
}

onMounted(fetchAll)
</script>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 20px; display: flex; align-items: center; gap: 16px; transition: var(--transition); }
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-hover); border-color: var(--color-border-light); }
.stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0; }
.stat-value { font-size: 24px; font-weight: 700; color: var(--color-text-primary); }
.stat-label { font-size: 13px; color: var(--color-text-secondary); margin-top: 2px; }
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
@media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
.chart-card { padding: 24px; }
.chart-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 16px; }
.table-header-row { padding: 20px 20px 0; }
.key-name { font-size: 14px; font-weight: 500; color: var(--color-text-primary); }
.key-prefix-sm { font-family: monospace; font-size: 12px; color: var(--color-text-muted); }
.progress-cell { display: flex; align-items: center; gap: 12px; }
.token-value { font-size: 14px; font-weight: 600; color: var(--color-primary-light); min-width: 60px; }
.meta-text { font-size: 13px; color: var(--color-text-secondary); }
</style>
