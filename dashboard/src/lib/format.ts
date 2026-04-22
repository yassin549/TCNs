import { formatDistanceToNowStrict } from 'date-fns'

export function formatCurrency(value: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatCompactNumber(value: number) {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

export function formatPercent(value: number, digits = 2) {
  return `${value.toFixed(digits)}%`
}

export function formatSigned(value: number, digits = 2) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`
}

export function formatSignedPercent(value: number, digits = 2) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function formatFreshness(value: string) {
  return `${formatDistanceToNowStrict(new Date(value), { addSuffix: true })}`
}

