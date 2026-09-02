# tbki-radar

Монитор обновлений фронтенда Т-БКИ (bug bounty program, Standoff 365).

Каждые 3 часа (GitHub Actions cron) проверяет JS-бандл кабинета
`account.tbki.ru`. При изменении — извлекает новые пути вида `/api/...`
и шлёт уведомление в Telegram.

Запросы выполняются с заголовком `X-Bug-Bounty: ScopeSova` в рамках
правил программы (2 GET-запроса на запуск, лимит программы — 5 rps).

## Структура

- `checker.py` — скачивание бандла, хэш, дифф путей, отправка в ТГ
- `.github/workflows/radar.yml` — расписание и запуск
- `state.json` — состояние (хэш, список путей), обновляется коммитом из workflow

## Настройка

Секреты репозитория:

- `TELEGRAM_BOT_TOKEN` — токен бота из @BotFather
- `TELEGRAM_CHAT_ID` — твой chat_id

Ручной запуск: Actions → radar → Run workflow.
