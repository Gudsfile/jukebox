import { render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import PinoutDiagram from './PinoutDiagram.svelte'

function renderDiagram(resolved) {
  return render(PinoutDiagram, {
    props: { profile: 'custom', resolved: { reset: null, cs: null, irq: null, ...resolved } },
  })
}

describe('PinoutDiagram — warnings', () => {
  it('shows no warning for a valid wiring', () => {
    const { container } = renderDiagram({ reset: 20, cs: 4 })

    expect(container.querySelector('.error')).toBeNull()
  })

  it('warns when two lines share a header pin', () => {
    renderDiagram({ reset: 4, cs: 4 })

    expect(screen.getByText('Several lines share the same header pin.')).toBeInTheDocument()
  })

  it('warns when a GPIO is not on the 40-pin header', () => {
    renderDiagram({ irq: 30 })

    expect(screen.getByText('GPIO30 (irq) is not on the 40-pin header.')).toBeInTheDocument()
  })
})
