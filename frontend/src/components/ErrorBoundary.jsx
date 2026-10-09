import { Component } from 'react'

export default class ErrorBoundary extends Component {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error, info) {
    console.error('A dashboard component failed to render.', error, info)
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="app-error-boundary" role="alert">
          <div className="card">
            <h1>The dashboard could not be displayed</h1>
            <p>Reload the application to restore the saved project workspace.</p>
            <button type="button" className="aws-inline-button" onClick={() => window.location.reload()}>
              Reload dashboard
            </button>
          </div>
        </main>
      )
    }
    return this.props.children
  }
}
