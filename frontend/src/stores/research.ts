import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { CreateRunBody, Evidence, Plan, ProviderStatus, Report, ResearchEvent, RunPage, RunSummary, SearchTask } from '@/api/types'

const eventNames = [
  'plan.ready', 'run.queued', 'run.started', 'run.completed', 'run.failed', 'run.cancelled',
  'node.started', 'node.completed', 'node.failed', 'node.skipped', 'evidence.added', 'budget.updated',
  'search_task.started', 'search_task.completed', 'search_task.failed',
]

export const useResearchStore = defineStore('research', () => {
  const currentRun = ref<RunSummary | null>(null)
  const plan = ref<Plan | null>(null)
  const events = ref<ResearchEvent[]>([])
  const tasks = ref<SearchTask[]>([])
  const evidence = ref<Evidence[]>([])
  const report = ref<Report | null>(null)
  const providers = ref<ProviderStatus[]>([])
  const history = ref<RunPage>({ items: [] })
  const busy = ref(false)
  const error = ref('')
  const connection = ref<'idle' | 'connecting' | 'connected' | 'reconnecting' | 'closed'>('idle')
  const focusedEvidenceId = ref('')
  let eventSource: EventSource | null = null
  let lastEventId = 0
  let selectionRequest = 0
  let detailRequest = 0
  let historyRequest = 0
  let historyRefreshing = false
  const historyCursorsInFlight = new Set<string>()

  const isActive = computed(() => Boolean(currentRun.value && ['queued', 'running'].includes(currentRun.value.status)))
  const completedEvents = computed(() => new Set(
    events.value.filter((event) => event.event === 'node.completed' && event.node).map((event) => event.node),
  ).size)

  function stopStream() {
    eventSource?.close()
    eventSource = null
    connection.value = 'closed'
  }

  function isCurrentSelection(runId: string, requestId: number) {
    return requestId === selectionRequest && currentRun.value?.run_id === runId
  }

  async function refreshDetails(id: string, requestId?: number) {
    const detailId = ++detailRequest
    const selectionId = requestId ?? selectionRequest
    const isCurrentRequest = () =>
      detailId === detailRequest &&
      selectionId === selectionRequest &&
      currentRun.value?.run_id === id
    const [run, nextTasks, nextEvidence] = await Promise.all([api.getRun(id), api.tasks(id), api.evidence(id)])
    if (!isCurrentRequest()) return
    let nextReport: Report | null = null
    try { nextReport = await api.report(id) } catch { nextReport = null }
    if (!isCurrentRequest()) return
    currentRun.value = run
    tasks.value = nextTasks
    evidence.value = nextEvidence
    report.value = nextReport
    if (['completed', 'failed', 'cancelled'].includes(run.status)) stopStream()
  }

  function consumeEvent(event: MessageEvent<string>) {
    const item = JSON.parse(event.data) as ResearchEvent
    if (currentRun.value && currentRun.value.run_id !== item.run_id) return
    if (!events.value.some((seen) => seen.id === item.id && seen.run_id === item.run_id)) {
      events.value = [...events.value, item].sort((a, b) => a.id - b.id)
    }
    lastEventId = Math.max(lastEventId, item.id)
    if (currentRun.value && currentRun.value.run_id === item.run_id) {
      currentRun.value = {
        ...currentRun.value,
        status: item.run_status,
        updated_at: item.created_at ?? currentRun.value.updated_at,
      }
      if (item.event.startsWith('search_task.')) void refreshDetails(item.run_id)
      if (['run.completed', 'run.failed', 'run.cancelled'].includes(item.event)) {
        stopStream()
        void refreshDetails(item.run_id)
      }
    }
  }

  function connect(id: string, after = lastEventId) {
    stopStream()
    connection.value = 'connecting'
    eventSource = new EventSource(`/api/v1/research-runs/${id}/events?after=${after}`)
    eventSource.onopen = () => { connection.value = 'connected' }
    eventSource.onerror = () => { connection.value = 'reconnecting' }
    for (const name of eventNames) eventSource.addEventListener(name, (event) => consumeEvent(event as MessageEvent<string>))
    eventSource.addEventListener('stream.error', (event) => {
      const source = eventSource
      const control = JSON.parse((event as MessageEvent<string>).data) as { message: string; recovery?: string }
      error.value = control.message
      source?.close()
      if (eventSource === source) eventSource = null
      if (control.recovery === 'restart_from_zero' && currentRun.value?.run_id === id) {
        lastEventId = 0
        connection.value = 'reconnecting'
        connect(id, 0)
      } else {
        connection.value = 'closed'
      }
    })
  }

  async function loadProviders() {
    try { providers.value = await api.providers() } catch (caught) { error.value = caught instanceof Error ? caught.message : '无法读取 Provider 状态' }
  }

  async function loadHistory(cursor?: string) {
    if (cursor && (historyRefreshing || cursor !== history.value.next_cursor || historyCursorsInFlight.has(cursor))) return
    const requestId = ++historyRequest
    if (cursor) historyCursorsInFlight.add(cursor)
    else historyRefreshing = true
    busy.value = true
    try {
      const page = await api.history(20, cursor)
      if (requestId !== historyRequest) return
      if (cursor) {
        const existingIds = new Set(history.value.items.map((item) => item.run_id))
        history.value = {
          items: [...history.value.items, ...page.items.filter((item) => !existingIds.has(item.run_id))],
          next_cursor: page.next_cursor,
        }
      } else {
        history.value = page
      }
    } catch (caught) {
      if (requestId === historyRequest) error.value = caught instanceof Error ? caught.message : '历史记录加载失败'
    } finally {
      if (cursor) historyCursorsInFlight.delete(cursor)
      else if (requestId === historyRequest) historyRefreshing = false
      if (requestId === historyRequest) busy.value = false
    }
  }

  async function createRun(body: CreateRunBody) {
    const requestId = ++selectionRequest
    detailRequest += 1
    lastEventId = 0
    busy.value = true
    error.value = ''
    try {
      const created = await api.create(body)
      if (requestId !== selectionRequest) return
      currentRun.value = created.run
      plan.value = created.plan
      events.value = []
      const nextTasks = await api.tasks(created.run.run_id)
      if (!isCurrentSelection(created.run.run_id, requestId)) return
      tasks.value = nextTasks
      evidence.value = []
      report.value = null
      connect(created.run.run_id)
      await loadHistory()
    } catch (caught) {
      if (requestId !== selectionRequest) return
      error.value = caught instanceof Error ? caught.message : '研究任务创建失败'
      throw caught
    } finally { if (requestId === selectionRequest) busy.value = false }
  }

  async function openRun(id: string) {
    const requestId = ++selectionRequest
    detailRequest += 1
    busy.value = true
    error.value = ''
    stopStream()
    try {
      const [run, nextPlan] = await Promise.all([api.getRun(id), api.getPlan(id)])
      if (requestId !== selectionRequest) return
      currentRun.value = run
      plan.value = nextPlan
      events.value = []
      lastEventId = 0
      await refreshDetails(id, requestId)
      if (requestId !== selectionRequest) return
      connect(id, 0)
    } catch (caught) {
      if (requestId === selectionRequest) error.value = caught instanceof Error ? caught.message : '研究任务加载失败'
    } finally { if (requestId === selectionRequest) busy.value = false }
  }

  async function startRun() {
    if (!currentRun.value) return
    const runId = currentRun.value.run_id
    const requestId = selectionRequest
    error.value = ''
    try {
      const started = await api.start(runId)
      if (!isCurrentSelection(runId, requestId)) return
      const currentStatus = currentRun.value?.status
      const alreadyAdvanced = currentStatus === 'running' || ['completed', 'failed', 'cancelled'].includes(currentStatus ?? '')
      if (!alreadyAdvanced) currentRun.value = started
      if (currentRun.value && ['queued', 'running'].includes(currentRun.value.status) && eventSource === null) {
        connect(runId, events.value[events.value.length - 1]?.id ?? 0)
      }
      await loadHistory()
    } catch (caught) {
      if (isCurrentSelection(runId, requestId)) error.value = caught instanceof Error ? caught.message : '启动失败'
    }
  }

  async function cancelRun() {
    if (!currentRun.value) return
    const runId = currentRun.value.run_id
    const requestId = selectionRequest
    error.value = ''
    try {
      const cancelled = await api.cancel(runId)
      if (!isCurrentSelection(runId, requestId)) return
      currentRun.value = cancelled
      await refreshDetails(runId, requestId)
      if (!isCurrentSelection(runId, requestId)) return
      await loadHistory()
    } catch (caught) {
      if (isCurrentSelection(runId, requestId)) error.value = caught instanceof Error ? caught.message : '取消失败'
    }
  }

  function jumpToEvidence(id: string) {
    focusedEvidenceId.value = id
    document.getElementById(`evidence-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    window.setTimeout(() => { focusedEvidenceId.value = '' }, 1800)
  }

  function resetCurrent() {
    selectionRequest += 1
    detailRequest += 1
    busy.value = false
    lastEventId = 0
    stopStream()
    currentRun.value = null
    plan.value = null
    events.value = []
    tasks.value = []
    evidence.value = []
    report.value = null
    error.value = ''
  }

  return {
    currentRun, plan, events, tasks, evidence, report, providers, history, busy, error,
    connection, focusedEvidenceId, isActive, completedEvents, stopStream, loadProviders,
    loadHistory, createRun, openRun, startRun, cancelRun, jumpToEvidence, resetCurrent,
  }
})
