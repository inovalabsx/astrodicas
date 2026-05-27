"""Testa conexão com o bot Telegram e descobre IDs."""

import asyncio
import os
import sys

os.environ["TELEGRAM_BOT_TOKEN"] = "8951692868:AAFSLeIUC7eqUnafmewtcqgeA6bpo5-sOOM"
os.environ["TELEGRAM_CHANNEL_ID"] = "@astro_dicas"
os.environ["OPENAI_API_KEY"] = "sk-test"

sys.path.insert(0, "/bots/Projects/bot-signos")

from telegram import Bot
from telegram.error import TelegramError


async def test_bot():
    print("🔍 Testando bot Telegram...")
    token = "8951692868:AAFSLeIUC7eqUnafmewtcqgeA6bpo5-sOOM"
    
    bot = Bot(token=token)
    
    # Teste 1: getMe
    try:
        me = await bot.get_me()
        print(f"\n✅ Bot conectado: @{me.username} (ID: {me.id})")
        print(f"  Nome: {me.first_name}")
    except TelegramError as e:
        print(f"❌ Erro ao conectar: {e}")
        return
    
    # Teste 2: getUpdates
    try:
        updates = await bot.get_updates(limit=10)
        print(f"\n📨 Últimas {len(updates)} atualizações:")
        for u in updates:
            chat = u.effective_chat
            user = u.effective_user
            print(f"  Chat: {chat.type} | ID: {chat.id}")
            if chat.title:
                print(f"  Título: {chat.title}")
            if chat.username:
                print(f"  Username: @{chat.username}")
            if user:
                print(f"  User: {user.full_name} (@{user.username})")
            if u.message and u.message.text:
                print(f"  Msg: {u.message.text[:100]}")
            print()
    except TelegramError as e:
        print(f"  Info: {e}")
    
    # Teste 3: descobrir @astro_dicas
    try:
        chat_info = await bot.get_chat("@astro_dicas")
        print(f"\n📢 Canal @astro_dicas:")
        print(f"  ID: {chat_info.id}")
        print(f"  Tipo: {chat_info.type}")
        print(f"  Título: {chat_info.title}")
        print(f"  Pode postar: {chat_info.permissions.can_send_messages if chat_info.permissions else '?'}")
    except TelegramError as e:
        print(f"\n❌ Canal @astro_dicas: {e}")

    # Teste 4: enviar mensagem teste pro bot (DM)
    try:
        from_user = None
        updates = await bot.get_updates(limit=3)
        for u in updates:
            if u.effective_user and not u.effective_user.is_bot:
                from_user = u.effective_user
                break
        if from_user:
            await bot.send_message(chat_id=from_user.id, text="🌟 Olá! Sou o AstroDicas Bot. Meu canal é @astro_dicas! Teste OK ✅")
            print(f"\n📤 Mensagem teste enviada pra @{from_user.username} (ID: {from_user.id})")
            print("  ✅ Verifique seu Telegram!")
    except TelegramError as e:
        print(f"\n  Info: {e}")

    print("\n✅ Teste concluído!")

if __name__ == "__main__":
    asyncio.run(test_bot())
