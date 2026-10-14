import '@testing-library/jest-dom/vitest'

// jsdom は dialog の showModal と close を実装していない
HTMLDialogElement.prototype.showModal = function () {
  this.open = true
}
HTMLDialogElement.prototype.close = function () {
  this.open = false
}
