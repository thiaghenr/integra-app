
Create a new bot-specific enriched endpoint for the WhatsApp chatbot.

Follow ALL rules from CLAUDE.md section "Bot-specific API Routes (/api/v1/bot/)".

Steps to execute:

1. Add the route in `app/routers/api/v1/bot.py`
2. Create a new `Bot*Read` schema in `app/backend/schemas/bot.py`
3. Reuse existing repositories/services — never modify them
4. Enrich the response with joins in `app/backend/services/bot_service.py`
5. Update the Bot-specific API Routes table in `CLAUDE.md`
6. Confirm no existing files were modified except `bot.py`, `bot_service.py`, `schemas/bot.py` and `CLAUDE.md`

The endpoint to create: $ARGUMENTS
