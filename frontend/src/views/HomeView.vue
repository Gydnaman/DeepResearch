<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResearchStore } from '@/stores/research'
import type { CreateRunBody, OutputFormat } from '@/api/types'
import { onboardingSession } from './onboardingSession'

const research = useResearchStore()
const route = useRoute()
const router = useRouter()
const onboardingStorageKey = 'deepresearch.onboarding.dismissed.v1'
const onboardingVisible = ref(false)
let onboardingReady = false
const topic = ref('')
const dimensionsText = ref('成本, 可靠性, 部署条件')
const outputFormat = ref<OutputFormat>('narrative')
const webEnabled = ref(true)
const localEnabled = ref(true)
const startDate = ref('')
const endDate = ref('')
const maxReflectRounds = ref(1)
const maxScoutCalls = ref(3)
const maxConcurrentScouts = ref(2)
const maxRuntime = ref(45)
const maxTokens = ref(0)
const formError = ref('')

const progressPercent = computed(() => {
  if (research.currentRun?.status === 'completed') return 100
  const reflectStarted = research.events.some((event) => event.node === 'reflect')
  const totalNodes = 7 + Number(reflectStarted)
  return Math.min(100, Math.round((research.completedEvents / totalNodes) * 100))
})
const statusLabel: Record<string, string> = {
  planned: '待确认', queued: '排队中', running: '研究中', completed: '已完成', failed: '失败', cancelled: '已取消',
}
const statusTone: Record<string, string> = {
  planned: 'tone-neutral', queued: 'tone-waiting', running: 'tone-running', completed: 'tone-success', failed: 'tone-danger', cancelled: 'tone-muted',
}

function eventTime(value?: string) {
  return value
    ? new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : ''
}

function reportParts(body: string) {
  const chunks = body.split(/(\[\[cite:[0-9a-f-]{36}\]\])/gi)
  return chunks.map((text) => {
    const match = text.match(/^\[\[cite:([0-9a-f-]{36})\]\]$/i)
    const citation = match ? research.report?.citations?.find((item) => item.citation_id === match[1]) : undefined
    return { text: match ? `[${citation?.marker ?? '引用'}]` : text, evidenceId: citation?.evidence_id ?? '' }
  })
}

async function submitResearch() {
  formError.value = ''
  const topicValue = topic.value.trim()
  if (!topicValue) {
    formError.value = '请输入研究主题。'
    document.getElementById('topic')?.focus()
    return
  }
  if (!webEnabled.value && !localEnabled.value) {
    formError.value = '至少启用一个研究来源。'
    return
  }
  if (Boolean(startDate.value) !== Boolean(endDate.value)) {
    formError.value = '时间范围的起止日期需要同时填写。'
    return
  }
  if (startDate.value && endDate.value && startDate.value > endDate.value) {
    formError.value = '开始日期不能晚于结束日期。'
    return
  }
  const body: CreateRunBody & { budgets: NonNullable<CreateRunBody['budgets']> } = {
    topic: topicValue,
    dimensions: dimensionsText.value.split(',').map((item) => item.trim()).filter(Boolean),
    output_format: outputFormat.value,
    sources: { web: webEnabled.value, local: localEnabled.value },
    budgets: {
      max_reflect_rounds: maxReflectRounds.value,
      max_scout_calls: maxScoutCalls.value,
      max_concurrent_scouts: maxConcurrentScouts.value,
      max_runtime_seconds: maxRuntime.value,
    },
  }
  if (maxTokens.value > 0) body.budgets.max_tokens = maxTokens.value
  if (startDate.value && endDate.value) body.time_range = { start: startDate.value, end: endDate.value }
  try {
    await research.createRun(body)
    if (research.currentRun) {
      await router.replace({ name: 'run', params: { id: research.currentRun.run_id } })
    }
  } catch {
    formError.value = research.error
  }
}

function openEvidence(id: string) {
  research.jumpToEvidence(id)
}

function maybeShowOnboarding() {
  if (!onboardingReady || route.name !== 'home') return
  if (onboardingSession.dismissed) {
    onboardingVisible.value = false
    return
  }
  try {
    onboardingVisible.value = window.localStorage.getItem(onboardingStorageKey) !== 'true'
  } catch {
    onboardingVisible.value = true
  }
}

function dismissOnboarding() {
  onboardingSession.dismissed = true
  onboardingVisible.value = false
  try {
    window.localStorage.setItem(onboardingStorageKey, 'true')
  } catch {
    // Keep the guide dismissible for this visit if browser storage is unavailable.
  }
}

