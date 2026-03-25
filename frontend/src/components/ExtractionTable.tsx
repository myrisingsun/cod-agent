import type { PledgeFields, FieldConfidence } from '../types'

const FIELD_LABELS: Record<keyof PledgeFields, string> = {
  contract_number:  'Номер договора',
  contract_date:    'Дата договора',
  pledgee:          'Залогодержатель',
  pledgor:          'Залогодатель',
  pledgor_inn:      'ИНН залогодателя',
  pledge_subject:   'Предмет залога',
  cadastral_number: 'Кадастровый номер',
  area_sqm:         'Площадь, кв.м.',
  pledge_value:     'Залоговая стоимость',
  validity_period:  'Срок действия',
}

const LOW_CONFIDENCE = 0.7

interface Props {
  fields: PledgeFields
  confidence: FieldConfidence
}

export function ExtractionTable({ fields, confidence }: Props) {
  const keys = Object.keys(FIELD_LABELS) as (keyof PledgeFields)[]

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-600 w-48">Поле</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Значение</th>
            <th className="text-right px-4 py-3 font-medium text-gray-600 w-24">Уверенность</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {keys.map((key) => {
            const value = fields[key]
            const conf = confidence[key as keyof FieldConfidence]
            const isLow = conf < LOW_CONFIDENCE
            const isEmpty = value == null || value === ''

            return (
              <tr
                key={key}
                className={isLow && !isEmpty ? 'bg-yellow-50' : ''}
              >
                <td className="px-4 py-3 font-medium text-gray-700">{FIELD_LABELS[key]}</td>
                <td className={`px-4 py-3 ${isEmpty ? 'text-gray-400 italic' : 'text-gray-900'}`}>
                  {isEmpty ? 'не найдено' : String(value)}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className={`text-xs font-medium ${
                    isEmpty       ? 'text-gray-300' :
                    isLow         ? 'text-yellow-600' :
                                    'text-green-600'
                  }`}>
                    {isEmpty ? '—' : `${Math.round(conf * 100)}%`}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
