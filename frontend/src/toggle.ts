// <tag-toggle>: an on/off control without a checkbox. It keeps a checkbox's
// API (checked, disabled, indeterminate, a bubbling "change"), so dialogs read
// it the same way. Shows its state itself:
//   default    a pill holding its label; off is dim and struck through
//   kind="x"   a discreet ✕ that leaves its row out (↺ puts it back); the row
//              is struck through by CSS
// Hovering says what a click does, unless the element has its own title.
class TagToggle extends HTMLElement {
  static observedAttributes = ['checked', 'disabled', 'indeterminate']
  private own: string | null = null

  connectedCallback() {
    this.own ??= this.getAttribute('title')
    this.setAttribute('role', 'button')
    if (!this.hasAttribute('tabindex')) this.tabIndex = 0
    this.addEventListener('click', this.flip)
    this.addEventListener('keydown', this.key)
    this.sync()
  }
  disconnectedCallback() {
    this.removeEventListener('click', this.flip)
    this.removeEventListener('keydown', this.key)
  }
  attributeChangedCallback() { this.sync() }

  get checked() { return this.hasAttribute('checked') }
  set checked(v: boolean) { this.toggleAttribute('checked', !!v) }
  get disabled() { return this.hasAttribute('disabled') }
  set disabled(v: boolean) { this.toggleAttribute('disabled', !!v) }
  get indeterminate() { return this.hasAttribute('indeterminate') }
  set indeterminate(v: boolean) { this.toggleAttribute('indeterminate', !!v) }

  private flip = (e: Event) => {
    e.stopPropagation()
    if (this.disabled) return
    this.indeterminate = false
    this.checked = !this.checked
    this.dispatchEvent(new Event('change', { bubbles: true }))
  }
  private key = (e: KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); this.flip(e) }
  }

  private sync() {
    const on = this.checked
    this.setAttribute('aria-pressed', this.indeterminate ? 'mixed' : String(on))
    this.setAttribute('aria-disabled', String(this.disabled))
    if (this.getAttribute('kind') === 'x') {
      this.textContent = on ? '✕' : '↺'
      this.title = this.own ?? (on ? 'Leave this out' : 'Put this back')
    } else {
      const name = (this.textContent ?? '').trim()
      this.title = this.own ?? (on ? `${name}: on — click to turn off` : `${name}: off — click to turn on`)
    }
  }
}

if (!customElements.get('tag-toggle')) customElements.define('tag-toggle', TagToggle)

declare global {
  interface HTMLElementTagNameMap { 'tag-toggle': TagToggle }
}
export type { TagToggle }
