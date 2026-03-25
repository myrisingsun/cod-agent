import type { PackageStatus } from '../types'

const CONFIG: Record<PackageStatus, { label: string; className: string }> = {
  received:   { label: 'Получен',    className: 'bg-gray-100 text-gray-600' },
  processing: { label: 'Обработка',  className: 'bg-blue-100 text-blue-700 animate-pulse' },
  parsed:     { label: 'Распознан',  className: 'bg-purple-100 text-purple-700' },
  done:       { label: 'Готово',     className: 'bg-green-100 text-green-700' },
  error:      { label: 'Ошибка',     className: 'bg-red-100 text-red-700' },
}

export function PackageStatusBadge({ status }: { status: PackageStatus }) {
  const { label, className } = CONFIG[status] ?? CONFIG.error
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>
      {label}
    </span>
  )
}
