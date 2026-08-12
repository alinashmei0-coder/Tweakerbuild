# Twaeker Telegram → GitHub Actions → DeepSeek

Minimal prototype:

Telegram Bot → GitHub Actions → DeepSeek → generated files → Theos build → Telegram

## What you configure

1. Create a GitHub repository from this folder.
2. Add these GitHub repository secrets:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
   - DEEPSEEK_API_KEY
3. Edit `config.json` and set your Telegram bot token placeholder only if you choose local polling.
4. Put your GitHub token in the GitHub repository secret `GH_PAT` if the workflow must dispatch another workflow or call the GitHub API.

## Important architecture note

A pure GitHub Actions workflow cannot continuously receive Telegram updates without a webhook host or polling process. This prototype therefore uses Telegram's Bot API through a GitHub Actions polling workflow.

For testing, the polling workflow can be scheduled frequently, but GitHub Actions is not a real-time server and scheduled jobs have latency. The workflow stores the Telegram update offset in a repository variable called `TELEGRAM_OFFSET`.

A simpler first test is to manually run the workflow and provide the Telegram request as an input. The Telegram bridge is included for the intended UX.

## Files

- `.github/workflows/telegram-bot.yml`: polls Telegram and dispatches build jobs.
- `.github/workflows/build-tweak.yml`: calls DeepSeek, writes files, and builds with Theos.
- `scripts/telegram_poll.py`: reads Telegram messages and dispatches the build workflow.
- `scripts/send_telegram.py`: sends progress/results.
- `scripts/deepseek_generate.py`: asks DeepSeek for project files.
- `scripts/build_project.py`: writes the generated project safely.

## Security

Never commit bot tokens or API keys.

The bot is intentionally a prototype. Do not expose a privileged GitHub token in chat messages.

The example build target is a harmless test tweak. Requests that require proprietary symbols, private headers, bypasses, or unsupported APIs may need user-supplied headers and manual verification.

## First test

Run `telegram-bot.yml` manually from GitHub Actions. Send the bot:

`Create a harmless test tweak that logs a message when the target application starts.`

Then check the Actions run and the Telegram response.
