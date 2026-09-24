import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { useResearchStore } from '@/stores/research'
import App from '../App.vue'

const EmptyView = { template: '<div />' }

function historyRun(id = 'run-1') {
  return {
    run_id: id,
    topic: `Topic ${id}`,
    status: 'completed',
    output_format: 'narrative',
    sources: { web: true, local: true },
    created_at: '2026-09-24T00:00:00Z',
    updated_at: '2026-09-24T00:00:00Z',
    mode: 'mock',
    fixture: true,
  } as never
}

async function renderApp(path = '/') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: EmptyView },
      { path: '/runs/:id', name: 'run', component: EmptyView },
    ],
  })
  await router.push(path)
  await router.isReady()
  const pinia = createPinia()
  setActivePinia(pinia)
  const research = useResearchStore(pinia)
  research.history = { items: [historyRun()], next_cursor: null }
  vi.spyOn(api, 'history').mockResolvedValue({ items: [historyRun()], next_cursor: null })
  vi.spyOn(api, 'providers').mockResolvedValue([])
  vi.spyOn(api, 'getRun').mockResolvedValue(historyRun())
  vi.spyOn(api, 'getPlan').mockResolvedValue({ run_id: 'run-1', steps: [] } as never)
  vi.spyOn(api, 'tasks').mockResolvedValue([])
  vi.spyOn(api, 'evidence').mockResolvedValue([])
  vi.spyOn(api, 'report').mockResolvedValue({} as never)
  const wrapper = mount(App, { attachTo: document.body, global: { plugins: [pinia, router] } })
  await flushPromises()
  return { wrapper, router }
}

afterEach(() => {
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

describe('workbench navigation', () => {
  it('keeps the selected history run in the URL and returns to home for a new run', async () => {
    const { wrapper, router } = await renderApp()

    await wrapper.find('.history-item').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/runs/run-1')

    await wrapper.find('button.nav-item').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/')
  })

  it('opens a mobile-accessible history panel from the history navigation button', async () => {
    const { wrapper } = await renderApp()
    const historyButton = wrapper.find('button.history-nav')

    expect(historyButton.attributes('aria-expanded')).toBe('false')
    await historyButton.trigger('click')

    expect(historyButton.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.sidebar-history').classes()).toContain('mobile-open')
  })
})
