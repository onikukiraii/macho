self.addEventListener('push', (event) => {
  const { title, body } = event.data.json()
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
