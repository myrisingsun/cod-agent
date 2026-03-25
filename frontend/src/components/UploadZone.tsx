import { useState, DragEvent, ChangeEvent, useRef } from 'react'

interface Props {
  onUpload: (file: File) => Promise<void>
  uploading: boolean
}

export function UploadZone({ onUpload, uploading }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file?.type === 'application/pdf') onUpload(file)
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
    e.target.value = ''
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
        dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      } ${uploading ? 'opacity-50 cursor-wait' : ''}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleChange}
      />
      <div className="text-4xl mb-3">📄</div>
      {uploading ? (
        <p className="text-sm text-gray-600">Загрузка...</p>
      ) : (
        <>
          <p className="text-sm font-medium text-gray-700">
            Перетащите PDF или нажмите для выбора
          </p>
          <p className="text-xs text-gray-400 mt-1">Максимум 50 МБ</p>
        </>
      )}
    </div>
  )
}
