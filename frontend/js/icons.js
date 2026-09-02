/**
 * icons.js | AcademicGuard SVG Icon Renderer
 * Provides helper functions to inject cohesive SVG icons into the DOM.
 */

const AgIcons = (() => {
  const SPRITE_URL = '/assets/icons.svg';

  /**
   * Return an SVG HTML string referencing an icon symbol from the sprite.
   * @param {string} name - Icon symbol name (e.g. 'shield-check', 'ag-shield-check')
   * @param {object} [options] - Configuration options { size: 'sm'|'md'|'lg', className: '' }
   * @returns {string} SVG HTML markup
   */
  function render(name, options = {}) {
    const symbolId = name.startsWith('ag-') ? name : `ag-${name}`;
    const sizeClass = options.size ? `ag-icon-${options.size}` : '';
    const extraClass = options.className || '';
    const ariaHidden = options.ariaLabel ? '' : 'aria-hidden="true"';
    const ariaLabel = options.ariaLabel ? `aria-label="${options.ariaLabel}" role="img"` : '';

    return `<svg class="ag-icon ${sizeClass} ${extraClass}" ${ariaHidden} ${ariaLabel}><use href="${SPRITE_URL}#${symbolId}"></use></svg>`;
  }

  /**
   * Scan the DOM and replace elements matching `[data-ag-icon]` with inline SVG icon references.
   * Example: `<span data-ag-icon="dashboard" data-size="sm"></span>`
   */
  function replaceIcons(root = document) {
    const elements = root.querySelectorAll('[data-ag-icon]');
    elements.forEach(el => {
      const name = el.getAttribute('data-ag-icon');
      const size = el.getAttribute('data-size') || '';
      const cls = el.className || '';
      const aria = el.getAttribute('aria-label') || '';
      el.outerHTML = render(name, { size, className: cls, ariaLabel: aria });
    });
  }

  return {
    render,
    replaceIcons,
  };
})();

// Auto-run on DOMContentLoaded if DOM is loaded
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    AgIcons.replaceIcons();
  });
}

// Export for module/global environments
if (typeof window !== 'undefined') {
  window.AgIcons = AgIcons;
}
