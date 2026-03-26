import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { PackageStatusBadge } from '../components/PackageStatusBadge'
import { ExtractionTable } from '../components/ExtractionTable'
import { ChatWindow } from '../components/ChatWindow'
import { getPackage } from '../api/packages'
import { getExtraction, retryExtraction } from '../api/extraction'
import type { Package, ExtractionResult } from '../types'

const POLL_INTERVAL = 3000
const TERMINAL_STATUSES = new Set(['done', 'error'])

export function PackageDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [pkg, setPkg] = useState<Package | null>(null)
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null)
  const [loadingRetry, setLoadingRetry] = useState(false)
  const [error, setError] = useState('')

  const loadExtraction = useCallback(async (packageId: string) => {
    try {
      setExtraction(await getExtraction(packageId))
    } catch {
      setExtraction(null)
    }
  }, [])

  const loadPackage = useCallback(async () => {
    if (!id) return
    try {
      const p = await getPackage(id)
      setPkg(p)
      if (p.status === 'done') loadExtraction(id)
    } catch {
      setError('Пакет не найден')
    }
  }, [id, loadExtraction])

  useEffect(() => {
    loadPackage()
  }, [loadPackage])

  // Poll until terminal status
  useEffect(() => {
    if (!pkg || TERMINAL_STATUSES.has(pkg.status)) return
    const timer = setInterval(loadPackage, POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [pkg, loadPackage])

  async function handleRetry() {
    if (!id) return
    setLoadingRetry(true)
    try {
      await retryExtraction(id)
      await loadPackage()
    } catch {
      setError('Не удалось запустить повторную обработку')
    } finally {
      setLoadingRetry(false)
    }
  }

  if (error) {
    return (
      <Layout>
        <div className="text-center py-16">
          <p className="text-red-600 mb-4">{error}</p>
          <button onClick={() => navigate('/')} className="text-sm text-blue-600 hover:underline">
            ← Назад
          </button>
        </div>
      </Layout>
    )
  }

  if (!pkg) {
    return (
      <Layout>
        <div className="text-center py-16 text-gray-400 text-sm">Загрузка...</div>
      </Layout>
    )
  }

  const isProcessing = !TERMINAL_STATUSES.has(pkg.status)

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-gray-900 mb-1 block">
              ← Все пакеты
            </button>
            <h1 className="text-xl font-semibold text-gray-900 break-all">{pkg.filename}</h1>
            <div className="flex items-center gap-3 mt-2">
              <PackageStatusBadge status={pkg.status} />
              {pkg.accuracy != null && (
                <span className="text-sm text-gray-500">
                  Средняя точность: {Math.round(pkg.accuracy * 100)}%
                </span>
              )}
            </div>
          </div>
          {pkg.status === 'error' && (
            <button
              onClick={handleRetry}
              disabled={loadingRetry}
              className="bg-orange-500 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-orange-600 disabled:opacity-50"
            >
              {loadingRetry ? 'Запуск...' : 'Повторить обработку'}
            </button>
          )}
        </div>

        {/* Processing indicator */}
        {isProcessing && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-4 flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-blue-700">
              Документ обрабатывается — извлечение полей и индексирование...
            </p>
          </div>
        )}

        {/* Extraction results */}
        {pkg.status === 'done' && pkg.document_type !== 'not_pledge' && extraction && (
          <div>
            <h2 className="text-base font-semibold text-gray-900 mb-3">
              Извлечённые поля
              <span className="ml-2 text-xs font-normal text-yellow-600">
                🟡 — уверенность ниже 70%
              </span>
            </h2>
            <ExtractionTable fields={extraction.fields} confidence={extraction.confidence} />
          </div>
        )}

        {pkg.status === 'done' && pkg.document_type === 'not_pledge' && (
          <div className="bg-yellow-50 border border-yellow-300 rounded-xl px-4 py-4 text-sm text-yellow-800">
            <strong>Документ не является залоговым договором.</strong> Модель не обнаружила характерных
            полей: залогодержатель, залогодатель, предмет залога, кадастровый номер.
            Загрузите корректный договор залога недвижимости.
          </div>
        )}

        {pkg.status === 'error' && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-4 text-sm text-red-700">
            Ошибка при обработке документа. Проверьте формат файла и попробуйте снова.
          </div>
        )}

        {/* Q&A Chat */}
        {pkg.status === 'done' && pkg.document_type !== 'not_pledge' && (
          <div>
            <h2 className="text-base font-semibold text-gray-900 mb-3">Вопросы по документу</h2>
            <ChatWindow packageId={pkg.id} />
          </div>
        )}
      </div>
    </Layout>
  )
}
