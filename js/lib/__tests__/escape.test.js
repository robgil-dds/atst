import escape from '../escape'
describe('escape', () => {
  const htmlEscapes = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;',
  }
  it('should escape each character', () => {
    for (let [char, escapedChar] of Object.entries(htmlEscapes)) {
      expect(escape(char)).toBe(escapedChar)
    }
  })
  it('should escape multiple characters', () => {
    expect(escape('& and < and > and " and \' and /')).toBe(
      '&amp; and &lt; and &gt; and &quot; and &#x27; and &#x2F;'
    )
  })
})
