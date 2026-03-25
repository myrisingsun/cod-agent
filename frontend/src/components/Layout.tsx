import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    signOut()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-semibold text-gray-900 text-lg">
            КОД-агент
          </Link>
          {user && (
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user.email}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-500 hover:text-gray-900"
              >
                Выйти
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
