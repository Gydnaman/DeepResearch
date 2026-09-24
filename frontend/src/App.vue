<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useResearchStore } from '@/stores/research'

const research = useResearchStore()
const router = useRouter()
const mobileHistoryOpen = ref(false)
function startNew() {
  research.resetCurrent()
  mobileHistoryOpen.value = false
  void router.push({ name: 'home' })
  document.getElementById('composer')?.scrollIntoView({ behavior: 'smooth' })
}
function selectRun(id: string) {
  mobileHistoryOpen.value = false
  void router.push({ name: 'run', params: { id } })
}
function toggleHistory() {
  mobileHistoryOpen.value = !mobileHistoryOpen.value
}
onMounted(() => {
  void research.loadProviders()
  void research.loadHistory()
})
onUnmounted(() => research.stopStream())
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" aria-label="主导航">
      <a class="brand" href="#main" aria-label="DeepResearch 工作台">
        <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 19V5h3l5 7 5-7h3v14h-3V10l-5 7-5-7v9z" /></svg></span>
        <span><strong>DeepResearch</strong><small>研究工作台</small></span>
      </a>
      <div class="workspace-label">工作空间</div>
      <nav class="primary-nav">
        <button class="nav-item active" type="button" @click="startNew">
          <span class="nav-glyph" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="M10 4v12M4 10h12" /></svg></span><span>新建研究</span>
        </button>
        <button class="nav-item history-nav" type="button" :aria-expanded="mobileHistoryOpen" aria-controls="history" @click="toggleHistory"><span class="nav-glyph" aria-hidden="true"><svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="7" /><path d="M10 6v4l2.5 1.5" /></svg></span><span>研究历史</span></button>
        <a class="nav-item" href="#providers"><span class="nav-glyph" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="M7 3v4M13 3v4M5 7h10v3a5 5 0 0 1-10 0V7ZM10 15v2" /></svg></span><span>数据源状态</span></a>
      </nav>
      <section id="history" class="sidebar-history" :class="{ 'mobile-open': mobileHistoryOpen }" aria-labelledby="history-title">
        <div class="sidebar-heading"><h2 id="history-title">最近研究</h2><button class="icon-button" type="button" aria-label="刷新历史" @click="research.loadHistory()"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M16 8a6.5 6.5 0 0 0-11.3-2L3 8M3 4v4h4M4 12a6.5 6.5 0 0 0 11.3 2L17 12m0 4v-4h-4" /></svg></button></div>
        <p v-if="!research.history.items.length" class="sidebar-empty">完成的研究会显示在这里。</p>
        <button v-for="run in research.history.items" :key="run.run_id" class="history-item" :class="{ selected: research.currentRun?.run_id === run.run_id }" type="button" @click="selectRun(run.run_id)">
          <span class="history-dot" :class="`status-${run.status}`" aria-hidden="true"></span>
          <span class="history-copy"><strong>{{ run.topic }}</strong><small>{{ new Date(run.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</small></span>
        </button>
        <button v-if="research.history.next_cursor" class="load-more" type="button" @click="research.loadHistory(research.history.next_cursor ?? undefined)">加载更多历史</button>
      </section>
      <div class="sidebar-bottom">
        <div class="sidebar-heading"><h2>运行状态</h2><span class="health-indicator"><i></i>本地</span></div>
        <div class="mock-card"><span class="mock-mini">MOCK</span><p>当前所有 Provider 使用固定演示数据，不会访问外部服务。</p><a href="/docs" target="_blank" rel="noreferrer">查看 API 文档 ↗</a></div>
      </div>
    </aside>
    <main id="main" class="main-area">
      <header class="topbar">
        <div class="breadcrumb"><span>研究工作台</span><span aria-hidden="true">/</span><strong>{{ research.currentRun ? '任务详情' : '新建研究' }}</strong></div>
        <div class="topbar-right"><span class="mode-chip"><i></i>Mock 环境</span><span class="topbar-divider"></span><span class="local-chip"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2 3.5 5v4.7c0 4 2.8 6.8 6.5 8.3 3.7-1.5 6.5-4.3 6.5-8.3V5L10 2Zm0 3.2 3.5 1.6v2.9c0 2.5-1.4 4.4-3.5 5.6-2.1-1.2-3.5-3.1-3.5-5.6V6.8L10 5.2Z" /></svg>仅本机</span></div>
      </header>
      <RouterView />
    </main>
  </div>
</template>
