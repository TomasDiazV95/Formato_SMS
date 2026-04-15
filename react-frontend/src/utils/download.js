const EXCEL_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
export const ZIP_MIME = 'application/zip'

export function triggerDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

const cleanText = text => text.replace(/\s+/g, ' ').trim()

const extractMessageFromHtml = html => {
  if (typeof window !== 'undefined' && typeof window.DOMParser !== 'undefined') {
    try {
      const parser = new window.DOMParser()
      const doc = parser.parseFromString(html, 'text/html')
      const alertNode = doc.querySelector('.alert')
      if (alertNode?.textContent) return cleanText(alertNode.textContent)
      const title = doc.querySelector('title')?.textContent
      if (title) return cleanText(title)
      return cleanText(doc.body?.textContent || '')
    } catch (_) {
      // fallback to regex parse below
    }
  }
  const flashMatch = html.match(/<div[^>]*class="[^"]*alert[^"]*"[^>]*>([\s\S]*?)<\/div>/i)
  if (flashMatch) {
    return cleanText(flashMatch[1].replace(/<[^>]+>/g, ' '))
  }
  return cleanText(html)
}

const extractMessageFromBlob = async blob => {
  if (!blob) return ''
  try {
    if (typeof blob.text !== 'function') return ''
    const text = await blob.text()
    if (!text) return ''
    const trimmed = text.trim()
    if (trimmed.startsWith('{')) {
      try {
        const parsed = JSON.parse(trimmed)
        if (parsed?.message) return parsed.message
        if (parsed?.detail) return parsed.detail
      } catch (_) {
        // ignore JSON parse errors, fallback to HTML/text parsing
      }
    }
    if (/<html|<!doctype/i.test(trimmed)) {
      return extractMessageFromHtml(trimmed)
    }
    return cleanText(trimmed)
  } catch (_) {
    return ''
  }
}

export async function assertExcelResponse(response, defaultMessage = 'El backend devolvió un error.', extraAllowedTypes = []) {
  if (!response) throw new Error(defaultMessage)
  const status = typeof response.status === 'number' ? response.status : 200
  if (status >= 400) {
    const message = await extractMessageFromBlob(response.data)
    throw new Error(message || defaultMessage)
  }
  const allowed = [EXCEL_MIME, ...(extraAllowedTypes || [])].map(type => type?.toLowerCase()).filter(Boolean)
  const contentType = (response.headers?.['content-type'] || '').toLowerCase()
  if (allowed.some(type => contentType.includes(type))) return
  const blobType = (response.data && response.data.type) ? response.data.type.toLowerCase() : ''
  if (allowed.some(type => blobType.includes(type))) return
  const message = await extractMessageFromBlob(response.data)
  throw new Error(message || defaultMessage)
}
