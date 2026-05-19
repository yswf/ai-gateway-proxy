<template>
  <div class="usage-stats animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">用量统计</h1>
        <p class="page-subtitle">查看您的 Token 消耗记录</p>
      </div>
      <el-select v-model="selectedDays" style="width: 120px" @change="fetchAll">
        <el-option label="近 7 天" :value="7" />
        <el-option label="近 30 天" :value="30" />
        <el-option label="近 90 天" :value="90" />
      </el-select>
    </div>

    <!-- Charts -->
    <div class="charts-row">
      <div class="chart-card glass-card">
        <h3 class="chart-title">Token 用量趋势</h3>
        <v-chart :option="trendOption" autoresize style="height: 240px" :loading="loading" />
      </div>
      <div class="chart-card glass-card">
        <h3 class="chart-title">模型分布</h3>
        <v-chart :option="pieOption" autoresize style="height: 240px" :loading="loading" />
      </div>
    </div>

    <!-- Logs Table -->
    <div class="glass-card">
      <div class="logs-header">
        <h3 class="chart-title">请求明细</h3>
        <el-select
          v-model="selectedKey"
          placeholder="筛选 Key"
          clearable
          style="width: 200px"
          @change="fetchLogs"
        >
          <el-option
            v-for="k in keys"
            :key="k.id"
            :label="k.name"
            :value="k.id"
          />
        </el-select>
      </div>

      <el-table :data="logs" v-loading="logsLoading" empty-text="暂无请求记录">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">
            <span class="meta-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="模型" width="180">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.model }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="端点" min-width="180">
          <template #default="{ row }">
            <code class="endpoint-code">{{ row.endpoint }}</code>
          </template>
        </el-table-column>
        <el-table-column label="输入" width="90" align="right">
          <template #default="{ row }">
            <span class="meta-text">{{ row.prompt_tokens.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column label="输出" width="90" align="right">
          <template #default="{ row }">
            <span class="meta-text">{{ row.completion_tokens.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column label="总计" width="90" align="right">
          <template #default="{ row }">
            <span class="total-tokens">{{ row.total_tokens.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column label="延迟" width="90" align="right">
          <template #default="{ row }">
            <span :class="latencyClass(row.latency_ms)">
              {{ row.latency_ms != null ? row.latency_ms + 'ms' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status_code < 300 ? 'success' : 'danger'" size="small">
              {{ row.status_code }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="logsPage"
          :page-size="logsPageSize"
          :total="logsTotal"
          layout="total, prev, pager, next"
          @current-change="fetchLogs"
          background
        />
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
import { statsApi } from '@/api/stats'
import { apiKeysApi } from '@/api/apiKeys'
import type { DailyUsage, ModelUsage, UsageLogItem, APIKey } from '@/types'
import dayjs from 'dayjs'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(true)
const logsLoading = ref(false)
const selectedDays = ref(30)
const selectedKey = ref<string | null>(null)
const daily = ref<DailyUsage[]>([])
const models = ref<ModelUsage[]>([])
const logs = ref<UsageLogItem[]>([])
const keys = ref<APIKey[]>([])
const logsPage = ref(1)
const logsPageSize = 20
const logsTotal = ref(0)

function formatDate(d: string) { return dayjs(d).format('MM-DD HH:mm:ss') }

function latencyClass(ms: number | null) {
  if (ms == null) return 'meta-text'
  if (ms < 500) return 'latency-fast'
  if (ms < 2000) return 'latency-ok'
  return 'latency-slow'
}

const chartColors = ['#9ab856', '#0d759f', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

const trendOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', backgroundColor: '#111827', borderColor: '#1e2d45', textStyle: { color: '#f1f5f9' } },
  grid: { top: 20, right: 20, bottom: 20, left: 50, containLabel: true },
  xAxis: {
    type: 'category',
    data: daily.value.map(d => d.date.slice(5)),
    axisLabel: { color: '#475569', fontSize: 11 },
    axisLine: { lineStyle: { color: '#1e2d45' } },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#475569', fontSize: 11 },
    splitLine: { lineStyle: { color: '#1e2d4520' } },
  },
  series: [{
    type: 'bar',
    data: daily.value.map(d => d.total_tokens),
    itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#9ab856' }, { offset: 1, color: '#7c9b3d' }] }, borderRadius: [4, 4, 0, 0] },
  }],
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
    const [d, m] = await Promise.all([
      statsApi.getDailyUsage(selectedDays.value),
      statsApi.getModelUsage(selectedDays.value),
    ])
    daily.value = d.data
    models.value = m.data
  } finally {
    loading.value = false
  }
}

async function fetchLogs() {
  logsLoading.value = true
  try {
    const res = await statsApi.getLogs({
      skip: (logsPage.value - 1) * logsPageSize,
      limit: logsPageSize,
      key_id: selectedKey.value ?? undefined,
    })
    logs.value = res.data.items
    logsTotal.value = res.data.total
  } finally {
    logsLoading.value = false
  }
}

onMounted(async () => {
  const keysRes = await apiKeysApi.list({ limit: 100 })
  keys.value = keysRes.data.items
  await Promise.all([fetchAll(), fetchLogs()])
})
</script>

<style scoped>
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
@media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
.chart-card { padding: 20px; }
.chart-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 16px; }
.logs-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 20px 0; margin-bottom: 16px; }
.table-footer { padding: 16px 20px; display: flex; justify-content: flex-end; border-top: 1px solid var(--color-border); }
.meta-text { font-size: 13px; color: var(--color-text-secondary); }
.total-tokens { font-size: 13px; font-weight: 600; color: var(--color-primary-light); }
.endpoint-code { font-family: monospace; font-size: 12px; color: var(--color-text-secondary); }
.latency-fast { color: var(--color-success); font-size: 13px; }
.latency-ok { color: var(--color-warning); font-size: 13px; }
.latency-slow { color: var(--color-danger); font-size: 13px; }
</style>