function focusTopic() {
  const field = document.getElementById('topic')
  const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  field?.scrollIntoView?.({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' })
  field?.focus()
}

onMounted(() => {
  onboardingReady = true
  maybeShowOnboarding()
  const runId = route.params.id
  if (typeof runId === 'string') void research.openRun(runId)
})
watch(() => route.name, maybeShowOnboarding)
watch(() => route.params.id, (id) => {
  if (typeof id === 'string' && id !== research.currentRun?.run_id) void research.openRun(id)
  else if (typeof id !== 'string' && research.currentRun) research.resetCurrent()
})
</script>

<template>
  <div class="workspace-page">
    <section class="page-heading">
      <div>
        <div class="eyebrow"><span class="eyebrow-line"></span>研究编排 <span class="eyebrow-dot">·</span> MOCK RUNSPACE</div>
        <h1>研究工作台</h1>
        <p>将问题拆解为可追溯的证据链，查看每一步如何形成结论。</p>
      </div>
      <div class="heading-meta"><span class="mode-chip"><i></i>结果来自固定 Fixture</span><span class="timestamp-label">无外部 API 调用</span></div>
    </section>

    <div v-if="formError || research.error" class="error-banner" role="alert">
      <span class="error-mark" aria-hidden="true">!</span><span>{{ formError || research.error }}</span>
      <button type="button" class="icon-button" aria-label="关闭错误提示" @click="formError = ''; research.error = ''">×</button>
    </div>

    <section v-if="onboardingVisible && route.name === 'home' && !research.currentRun" class="onboarding-card" aria-labelledby="onboarding-title">
      <div class="onboarding-card-heading">
        <div><p class="onboarding-kicker">快速上手 · 三步</p><h2 id="onboarding-title">从主题到可检查的演示报告</h2><p class="onboarding-intro">按顺序填写主题、确认计划，再检查事件、证据和引用。你也可以直接开始填写。</p></div>
        <button class="onboarding-dismiss" type="button" @click="dismissOnboarding">关闭引导</button>
      </div>
      <ol class="onboarding-steps">
        <li><span class="onboarding-step-number" aria-hidden="true">01</span><div><h3>填写研究主题</h3><p>描述要回答的问题，并按需调整来源、关注维度和报告结构。来源选项对应固定演示样本。</p></div></li>
        <li><span class="onboarding-step-number" aria-hidden="true">02</span><div><h3>检查计划并开始</h3><p>生成计划后，先查看问题、步骤和来源任务；确认后再启动运行。</p></div></li>
        <li><span class="onboarding-step-number" aria-hidden="true">03</span><div><h3>检查证据与引用</h3><p>查看运行事件、证据池和报告。点击报告中的引用编号可定位到对应证据。</p></div></li>
      </ol>
      <div class="onboarding-card-footer"><p><strong>Mock 演示：</strong>不会访问真实 Web、模型服务或本地语料；报告不是经过真实来源验证的研究结论。</p><button class="onboarding-start" type="button" @click="focusTopic">开始填写主题</button></div>
    </section>

    <section id="composer" class="panel composer-panel" aria-labelledby="composer-title">
      <div class="panel-heading">
        <div class="panel-title-wrap"><span class="step-number">01</span><div><h2 id="composer-title">定义研究任务</h2><p>描述主题、来源与分析边界</p></div></div>
        <span class="required-note"><span>*</span> 必填项</span>
      </div>
      <form class="research-form" @submit.prevent="submitResearch">
        <div class="form-main">
          <label class="field-label" for="topic">研究主题 <span>*</span></label>
          <textarea id="topic" v-model="topic" name="topic" rows="2" maxlength="500" placeholder="例如：长时储能如何影响高比例可再生能源电网的可靠性？" aria-describedby="topic-help"></textarea>
          <div class="field-foot"><span id="topic-help">尽量明确问题范围，最多 500 个字符</span><span class="char-count">{{ topic.length }} / 500</span></div>
        </div>
        <div class="form-grid">
          <fieldset class="field-group source-group">
            <legend class="field-label">研究来源 <span>*</span></legend>
            <label class="source-option"><input v-model="webEnabled" type="checkbox" /><span class="checkmark" aria-hidden="true"></span><span class="source-symbol web-symbol" aria-hidden="true">W</span><span><strong>Web 资料</strong><small>固定网页摘要样本</small></span><span class="source-fixture">Fixture</span></label>
            <label class="source-option"><input v-model="localEnabled" type="checkbox" /><span class="checkmark" aria-hidden="true"></span><span class="source-symbol local-symbol" aria-hidden="true">L</span><span><strong>本地知识库</strong><small>内置研究笔记样本</small></span><span class="source-fixture">Fixture</span></label>
          </fieldset>
          <div class="field-group">
            <label class="field-label" for="dimensions">关注维度</label>
            <input id="dimensions" v-model="dimensionsText" type="text" placeholder="成本, 风险, 可靠性" />
            <span class="helper-text">用逗号分隔，最多 12 项</span>
          </div>
          <div class="field-group">
            <label class="field-label" for="format">报告结构</label>
            <select id="format" v-model="outputFormat">
              <option value="narrative">研究叙述</option><option value="executive_summary">执行摘要</option><option value="bullet_points">要点清单</option>
            </select>
            <span class="helper-text">Mock Writer 按结构组织章节</span>
          </div>
          <div class="field-group date-group">
            <label class="field-label" for="start-date">时间范围 <span class="optional-label">可选</span></label>
            <div class="date-inputs"><input id="start-date" v-model="startDate" type="date" aria-label="开始日期" /><span aria-hidden="true">至</span><input v-model="endDate" type="date" aria-label="结束日期" /></div>
            <span class="helper-text">可同时填写起止日期</span>
          </div>
        </div>
        <details class="budget-details">
          <summary><span class="summary-caret" aria-hidden="true">›</span>运行预算 <span class="optional-label">可以收紧默认限制</span></summary>
          <div class="budget-controls">
            <label>Reflect 上限 <select v-model.number="maxReflectRounds"><option :value="0">0 轮</option><option :value="1">1 轮</option></select></label>
            <label>Scout 调用上限 <select v-model.number="maxScoutCalls"><option :value="1">1 次</option><option :value="2">2 次</option><option :value="3">3 次</option></select></label>
            <label>Scout 并发上限 <select v-model.number="maxConcurrentScouts"><option :value="1">1 个</option><option :value="2">2 个</option></select></label>
            <label>最长运行时间 <select v-model.number="maxRuntime"><option :value="15">15 秒</option><option :value="45">45 秒</option><option :value="90">90 秒</option><option :value="120">120 秒</option></select></label>
            <label>Token 预算 <select v-model.number="maxTokens"><option :value="0">不限制</option><option :value="5000">5,000</option><option :value="20000">20,000</option><option :value="50000">50,000</option></select></label>
            <span class="budget-note">事件最多 100 条 · Mock Token 用量为“不适用”</span>
          </div>
        </details>
        <div class="form-actions">
          <p><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M9 1.5 2.8 4.3v4.4c0 3.8 2.6 6.4 6.2 7.8 3.6-1.4 6.2-4 6.2-7.8V4.3L9 1.5Zm0 3 3.2 1.4v2.8c0 2.2-1.3 4-3.2 5.1-1.9-1.1-3.2-2.9-3.2-5.1V5.9L9 4.5Z" /></svg>演示模式不会访问 Web 或模型服务</p>
          <button class="button-primary" type="submit" :disabled="research.busy"><span v-if="research.busy" class="spinner" aria-hidden="true"></span><span v-else>生成研究计划</span><span v-if="!research.busy" class="button-arrow" aria-hidden="true">→</span><span v-else>正在创建…</span></button>
        </div>
      </form>
    </section>

    <section v-if="research.currentRun && research.plan" class="run-overview" aria-label="当前研究">
      <div class="run-heading panel">
        <div class="run-title-block"><div class="run-kicker"><span class="step-number">02</span><span>研究计划与运行</span><span class="run-id">RUN · {{ research.currentRun.run_id.slice(0, 8).toUpperCase() }}</span></div><h2>{{ research.currentRun.topic }}</h2><div class="run-submeta"><span>{{ new Date(research.currentRun.created_at).toLocaleString('zh-CN') }}</span><span class="meta-separator">·</span><span>{{ research.currentRun.output_format.replace('_', ' ') }}</span><span class="mock-tag">MOCK</span><span>Token 用量：不适用</span></div></div>
        <div class="run-actions"><span class="status-badge" :class="statusTone[research.currentRun.status]"><i></i>{{ statusLabel[research.currentRun.status] }}</span><button v-if="research.currentRun.status === 'planned'" class="button-primary start-button" type="button" @click="research.startRun()">确认并开始 <span aria-hidden="true">→</span></button><button v-else-if="research.isActive" class="button-secondary cancel-button" type="button" @click="research.cancelRun()">取消运行</button><button class="button-quiet" type="button" @click="research.openRun(research.currentRun.run_id)">重新加载</button></div>
      </div>

      <div class="run-grid">
        <section class="panel plan-panel" aria-labelledby="plan-title">
          <div class="panel-heading compact-heading"><div class="panel-title-wrap"><div><h2 id="plan-title">研究计划</h2><p>启动前可查看将要执行的步骤</p></div></div><span class="step-count">{{ research.plan.steps.length }} 个步骤</span></div>
          <ol class="plan-list"><li v-for="(step, index) in research.plan.steps" :key="step.id" :class="{ skipped: step.status === 'skipped' }"><span class="plan-index">{{ String(index + 1).padStart(2, '0') }}</span><span class="plan-node"><strong>{{ step.node.replace(/_/g, ' ') }}</strong><small v-if="step.source">{{ step.source === 'web' ? 'Web 资料' : '本地知识库' }} · {{ step.status === 'skipped' ? '来源已关闭' : 'Mock Scout' }}</small><small v-else>研究流程节点</small></span><span class="plan-state">{{ step.status === 'skipped' ? '已跳过' : '已规划' }}</span></li></ol>
          <div class="questions-box"><h3>需要回答的问题</h3><ul><li v-for="question in research.plan.questions" :key="question">{{ question }}</li></ul></div>
        </section>

        <div class="activity-column">
          <section class="panel progress-panel" aria-labelledby="progress-title">
            <div class="panel-heading compact-heading"><div><h2 id="progress-title">运行进度</h2><p>{{ research.isActive ? '研究图按顺序推进，事件实时保存。' : '节点完成情况与事件记录。' }}</p></div><span class="connection-state" :class="`connection-${research.connection}`"><i></i>{{ research.connection === 'connected' ? '实时连接' : research.connection === 'reconnecting' ? '正在重连' : research.connection === 'closed' ? '连接已关闭' : research.connection === 'connecting' ? '连接中' : '未连接' }}</span></div>
            <div class="progress-track" role="progressbar" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100" :aria-label="`研究进度 ${progressPercent}%`"><span :style="{ width: `${progressPercent}%` }"></span></div>
            <div class="progress-caption"><span>{{ research.completedEvents }} 个流程节点已完成</span><span>{{ progressPercent }}%</span></div>
            <div class="task-list"><div v-for="task in research.tasks" :key="task.task_id" class="task-row"><span class="task-source-icon" :class="task.source">{{ task.source === 'web' ? 'W' : 'L' }}</span><span class="task-name"><strong>{{ task.query_label }}</strong><small>{{ task.source === 'web' ? '网页摘要 Fixture' : '本地资料 Fixture' }}</small></span><span class="task-status" :class="`task-${task.status}`">{{ task.status === 'completed' ? '完成' : task.status === 'running' ? '运行中' : task.status === 'failed' ? '失败' : task.status === 'skipped' ? '已跳过' : '待执行' }}</span></div></div>
          </section>

          <section class="panel event-panel" aria-labelledby="events-title">
            <div class="panel-heading compact-heading"><div><h2 id="events-title">事件时间线</h2><p>按服务端序号排列，可断线续传</p></div><span class="event-count">{{ research.events.length }} / 100</span></div>
            <div v-if="research.events.length" class="event-list" role="log" aria-live="polite" aria-relevant="additions">
              <article v-for="event in research.events.slice(-18).reverse()" :key="event.id" class="event-item"><span class="event-sequence">{{ String(event.id).padStart(2, '0') }}</span><span class="event-marker" :class="event.status === 'failed' ? 'marker-danger' : event.event.startsWith('run.') ? 'marker-terminal' : ''"><i></i></span><div class="event-copy"><div><strong>{{ event.summary }}</strong><small>{{ eventTime(event.created_at) }}</small></div><p><code>{{ event.event }}</code><span v-if="event.error_code" class="event-error">{{ event.error_code }}</span></p></div></article>
            </div>
            <div v-else class="empty-events"><span class="empty-pulse" aria-hidden="true"></span><p>计划已就绪，确认后开始运行。</p><small>事件记录会在此按顺序出现</small></div>
          </section>
        </div>
      </div>

      <div class="results-grid">
        <section class="panel evidence-panel" aria-labelledby="evidence-title">
          <div class="panel-heading compact-heading"><div><h2 id="evidence-title">证据池</h2><p>本次运行检索到的固定样本</p></div><span class="count-pill">{{ research.evidence.length }} 条</span></div>
          <div v-if="research.evidence.length" class="evidence-list">
            <article v-for="item in research.evidence" :id="`evidence-${item.evidence_id}`" :key="item.evidence_id" class="evidence-item" :class="{ focused: research.focusedEvidenceId === item.evidence_id }">
              <div class="evidence-topline"><span class="source-label"><i :class="item.source_type">{{ item.source_type === 'web' ? 'W' : 'L' }}</i>{{ item.source_label }}</span><span class="relevance">Fixture 模拟值 <strong>{{ Math.round(item.relevance * 100) }}%</strong></span></div>
              <p>{{ item.excerpt }}</p><div class="evidence-meta"><code>{{ item.evidence_id.slice(0, 12) }}</code><span v-if="item.published_at">发布日期 {{ item.published_at }}</span><span class="fixture-mark">Fixture</span></div>
            </article>
          </div>
          <div v-else class="empty-panel"><span class="empty-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m15.5 15.5 5 5" /></svg></span><strong>{{ research.currentRun.status === 'completed' ? '此任务没有返回证据' : '证据将在 Scout 完成后出现' }}</strong><p>关闭的来源或无结果 Fixture 会在此明确显示。</p></div>
        </section>

        <section class="panel report-panel" aria-labelledby="report-title">
          <div class="panel-heading compact-heading"><div><h2 id="report-title">研究报告</h2><p>结论仅引用当前运行的证据</p></div><span v-if="research.report" class="report-fixture"><i></i>MOCK 报告</span></div>
          <template v-if="research.report">
            <div v-if="research.report.warning" class="report-warning"><span aria-hidden="true">!</span><span>{{ research.report.warning.includes('no_evidence') ? '未找到证据：本报告仅说明证据缺口。' : '部分来源不可用：结论覆盖范围有限。' }}</span></div>
            <article v-for="section in research.report.sections" :key="section.section_id" class="report-section"><h3>{{ section.title }}</h3><p class="report-body"><template v-for="(part, index) in reportParts(section.body)" :key="index"><button v-if="part.evidenceId" class="inline-citation" type="button" :aria-label="`跳转到引用证据 ${part.text}`" @click="openEvidence(part.evidenceId)">{{ part.text }}</button><span v-else>{{ part.text }}</span></template></p></article>
            <div class="citation-list"><h3>引用来源 <span>{{ research.report.citations?.length ?? 0 }}</span></h3><button v-for="citation in research.report.citations ?? []" :key="citation.citation_id" class="citation-row" type="button" @click="openEvidence(citation.evidence_id)"><span class="citation-marker">[{{ citation.marker }}]</span><span>{{ research.evidence.find((item) => item.evidence_id === citation.evidence_id)?.source_label ?? '查看证据' }}</span><span class="citation-arrow" aria-hidden="true">↗</span></button><p v-if="!research.report.citations?.length" class="no-citations">报告没有可引用的证据项。</p></div>
            <div class="report-disclaimer"><span>i</span>此报告由演示 Fixture 生成，不代表经过真实来源验证的研究结论。</div>
          </template>
          <div v-else class="empty-panel report-empty"><span class="empty-icon report-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h8l4 4V20H6zM14 3.5V8h4M9 12h6M9 15.5h6" /></svg></span><strong>{{ research.currentRun.status === 'failed' ? '任务失败，报告未发布' : research.currentRun.status === 'cancelled' ? '任务已取消，报告未发布' : '报告将在流程结束后生成' }}</strong><p>完成后可检查报告章节与每条引用对应的证据。</p></div>
        </section>
      </div>

      <footer class="page-footer"><span>DeepResearch · 阶段 A 演示</span><span>本地运行 <i></i> 数据仅来自固定 Fixture</span></footer>
    </section>
    <section id="providers" class="provider-strip" aria-label="Provider 配置状态"><div class="provider-strip-title"><span class="provider-shield">◇</span><div><strong>Provider 状态</strong><small>本地配置 · 非连接性测试</small></div></div><div v-for="provider in research.providers" :key="provider.kind" class="provider-status"><span class="provider-dot"></span><span>{{ provider.provider }}</span><small>Mock 已配置</small></div><p>未接入真实模型或搜索服务</p></section>
  </div>
</template>
