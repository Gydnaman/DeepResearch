import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { useResearchStore } from '../research'

class FakeEventSource extends EventTarget {
  static instances: FakeEventSource[] = []
  onopen: ((this: EventSource, ev: Event) => unknown) | null = null
  onerror: ((this: EventSource, ev: Event) => unknown) | null = null
  closed = false

  constructor(readonly url: string | URL) {
    super()
    FakeEventSource.instances.push(this)
  }

  close() {
    this.closed = true
  }
}

function run(id = 'run-1', status = 'planned') {
  return {
    run_id: id,
    topic: `Topic ${id}`,
    status,
    output_format: 'narrative',
    sources: { web: true, local: true },
    created_at: '2026-09-24T00:00:00Z',
    updated_at: '2026-09-24T00:00:00Z',
    mode: 'mock',
    fixture: true,
  } as never
}

function plan(id = 'run-1') {
  return { run_id: id, questions: [], steps: [], created_at: '2026-09-24T00:00:00Z', mode: 'mock', fixture: true } as never
}

function mockDetails(id = 'run-1') {
  vi.spyOn(api, 'getRun').mockImplementation(async (runId) => run(runId || id))
  vi.spyOn(api, 'getPlan').mockImplementation(async (runId) => plan(runId || id))
  vi.spyOn(api, 'tasks').mockResolvedValue([])
  vi.spyOn(api, 'evidence').mockResolvedValue([])
  vi.spyOn(api, 'report').mockResolvedValue({} as never)
  vi.spyOn(api, 'history').mockResolvedValue({ items: [] })
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('research event stream', () => {
  it('adds each persisted event kind to the local timeline', async () => {
    mockDetails()
    const research = useResearchStore()
    await research.openRun('run-1')
    const source = FakeEventSource.instances[0]
    const names = ['node.started', 'node.skipped', 'evidence.added', 'budget.updated']

    names.forEach((name, index) => {
      source?.dispatchEvent(new MessageEvent(name, {
        data: JSON.stringify({
          id: index + 1,
          run_id: 'run-1',
          event: name,
          phase: 'test',
          node: null,
          status: 'running',
          run_status: 'running',
          summary: name,
          fixture: true,
          created_at: '2026-09-24T00:00:00Z',
          evidence_ids: [],
        }),
      }))
    })

    expect(research.events.map((event) => event.event)).toEqual(names)
  })

  it('reconnects from the advertised recovery cursor after a stream control error', async () => {
    mockDetails()
    const research = useResearchStore()
    await research.openRun('run-1')
    const source = FakeEventSource.instances[0]
    source?.dispatchEvent(new MessageEvent('stream.error', {
      data: JSON.stringify({ message: 'Invalid cursor', recovery: 'restart_from_zero' }),
    }))

    expect(FakeEventSource.instances).toHaveLength(2)
    expect(String(FakeEventSource.instances[1]?.url)).toContain('after=0')
  })

  it('keeps the latest run selected when overlapping detail requests resolve out of order', async () => {
    const oldRun = deferred<Awaited<ReturnType<typeof api.getRun>>>()
    vi.spyOn(api, 'getRun').mockImplementation((id) => id === 'run-old' ? oldRun.promise : Promise.resolve(run(id)))
    vi.spyOn(api, 'getPlan').mockImplementation(async (id) => plan(id))
    vi.spyOn(api, 'tasks').mockResolvedValue([])
    vi.spyOn(api, 'evidence').mockResolvedValue([])
    vi.spyOn(api, 'report').mockResolvedValue({} as never)
    vi.spyOn(api, 'history').mockResolvedValue({ items: [] })
    const research = useResearchStore()

    const oldRequest = research.openRun('run-old')
    await research.openRun('run-new')
    oldRun.resolve(run('run-old'))
    await oldRequest

    expect((research.currentRun as { run_id: string } | null)?.run_id).toBe('run-new')
    expect(research.plan?.run_id).toBe('run-new')
    expect(String(FakeEventSource.instances[FakeEventSource.instances.length - 1]?.url)).toContain('/run-new/')
  })

  it('does not let a slow task refresh overwrite a terminal snapshot', async () => {
    const staleRun = deferred<Awaited<ReturnType<typeof api.getRun>>>()
    let reads = 0
    vi.spyOn(api, 'getRun').mockImplementation(async (id) => {
      reads += 1
      if (reads === 3) return staleRun.promise
      return run(id, reads === 4 ? 'completed' : 'planned')
    })
    vi.spyOn(api, 'getPlan').mockImplementation(async (id) => plan(id))
    vi.spyOn(api, 'tasks').mockResolvedValue([])
    vi.spyOn(api, 'evidence').mockResolvedValue([])
    vi.spyOn(api, 'report').mockResolvedValue({} as never)
    vi.spyOn(api, 'history').mockResolvedValue({ items: [] })
    const research = useResearchStore()
    await research.openRun('run-1')
    const source = FakeEventSource.instances[0]

    source?.dispatchEvent(new MessageEvent('search_task.completed', {
      data: JSON.stringify({ id: 1, run_id: 'run-1', event: 'search_task.completed', run_status: 'running', created_at: '2026-09-24T00:00:01Z' }),
    }))
    source?.dispatchEvent(new MessageEvent('run.completed', {
      data: JSON.stringify({ id: 2, run_id: 'run-1', event: 'run.completed', run_status: 'completed', created_at: '2026-09-24T00:00:02Z' }),
    }))
    await vi.waitFor(() => expect(research.currentRun?.status).toBe('completed'))
    staleRun.resolve(run('run-1', 'running'))
    await vi.waitFor(() => expect(reads).toBeGreaterThanOrEqual(4))

    expect(research.currentRun?.status).toBe('completed')
  })

  it('deduplicates concurrent history page requests for the same cursor', async () => {
    const nextPage = deferred<Awaited<ReturnType<typeof api.history>>>()
    const history = vi.spyOn(api, 'history')
      .mockResolvedValueOnce({ items: [run('run-1')], next_cursor: 'cursor-1' } as never)
      .mockReturnValue(nextPage.promise)
    const research = useResearchStore()
    await research.loadHistory()

    const first = research.loadHistory('cursor-1')
    const duplicate = research.loadHistory('cursor-1')
    nextPage.resolve({ items: [run('run-2')], next_cursor: null } as never)
    await Promise.all([first, duplicate])

    expect(history.mock.calls.filter((call) => call[1] === 'cursor-1')).toHaveLength(1)
    expect(research.history.items.map((item) => item.run_id)).toEqual(['run-1', 'run-2'])
  })

  it('does not let an older history page overwrite a newer refresh', async () => {
    const stalePage = deferred<Awaited<ReturnType<typeof api.history>>>()
    const history = vi.spyOn(api, 'history')
      .mockResolvedValueOnce({ items: [run('run-1')], next_cursor: 'cursor-1' } as never)
      .mockReturnValueOnce(stalePage.promise)
      .mockResolvedValueOnce({ items: [run('run-new')], next_cursor: null } as never)
    const research = useResearchStore()
    await research.loadHistory()

    const olderRequest = research.loadHistory('cursor-1')
    await research.loadHistory()
    stalePage.resolve({ items: [run('run-stale')], next_cursor: null } as never)
    await olderRequest

    expect(history).toHaveBeenCalledTimes(3)
    expect(research.history.items.map((item) => item.run_id)).toEqual(['run-new'])
  })

  it('keeps pagination blocked until the latest overlapping history refresh finishes', async () => {
    const olderRefresh = deferred<Awaited<ReturnType<typeof api.history>>>()
    const latestRefresh = deferred<Awaited<ReturnType<typeof api.history>>>()
    const history = vi.spyOn(api, 'history')
      .mockResolvedValueOnce({ items: [run('run-1')], next_cursor: 'cursor-1' } as never)
      .mockReturnValueOnce(olderRefresh.promise)
      .mockReturnValueOnce(latestRefresh.promise)
    const research = useResearchStore()
    await research.loadHistory()

    const oldRequest = research.loadHistory()
    const latestRequest = research.loadHistory()
    olderRefresh.resolve({ items: [run('run-stale')], next_cursor: 'cursor-stale' } as never)
    await oldRequest
    await research.loadHistory('cursor-1')
    latestRefresh.resolve({ items: [run('run-new')], next_cursor: null } as never)
    await latestRequest

    expect(history).toHaveBeenCalledTimes(3)
    expect(research.history.items.map((item) => item.run_id)).toEqual(['run-new'])
  })

  it('does not let a late start response replace a terminal event or reconnect', async () => {
    const startResponse = deferred<Awaited<ReturnType<typeof api.start>>>()
    let runReads = 0
    vi.spyOn(api, 'getRun').mockImplementation(async (id) => {
      runReads += 1
      return run(id, runReads === 1 ? 'planned' : 'completed')
    })
    vi.spyOn(api, 'getPlan').mockImplementation(async (id) => plan(id))
    vi.spyOn(api, 'tasks').mockResolvedValue([])
    vi.spyOn(api, 'evidence').mockResolvedValue([])
    vi.spyOn(api, 'report').mockResolvedValue({} as never)
    vi.spyOn(api, 'history').mockResolvedValue({ items: [] })
    vi.spyOn(api, 'start').mockReturnValue(startResponse.promise)
    const research = useResearchStore()
    await research.openRun('run-1')

    const pendingStart = research.startRun()
    FakeEventSource.instances[0]?.dispatchEvent(new MessageEvent('run.completed', {
      data: JSON.stringify({ id: 1, run_id: 'run-1', event: 'run.completed', run_status: 'completed', created_at: '2026-09-24T00:00:01Z' }),
    }))
    await vi.waitFor(() => expect(research.currentRun?.status).toBe('completed'))
    startResponse.resolve(run('run-1', 'queued') as never)
    await pendingStart

    expect(research.currentRun?.status).toBe('completed')
    expect(FakeEventSource.instances).toHaveLength(1)
  })

  it('ignores a late create response after another run is selected', async () => {
    const created = deferred<Awaited<ReturnType<typeof api.create>>>()
    mockDetails()
    vi.spyOn(api, 'create').mockReturnValue(created.promise)
    const research = useResearchStore()
    const pendingCreate = research.createRun({ topic: 'new topic' } as never)
    await research.openRun('run-new')
    created.resolve({ run: run('run-created'), plan: plan('run-created') } as never)
    await pendingCreate

    expect((research.currentRun as { run_id: string } | null)?.run_id).toBe('run-new')
    expect(String(FakeEventSource.instances[FakeEventSource.instances.length - 1]?.url)).toContain('/run-new/')
  })

  it('clears the busy state when a pending create is abandoned for a new task', async () => {
    const created = deferred<Awaited<ReturnType<typeof api.create>>>()
    vi.spyOn(api, 'create').mockReturnValue(created.promise)
    const research = useResearchStore()
    const pendingCreate = research.createRun({ topic: 'new topic' } as never)
    research.resetCurrent()
    created.resolve({ run: run('run-abandoned'), plan: plan('run-abandoned') } as never)
    await pendingCreate

    expect(research.busy).toBe(false)
    expect(research.currentRun).toBeNull()
  })

  it.each(['start', 'cancel'] as const)('ignores a late %s response after another run is selected', async (action) => {
    const response = deferred<Awaited<ReturnType<typeof api.start>>>()
    mockDetails()
    vi.spyOn(api, action).mockReturnValue(response.promise as never)
    const research = useResearchStore()
    research.currentRun = run('run-old')
    const pendingAction = action === 'start' ? research.startRun() : research.cancelRun()
    await research.openRun('run-new')
    response.resolve(run('run-old', action === 'start' ? 'queued' : 'cancelled') as never)
    await pendingAction

    expect((research.currentRun as { run_id: string } | null)?.run_id).toBe('run-new')
    expect(String(FakeEventSource.instances[FakeEventSource.instances.length - 1]?.url)).toContain('/run-new/')
  })
})

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
