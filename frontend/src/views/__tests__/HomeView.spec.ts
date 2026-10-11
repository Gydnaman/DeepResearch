import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useResearchStore } from '@/stores/research'
import HomeView from '../HomeView.vue'
import { onboardingSession } from '../onboardingSession'

const onboardingStorageKey = 'deepresearch.onboarding.dismissed.v1'

async function renderHome() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: HomeView },
      { path: '/runs/:id', name: 'run', component: HomeView },
    ],
  })
  await router.push('/')
  await router.isReady()
  const pinia = createPinia()
  setActivePinia(pinia)
  const research = useResearchStore(pinia)
  const wrapper = mount(HomeView, { attachTo: document.body, global: { plugins: [pinia, router] } })
  return { wrapper, research, router }
}

beforeEach(() => { onboardingSession.dismissed = false; localStorage.removeItem(onboardingStorageKey) })
afterEach(() => { onboardingSession.dismissed = false; vi.restoreAllMocks(); localStorage.removeItem(onboardingStorageKey); document.body.innerHTML = '' })

describe('research task form', () => {
  it('explains that a topic is required before submission', async () => {
    const { wrapper } = await renderHome()

    await wrapper.find('form').trigger('submit')

    expect(wrapper.find('.error-banner').text()).toContain('请输入研究主题')
    expect(wrapper.find('#topic').element).toBe(document.activeElement)
  })

  it('requires at least one fixture source', async () => {
    const { wrapper } = await renderHome()
    await wrapper.find('#topic').setValue('Grid scale storage')
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    if (checkboxes[0]) await checkboxes[0].setValue(false)
    if (checkboxes[1]) await checkboxes[1].setValue(false)
    await wrapper.find('form').trigger('submit')

    expect(wrapper.find('.error-banner').text()).toContain('至少启用一个研究来源')
  })

  it('requires both dates and an ordered date range', async () => {
    const { wrapper } = await renderHome()
    await wrapper.find('#topic').setValue('Grid scale storage')
    await wrapper.find('#start-date').setValue('2025-12-31')
    await wrapper.find('input[aria-label="结束日期"]').setValue('2025-01-01')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.find('.error-banner').text()).toContain('开始日期不能晚于结束日期')
  })

  it('submits the selected sources, report format, budgets, and date range', async () => {
    const { wrapper, research } = await renderHome()
    const createRun = vi.spyOn(research, 'createRun').mockResolvedValue()
    await wrapper.find('#topic').setValue('Grid scale storage')
    await wrapper.find('#dimensions').setValue('cost, risk')
    await wrapper.find('#format').setValue('bullet_points')
    await wrapper.findAll('input[type="checkbox"]')[0]?.setValue(false)
    await wrapper.find('#start-date').setValue('2025-01-01')
    await wrapper.find('input[aria-label="结束日期"]').setValue('2025-12-31')
    await wrapper.findAll('select')[5]?.setValue('5000')
    await wrapper.find('form').trigger('submit')

    expect(createRun).toHaveBeenCalledWith({
      topic: 'Grid scale storage',
      dimensions: ['cost', 'risk'],
      output_format: 'bullet_points',
      sources: { web: false, local: true },
      budgets: {
        max_reflect_rounds: 1,
        max_scout_calls: 3,
        max_concurrent_scouts: 2,
        max_runtime_seconds: 45,
        max_tokens: 5000,
      },
      time_range: { start: '2025-01-01', end: '2025-12-31' },
    })
  })

  it('shows completed runs at 100 percent when Scout plan steps share one graph node', async () => {
    const { wrapper, research } = await renderHome()
    research.currentRun = {
      run_id: 'run-1',
      topic: 'Grid scale storage',
      status: 'completed',
      output_format: 'narrative',
      sources: { web: true, local: true },
      created_at: '2026-09-24T00:00:00Z',
      updated_at: '2026-09-24T00:00:00Z',
      mode: 'mock',
      fixture: true,
    } as never
    research.plan = {
      run_id: 'run-1',
      questions: [],
      steps: [
        { node: 'intent_router', status: 'completed' },
        { node: 'planner', status: 'completed' },
        { node: 'web_scout', status: 'completed' },
        { node: 'local_scout', status: 'completed' },
        { node: 'evidence_judge', status: 'completed' },
        { node: 'analyst', status: 'completed' },
        { node: 'writer', status: 'completed' },
          { node: 'citation_validator', status: 'completed' },
      ],
      created_at: '2026-09-24T00:00:00Z',
      mode: 'mock',
      fixture: true,
    } as never
    research.events = [
      'intent_router', 'planner', 'scouts', 'evidence_judge', 'analyst', 'writer', 'citation_validator',
    ].map((node, index) => ({ id: index + 1, node, event: 'node.completed' } as never))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[role="progressbar"]').attributes('aria-valuenow')).toBe('100')
    expect(wrapper.find('.progress-caption').text()).toContain('100%')
  })

  it('routes to the new run after submitting from a run detail URL', async () => {
    const { wrapper, research, router } = await renderHome()
    vi.spyOn(research, 'openRun').mockResolvedValue()
    vi.spyOn(research, 'createRun').mockImplementation(async () => {
      research.currentRun = {
        run_id: 'run-new',
        topic: 'Grid scale storage',
        status: 'planned',
        output_format: 'narrative',
        sources: { web: true, local: true },
        created_at: '2026-09-24T00:00:00Z',
        updated_at: '2026-09-24T00:00:00Z',
        mode: 'mock',
        fixture: true,
      } as never
    })
    await router.push('/runs/run-old')
    await flushPromises()
    await wrapper.find('#topic').setValue('Grid scale storage')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/runs/run-new')
  })

  it('keeps the data source navigation target in the visible provider strip', async () => {
    const { wrapper } = await renderHome()

    expect(wrapper.find('#providers').classes()).toContain('provider-strip')
  })

  it('keeps the onboarding guide dismissed across remounts when browser storage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('storage unavailable') })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('storage unavailable') })

    const firstVisit = await renderHome()
    expect(firstVisit.wrapper.find('.onboarding-card').exists()).toBe(true)
    await firstVisit.wrapper.find('.onboarding-dismiss').trigger('click')
    firstVisit.wrapper.unmount()

    const returnVisit = await renderHome()
    expect(returnVisit.wrapper.find('.onboarding-card').exists()).toBe(false)
    returnVisit.wrapper.unmount()
  })

  it('persists onboarding dismissal in localStorage across remounts', async () => {
    const firstVisit = await renderHome()
    expect(firstVisit.wrapper.find('.onboarding-card').exists()).toBe(true)

    await firstVisit.wrapper.find('.onboarding-dismiss').trigger('click')
    expect(localStorage.getItem(onboardingStorageKey)).toBe('true')
    firstVisit.wrapper.unmount()

    onboardingSession.dismissed = false
    const returnVisit = await renderHome()
    expect(returnVisit.wrapper.find('.onboarding-card').exists()).toBe(false)
    returnVisit.wrapper.unmount()
  })

  it('focuses the topic field when starting from the onboarding guide', async () => {
    const { wrapper } = await renderHome()

    await wrapper.find('.onboarding-start').trigger('click')

    expect(wrapper.find('#topic').element).toBe(document.activeElement)
  })
})
