<template>
  <div class="dashboard animate-fade-in">
    <!-- Stat Cards -->
    <div class="stats-grid" style="margin-bottom: 24px;">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="stat-top">
          <div class="stat-icon" :style="{ background: card.gradient }">
            <el-icon :size="20"><component :is="card.icon" /></el-icon>
          </div>
          <span class="stat-label">{{ card.label }}</span>
        </div>
        <div class="stat-value">{{ card.value }}</div>
        <div class="stat-sub">{{ card.sub }}</div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-grid" style="margin-bottom: 24px;">
      <div class="card" style="padding: 20px;">
        <div class="chart-header">
          <div>
            <h3 class="chart-title">Token 用量趋势</h3>
            <p class="chart-subtitle">近 {{ trendDays }} 天</p>
          </div>
          <el-select v-model="trendDays" size="small" style="width: 90px" @change="fetchDailyUsage">
            <el-option label="7 天" :value="7" />
            <el-option label="30 天" :value="30" />
            <el-option label="90 天" :value="90" />
          </el-select>
        </div>
        <v-chart :option="trendOption" autoresize style="height: 240px" :loading="chartsLoading" />
      </div>

      <div class="card" style="padding: 20px;">
        <div class="chart-header">
          <div>
            <h3 class="chart-title">模型使用分布</h3>
            <p class="chart-subtitle">近 30 天</p>
          </div>
        </div>
        <v-chart :option="modelOption" autoresize style="height: 240px" :loading="chartsLoading" />
      </div>
    </div>

    <!-- Quick links -->
    <div>
      <h3 class="section-title">快速操作</h3>
      <div class="quick-grid">
        <router-link to="/keys" class="quick-card card">
          <div class="quick-icon" style="background: linear-gradient(135deg, #6366f1, #8b5cf6)">
            <el-icon :size="22"><Key /></el-icon>
          </div>
          <div class="quick-body">
            <div class="quick-title">管理 API Keys</div>
            <div class="quick-desc">创建和管理您的访问密钥</div>
          </div>
          <el-icon class="quick-arrow"><ArrowRight /></el-icon>
        </router-link>
        <router-link to="/usage" class="quick-card card">
          <div class="quick-icon" style="background: linear-gradient(135deg, #10b981, #059669)">
            <el-icon :size="22"><DataLine /></el-icon>
          </div>
          <div class="quick-body">
            <div class="quick-title">查看用量详情</div>
            <div class="quick-desc">查看每次请求的 Token 消耗</div>
          </div>
          <el-icon class="quick-arrow"><ArrowRight /></el-icon>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { Coin, TrendCharts, Key, DataLine, ArrowRight } from '@element-plus/icons-vue'
import { statsApi } from '@/api/stats'
import type { UserStatsSummary, DailyUsage, ModelUsage } from '@/types'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const summary = ref<UserStatsSummary | null>(null)
const daily = ref<DailyUsage[]>([])
const models = ref<ModelUsage[]>([])
const chartsLoading = ref(true)
const trendDays = ref(30)

const PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899']

function fmt(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return n.toString()
}

const statCards = computed(() => [
  { label: '今日 Tokens', value: fmt(summary.value?.today_tokens ?? 0), sub: `累计 ${fmt(summary.value?.total_tokens_used ?? 0)}`, icon: Coin, gradient: 'linear-gradient(135deg,#6366f1,#8b5cf6)' },
  { label: '今日请求', value: fmt(summary.value?.today_requests ?? 0), sub: `累计 ${fmt(summary.value?.total_requests ?? 0)} 次`, icon: TrendCharts, gradient: 'linear-gradient(135deg,#10b981,#059669)' },
  { label: '活跃 Keys', value: `${summary.value?.active_keys ?? 0}`, sub: `共 ${summary.value?.total_keys ?? 0} 个`, icon: Key, gradient: 'linear-gradient(135deg,#f59e0b,#d97706)' },
  { label: '累计 Tokens', value: fmt(summary.value?.total_tokens_used ?? 0), sub: `${fmt(summary.value?.total_requests ?? 0)} 次请求`, icon: DataLine, gradient: 'linear-gradient(135deg,#3b82f6,#1d4ed8)' },
])

const trendOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', confine: true },
  legend: { data: ['输入 Tokens', '输出 Tokens'], textStyle: { color: '#475569' }, top: 0 },
  grid: { top: 36, right: 12, bottom: 16, left: 50, containLabel: true },
  xAxis: { type: 'category', data: daily.value.map(d => d.date.slice(5)), axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { lineStyle: { color: '#e2e8f0' } }, splitLine: { show: false } },
  yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 11, formatter: fmt }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
  series: [
    { name: '输入 Tokens', type: 'line', data: daily.value.map(d => d.prompt_tokens), smooth: true, lineStyle: { color: '#6366f1', width: 2 }, itemStyle: { color: '#6366f1' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(99,102,241,0.15)' }, { offset: 1, color: 'rgba(99,102,241,0)' }] } } },
    { name: '输出 Tokens', type: 'line', data: daily.value.map(d => d.completion_tokens), smooth: true, lineStyle: { color: '#10b981', width: 2 }, itemStyle: { color: '#10b981' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(16,185,129,0.12)' }, { offset: 1, color: 'rgba(16,185,129,0)' }] } } },
  ],
}))

const modelOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', formatter: '{b}: {c} tokens ({d}%)' },
  legend: { orient: 'vertical', right: '2%', top: 'center', textStyle: { color: '#475569', fontSize: 12 } },
  series: [{
    type: 'pie', radius: ['42%', '68%'], center: ['36%', '50%'],
    data: models.value.map((m, i) => ({ name: m.model, value: m.total_tokens, itemStyle: { color: PALETTE[i % PALETTE.length] } })),
    label: { show: false },
    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.15)' } },
  }],
}))

async function fetchDailyUsage() {
  const res = await statsApi.getDailyUsage(trendDays.value)
  daily.value = res.data
}

onMounted(async () => {
  chartsLoading.value = true
  try {
    const [s, d, m] = await Promise.all([
      statsApi.getSummary(),
      statsApi.getDailyUsage(trendDays.value),
      statsApi.getModelUsage(30),
    ])
    summary.value = s.data
    daily.value = d.data
    models.value = m.data
  } finally {
    chartsLoading.value = false
  }
})
</script>

<style scoped>
.chart-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.chart-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); }
.chart-subtitle { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; }
.section-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 12px; }

.stat-top { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.stat-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0; }
.stat-label { font-size: 13px; font-weight: 500; color: var(--color-text-secondary); }
.stat-value { font-size: 28px; font-weight: 700; color: var(--color-text-primary); line-height: 1.2; }
.stat-sub { font-size: 12px; color: var(--color-text-muted); margin-top: 6px; }

.quick-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.quick-card { display: flex; align-items: center; gap: 14px; padding: 18px; text-decoration: none; }
.quick-card:hover { border-color: var(--color-primary); }
.quick-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0; }
.quick-body { flex: 1; min-width: 0; }
.quick-title { font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
.quick-desc { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; }
.quick-arrow { color: var(--color-text-muted); flex-shrink: 0; }
</style>
