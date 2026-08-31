/**
 * Renders a model answer.
 *
 * Two constraints shape this. First, the text is generated, so it never reaches
 * `innerHTML`: everything below builds React elements, and a stray `<script>`
 * in an answer arrives on screen as the characters `<script>`. Second, answers
 * stream, so the markup has to be correct at every intermediate string — an
 * unterminated `**` is drawn as literal asterisks and quietly becomes bold once
 * its partner arrives, rather than flickering the paragraph in and out.
 *
 * The grammar is deliberately small: paragraphs, bullet and numbered lists,
 * bold, italic, inline code, and the `[1]` citation markers the RAG service
 * writes into the prose. Anything else is left as text.
 */

const BULLET = /^\s*[-*•]\s+/
const NUMBERED = /^\s*\d+[.)]\s+/
const HEADING = /^\s*#{1,6}\s+/

// One pass for all inline forms, so their delimiters cannot nest wrongly:
// citation marker | bold | italic | inline code.
const INLINE = /(\[\d+\])|(\*\*[^*\n]+\*\*)|(\*[^*\n]+\*)|(`[^`\n]+`)/g

function inline(text, key, onCite) {
  const out = []
  let last = 0
  let match

  INLINE.lastIndex = 0
  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > last) out.push(text.slice(last, match.index))
    const token = match[0]
    const id = `${key}-${match.index}`

    if (match[1]) {
      const n = Number(token.slice(1, -1))
      out.push(
        <button
          key={id}
          type="button"
          className="asst-cite"
          onClick={() => onCite?.(n)}
          aria-label={`Show source ${n}`}
        >
          {n}
        </button>,
      )
    } else if (match[2]) {
      out.push(<strong key={id}>{token.slice(2, -2)}</strong>)
    } else if (match[3]) {
      out.push(<em key={id}>{token.slice(1, -1)}</em>)
    } else {
      out.push(<code key={id}>{token.slice(1, -1)}</code>)
    }
    last = match.index + token.length
  }

  if (last < text.length) out.push(text.slice(last))
  return out
}

/** Groups lines into paragraphs and lists. Blank lines separate blocks. */
function blocks(source) {
  const result = []
  let list = null

  const closeList = () => {
    if (list) result.push(list)
    list = null
  }

  for (const raw of source.split('\n')) {
    const line = raw.trimEnd()

    if (!line.trim()) {
      closeList()
      continue
    }

    const kind = BULLET.test(line) ? 'ul' : NUMBERED.test(line) ? 'ol' : null
    if (kind) {
      if (list?.kind !== kind) {
        closeList()
        list = { kind, items: [] }
      }
      list.items.push(line.replace(kind === 'ul' ? BULLET : NUMBERED, ''))
      continue
    }

    closeList()
    if (HEADING.test(line)) {
      result.push({ kind: 'h', text: line.replace(HEADING, '') })
    } else {
      const previous = result[result.length - 1]
      // A hard-wrapped paragraph is one paragraph, not one per line.
      if (previous?.kind === 'p') previous.text += ` ${line.trim()}`
      else result.push({ kind: 'p', text: line.trim() })
    }
  }

  closeList()
  return result
}

export default function Answer({ text, streaming = false, onCite }) {
  const parsed = blocks(text)

  return (
    <div className="asst-answer">
      {parsed.map((block, i) => {
        if (block.kind === 'h') {
          return (
            <p key={i} className="asst-answer__h">
              {inline(block.text, `h${i}`, onCite)}
            </p>
          )
        }
        if (block.kind === 'p') {
          const last = streaming && i === parsed.length - 1
          return (
            <p key={i}>
              {inline(block.text, `p${i}`, onCite)}
              {last && <span className="asst-caret" aria-hidden="true" />}
            </p>
          )
        }
        const List = block.kind === 'ul' ? 'ul' : 'ol'
        return (
          <List key={i} className="asst-answer__list">
            {block.items.map((item, j) => (
              <li key={j}>{inline(item, `l${i}-${j}`, onCite)}</li>
            ))}
          </List>
        )
      })}
      {/* The caret belongs to the last paragraph, but an answer can open with a
          list — this keeps the pulse on screen in that case too. */}
      {streaming && parsed[parsed.length - 1]?.kind !== 'p' && (
        <span className="asst-caret" aria-hidden="true" />
      )}
    </div>
  )
}
