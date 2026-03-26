import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { UploadZone } from '../components/UploadZone'
import { PackageStatusBadge } from '../components/PackageStatusBadge'
import { listPackages, uploadPackage, deletePackage } from '../api/packages'
import type { Package } from '../types'

export function DashboardPage() {
  const [packages, setPackages] = useState<Package[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = useCallback(async () => {
    try {
      setPackages(await listPackages())
    } catch {
      setError('Не удалось загрузить список пакетов')
    }
  }, [])

  useEffect(() => {
    load()
    // Poll while any package is in-flight
    const interval = setInterval(() => {
      setPackages((prev) => {
        if (prev.some((p) => p.status === 'received' || p.status === 'processing')) {
          load()
        }
        return prev
      })
    }, 3000)
    return () => clearInterval(interval)
  }, [load])

  async function handleUpload(file: File) {
    setError('')
    setUploading(true)
    try {
      const pkg = await uploadPackage(file)
      setPackages((prev) => [pkg, ...prev])
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      setError(status === 413 ? 'Файл превышает 50 МБ' : 'Ошибка загрузки файла')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm('Удалить пакет?')) return
    await deletePackage(id)
    setPackages((prev) => prev.filter((p) => p.id !== id))
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Пакеты документов</h1>
          <p className="text-sm text-gray-500 mt-1">Загружайте залоговые договоры для автоматического анализа</p>
        </div>

        <UploadZone onUpload={handleUpload} uploading={uploading} />

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {packages.length === 0 ? (
          <p className="text-center text-sm text-gray-400 py-8">Нет загруженных документов</p>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Файл</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Точность</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Дата</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {packages.map((pkg) => (
                  <tr
                    key={pkg.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/packages/${pkg.id}`)}
                  >
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">
                      {pkg.filename}
                    </td>
                    <td className="px-4 py-3">
                      <PackageStatusBadge status={pkg.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {pkg.accuracy != null ? `${Math.round(pkg.accuracy * 100)}%` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(pkg.created_at).toLocaleDateString('ru-RU')}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {pkg.status !== 'processing' && pkg.status !== 'received' && (
                        <button
                          onClick={(e) => handleDelete(pkg.id, e)}
                          className="text-gray-400 hover:text-red-600 text-xs"
                        >
                          Удалить
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}
