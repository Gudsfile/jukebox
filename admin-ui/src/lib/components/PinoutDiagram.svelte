<script>
  import pinoutImage from '../../assets/raspberry-pi-gpio-pinout.webp'
  import { BCM_TO_PHYSICAL, wiringFor } from '../pn532/pinout.js'

  // onPinClick(bcm) is optional: when given, every GPIO pin of the header becomes clickable.
  let { profile, resolved, onPinClick = null } = $props()

  // Pin centres measured on the 2064×1185 source image.
  const IMAGE = { width: 2064, height: 1185 }
  const COLUMN_X = [1373, 1414]
  const FIRST_ROW_Y = 176
  const ROW_STEP = 43.84

  function centre(physical) {
    const index = physical - 1
    return { x: COLUMN_X[index % 2], y: FIRST_ROW_Y + Math.floor(index / 2) * ROW_STEP }
  }

  let wiring = $derived(wiringFor(profile, resolved))
  let anyPower = $derived(wiring.wired.some((pin) => pin.anyOf))
  // Two lines on one physical pin (e.g. CS and RST both on GPIO4) is a wiring error.
  let clashes = $derived(
    new Set(wiring.wired.map((pin) => pin.physical).filter((physical, i, all) => all.indexOf(physical) !== i)),
  )
</script>

<figure class="pinout">
  <div class="pinout-canvas">
    <img src={pinoutImage} alt="Raspberry Pi 40-pin GPIO header" />
    <svg viewBox={`0 0 ${IMAGE.width} ${IMAGE.height}`} aria-hidden="true">
      {#each wiring.wired as pin (`${pin.label}-${pin.physical}`)}
        {@const { x, y } = centre(pin.physical)}
        {@const right = pin.physical % 2 === 0}
        <g
          class={`pin pin-${pin.kind}`}
          class:pin-clash={clashes.has(pin.physical) || wiring.claimed.some(({ bcm }) => bcm === pin.bcm)}
          class:pin-any={pin.anyOf}
        >
          <circle cx={x} cy={y} r="19" />
          <text x={right ? x + 34 : x - 34} y={y + 9} text-anchor={right ? 'start' : 'end'}>{pin.label}</text>
        </g>
      {/each}
      {#if onPinClick}
        {#each Object.entries(BCM_TO_PHYSICAL) as [bcm, physical] (bcm)}
          {@const { x, y } = centre(physical)}
          <!-- Mouse shortcut only: the svg is aria-hidden and every pin is set through the form's text inputs. -->
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
          <circle class="hit" cx={x} cy={y} r="20" onclick={() => onPinClick(Number(bcm))}>
            <title>GPIO{bcm} · pin {physical}</title>
          </circle>
        {/each}
      {/if}
    </svg>
  </div>
  <figcaption>
    <ul class="legend">
      <li><span class="swatch pin-signal"></span>Configurable (CS, RST, IRQ)</li>
      <li><span class="swatch pin-bus"></span>SPI bus</li>
      <li>
        <span class="swatch pin-power" class:pin-any={anyPower}></span>Power{anyPower ? ' (any one of each)' : ''}
      </li>
    </ul>
    {#if clashes.size}
      <p class="error">Several lines share the same header pin.</p>
    {/if}
    {#each wiring.claimed as { key, bcm, name } (key)}
      <p class="error">
        GPIO{bcm} ({key}) is {name}, already claimed by the kernel SPI driver: probing fails with GPIO busy.
      </p>
    {/each}
    {#each wiring.unmapped as { key, bcm } (key)}
      <p class="error">GPIO{bcm} ({key}) is not on the 40-pin header.</p>
    {/each}
    <small
      >Diagram © Raspberry Pi Ltd, <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.</small
    >
  </figcaption>
</figure>

<style>
  .pinout {
    margin: 0;
  }
  .pinout-canvas {
    position: relative;
    max-width: 900px;
    background: #fff;
    border-radius: 6px;
  }
  .pinout-canvas img,
  .pinout-canvas svg {
    display: block;
    width: 100%;
    height: auto;
  }
  .pinout-canvas svg {
    position: absolute;
    inset: 0;
  }
  .hit {
    fill: transparent;
    cursor: pointer;
  }
  .hit:hover {
    fill: color-mix(in srgb, var(--accent) 35%, transparent);
  }
  .pin circle {
    fill: none;
    stroke-width: 7;
  }
  .pin text {
    font: 700 30px var(--sans);
    paint-order: stroke;
    stroke: #fff;
    stroke-width: 8;
  }
  .pin-signal {
    --pin: var(--accent);
  }
  .pin-bus {
    --pin: var(--state-known);
  }
  .pin-power {
    --pin: var(--state-unknown);
  }
  .pin-any circle {
    stroke-dasharray: 9 6;
  }
  .swatch.pin-any {
    border-style: dashed;
  }
  .pin-clash {
    --pin: var(--danger);
  }
  .pin circle {
    stroke: var(--pin);
  }
  .pin text {
    fill: var(--pin);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    padding: 0;
    list-style: none;
  }
  .swatch {
    display: inline-block;
    width: 0.8em;
    height: 0.8em;
    margin-right: 0.4em;
    border-radius: 50%;
    border: 3px solid var(--pin);
  }
</style>
