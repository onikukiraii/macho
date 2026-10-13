const DEFAULT_TITLE = 'レスト終了'

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

// iOS は push を受けて通知を出さないと購読を取り消すため、data が無いときや JSON でないときも通知を出す
function readPushMessage(data) {
  try {
    return data.json()
  } catch {
    return { title: DEFAULT_TITLE, body: '' }
  }
}

self.addEventListener('push', (event) => {
  const { title, body } = readPushMessage(event.data)
  event.waitUntil(self.registration.showNotification(title, { body, icon: '/icons/icon-192.png' }))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      const [windowClient] = windowClients
      return windowClient === undefined ? self.clients.openWindow('/') : windowClient.focus()
    }),
  )
})
