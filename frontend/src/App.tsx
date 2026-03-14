const cardStyle = {
  maxWidth: '720px',
  margin: '0 auto',
  padding: '32px',
  borderRadius: '24px',
  background: 'rgba(255, 255, 255, 0.88)',
  boxShadow: '0 24px 80px rgba(15, 23, 42, 0.18)',
}

const badgeStyle = {
  display: 'inline-block',
  padding: '6px 12px',
  borderRadius: '999px',
  background: '#d1fae5',
  color: '#065f46',
  fontSize: '12px',
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase' as const,
}

export default function App() {
  return (
    <main
      style={{
        minHeight: '100vh',
        padding: '48px 20px',
        background:
          'radial-gradient(circle at top, #fde68a 0%, #fef3c7 22%, #fff7ed 55%, #fffbeb 100%)',
        fontFamily: 'Segoe UI, sans-serif',
        color: '#111827',
      }}
    >
      <section style={cardStyle}>
        <span style={badgeStyle}>Frontend online</span>
        <h1 style={{ fontSize: 'clamp(2rem, 4vw, 3.6rem)', margin: '18px 0 12px' }}>
          JMIE React frontend running in Docker
        </h1>
        <p style={{ fontSize: '1.05rem', lineHeight: 1.7, color: '#374151', marginBottom: '24px' }}>
          This container is serving the frontend with Vite in development mode. Once the real UI files are added,
          this page will be replaced by the application.
        </p>
        <div style={{ display: 'grid', gap: '12px' }}>
          <a href="http://localhost:8000/docs" style={{ color: '#1d4ed8', fontWeight: 600 }}>
            Open FastAPI docs
          </a>
          <a href="http://localhost:8000/health" style={{ color: '#1d4ed8', fontWeight: 600 }}>
            Check API health endpoint
          </a>
        </div>
      </section>
    </main>
  )
}