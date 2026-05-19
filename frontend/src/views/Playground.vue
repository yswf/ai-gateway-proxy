<template>
  <div class="playground-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">API 测试 (Playground)</h1>
        <p class="page-subtitle">使用您的 API Key 进行在线调试</p>
      </div>
    </div>

    <div class="playground-layout">
      <!-- Configuration Panel -->
      <div class="config-panel glass-card">
        <h3 class="panel-title">请求配置</h3>
        <el-form label-position="top">
          <el-form-item label="快速加载配置 (可选)">
            <el-select 
              v-model="selectedKeyId" 
              placeholder="选择已申请的 Key 自动加载允许的模型" 
              @change="onKeyChange"
              style="width: 100%"
              clearable
            >
              <el-option v-for="k in userKeys" :key="k.id" :label="`${k.name} (${k.key_prefix}...`" :value="k.id" />
            </el-select>
            <div class="form-hint" style="font-size: 12px; color: var(--color-text-muted); margin-top: 4px;">用于智能加载模型列表。出于安全原因，您仍需在下方手动输入完整的 Key</div>
          </el-form-item>

          <el-form-item label="API Key">
            <el-input 
              v-model="apiKey" 
              type="password" 
              show-password 
              placeholder="请输入您保存的完整 API Key (sk-...)" 
            />
          </el-form-item>

          <el-form-item label="Base URL (Proxy Endpoint)">
            <el-input v-model="baseUrl" readonly>
              <template #append>
                <el-button :icon="CopyDocument" @click="copyBaseUrl" />
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="模型名称 (Model)">
            <el-select 
              v-if="availableModels.length > 0 || fetchingModels"
              v-model="modelName" 
              placeholder="请选择模型 (支持手动输入)" 
              style="width: 100%"
              filterable
              allow-create
              :loading="fetchingModels"
            >
              <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
            </el-select>
            <el-input v-else v-model="modelName" placeholder="例如: gpt-3.5-turbo (下拉列表为空时可直接输入)" />
          </el-form-item>

          <el-form-item label="用户提示词 (Prompt)">
            <el-input 
              v-model="prompt" 
              type="textarea" 
              :rows="4" 
              placeholder="请输入测试对话内容..." 
            />
          </el-form-item>

          <el-button 
            type="primary" 
            style="width: 100%; margin-top: 10px;" 
            @click="sendRequest"
            :loading="loading"
          >
            发送请求
          </el-button>
        </el-form>
      </div>

      <!-- Result Panel -->
      <div class="result-panel">
        <div class="glass-card mb-4 code-box">
          <div class="code-box-header">
            <span>cURL 示例</span>
            <el-button link type="primary" size="small" @click="copyCurl">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
          <pre class="code-content"><code>{{ curlCommand }}</code></pre>
        </div>

        <div class="glass-card code-box result-box" v-loading="loading">
          <div class="code-box-header">
            <span>响应结果</span>
            <el-tag v-if="status" :type="status >= 400 ? 'danger' : 'success'" size="small">
              HTTP {{ status }}
            </el-tag>
          </div>
          <pre class="code-content"><code>{{ responseData || '暂无数据' }}</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { apiKeysApi } from '@/api/apiKeys'
import { applicationsApi } from '@/api/applications'
import type { APIKey } from '@/types'

const apiKey = ref('')
const selectedKeyId = ref('')
const userKeys = ref<APIKey[]>([])
const availableModels = ref<string[]>([])
const fetchingModels = ref(false)

const baseUrl = ref(window.location.origin + '/api/v1/proxy/chat/completions')
const modelName = ref('gpt-3.5-turbo')
const prompt = ref('你好，请做一下自我介绍。')

const loading = ref(false)
const responseData = ref('')
const status = ref<number | null>(null)

const curlCommand = computed(() => {
  return `curl -X POST "${baseUrl.value}" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKey.value || 'YOUR_API_KEY'}" \\
  -d '{
    "model": "${modelName.value}",
    "messages": [
      {
        "role": "user",
        "content": "${prompt.value.replace(/\n/g, '\\n').replace(/"/g, '\\"')}"
      }
    ]
  }'`
})

async function copyBaseUrl() {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(baseUrl.value)
    } else {
      const textArea = document.createElement("textarea")
      textArea.value = baseUrl.value
      textArea.style.position = "fixed"
      textArea.style.left = "-999999px"
      textArea.style.top = "-999999px"
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      textArea.remove()
      if (!successful) throw new Error('Fallback copy failed')
    }
    ElMessage.success('Base URL 已复制')
  } catch (e) {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

async function copyCurl() {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(curlCommand.value)
    } else {
      const textArea = document.createElement("textarea")
      textArea.value = curlCommand.value
      textArea.style.position = "fixed"
      textArea.style.left = "-999999px"
      textArea.style.top = "-999999px"
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      textArea.remove()
      if (!successful) throw new Error('Fallback copy failed')
    }
    ElMessage.success('cURL 命令已复制')
  } catch (e) {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

async function sendRequest() {
  if (!apiKey.value) {
    ElMessage.warning('请输入 API Key')
    return
  }
  if (!modelName.value) {
    ElMessage.warning('请输入模型名称')
    return
  }

  loading.value = true
  responseData.value = ''
  status.value = null

  try {
    const res = await fetch(baseUrl.value, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey.value}`
      },
      body: JSON.stringify({
        model: modelName.value,
        messages: [{ role: 'user', content: prompt.value }]
      })
    })
    
    status.value = res.status
    const text = await res.text()
    
    try {
      // 尝试格式化 JSON
      const json = JSON.parse(text)
      responseData.value = JSON.stringify(json, null, 2)
    } catch {
      responseData.value = text
    }
  } catch (e: any) {
    responseData.value = '请求异常: ' + e.message
  } finally {
    loading.value = false
  }
}

async function fetchKeys() {
  try {
    const res = await apiKeysApi.list({ limit: 100 })
    userKeys.value = res.data.items
  } catch (e) {
    // ignore
  }
}

async function onKeyChange(keyId: string) {
  availableModels.value = []
  if (!keyId) return
  
  const key = userKeys.value.find(k => k.id === keyId)
  if (!key) return

  if (key.allowed_models && key.allowed_models.length > 0) {
    availableModels.value = key.allowed_models
    modelName.value = key.allowed_models[0]
    return
  }

  if (key.provider_id) {
    fetchingModels.value = true
    try {
      const res = await applicationsApi.listModelsByProvider(key.provider_id)
      availableModels.value = res.data.items.map(m => m.name)
      if (availableModels.value.length > 0 && !availableModels.value.includes(modelName.value)) {
        modelName.value = availableModels.value[0]
      }
    } catch(e) {
      // ignore
    } finally {
      fetchingModels.value = false
    }
  }
}

onMounted(() => {
  fetchKeys()
})
</script>

<style scoped>
.playground-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 900px) {
  .playground-layout {
    grid-template-columns: 1fr;
  }
}

.panel-title {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
}

.mb-4 {
  margin-bottom: 16px;
}

.code-box {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.result-box {
  min-height: 300px;
}

.code-box-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--color-bg-subtle);
  border-bottom: 1px solid var(--color-border);
  font-weight: 500;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.code-content {
  margin: 0;
  padding: 16px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-primary-light);
  background: rgba(99, 102, 241, 0.03);
  overflow-x: auto;
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
