# Sprint 6 — Frontend (React + Vite + TypeScript)

## Что реализовано

### Стек
- **React 18** + **TypeScript** + **Vite 5**
- **TailwindCSS 3** — утилитарная стилизация
- **React Router 6** — клиентская маршрутизация
- **Axios** — HTTP-клиент с JWT interceptor

### Структура (`frontend/src/`)
```
api/          — API-клиент (auth, packages, extraction, chat)
context/      — AuthContext (глобальное состояние пользователя)
types/        — TypeScript-типы, зеркалящие схемы бэкенда
pages/        — страницы приложения
components/   — переиспользуемые компоненты
```

### Страницы

| Маршрут | Страница | Описание |
|---|---|---|
| `/login` | LoginPage | Форма входа, JWT access token в памяти |
| `/register` | RegisterPage | Регистрация + авто-вход |
| `/` | DashboardPage | Список пакетов, загрузка PDF, polling статуса |
| `/packages/:id` | PackageDetailPage | Поля + chat |

### Компоненты

| Компонент | Описание |
|---|---|
| `Layout` | Шапка с email пользователя и кнопкой выхода |
| `ProtectedRoute` | Редирект на `/login` если нет токена |
| `UploadZone` | Drag-and-drop зона загрузки PDF (50 МБ) |
| `PackageStatusBadge` | Цветные бейджи статусов (received/processing/done/error) |
| `ExtractionTable` | 10 полей + confidence, **жёлтая подсветка < 70%** |
| `ChatWindow` | Q&A чат с историей и раскрывающимися источниками |

### Auth + JWT
- Access token хранится **в памяти** (не localStorage — защита от XSS)
- Refresh token — httpOnly cookie, устанавливается бэкендом
- При монтировании: авто-восстановление сессии через `/auth/refresh`
- На 401: interceptor запрашивает новый токен и повторяет запрос
- Параллельные запросы при refresh ставятся в очередь

### Polling
- Dashboard: опрашивает список каждые 3 сек пока есть пакеты в `received|processing`
- PackageDetail: опрашивает статус пакета каждые 3 сек до `done|error`

### Сборка
```bash
cd frontend
npm install
npm run build   # tsc + vite build → dist/
npm run dev     # dev server на :3000 с proxy на app:8080
```

Production bundle: **220 кБ JS** (gzip: 73 кБ), **14 кБ CSS** (gzip: 3 кБ).
