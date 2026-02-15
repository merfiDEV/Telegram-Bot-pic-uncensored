import asyncio
import re
import urllib.parse
import hashlib
import httpx
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineQuery, InlineQueryResultPhoto

logging.basicConfig(level=logging.INFO)

TOKEN = ''

bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_image_hash(url: str) -> str:
    try:
        clean_url = url.split('?')[0].split('#')[0].lower().strip()
        return hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    except Exception:
        return hashlib.md5(url.encode('utf-8')).hexdigest()

async def is_valid_image(client: httpx.AsyncClient, url: str) -> bool:
    try:
        if not any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            pass
            
        response = await client.head(url, timeout=2.0, follow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            return content_type.startswith('image/')
        return False
    except Exception:
        return False

async def search_images(query: str, start_index: int = 1, limit: int = 50):
    encoded_query = urllib.parse.quote(query)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    cookies = {'SRCHHPGUSR': 'ADLT=OFF'}

    try:
        fetch_url = f"https://www.bing.com/images/search?q={encoded_query}&adlt=off&first={start_index}"
        
        async with httpx.AsyncClient(headers=headers, cookies=cookies, timeout=10.0, follow_redirects=True) as client:
            response = await client.get(fetch_url)
            response.raise_for_status()
            
            links = re.findall(r'murl&quot;:&quot;(.*?)&quot;', response.text)
            
            unique_results = []
            seen_hashes = set()

            tasks = []
            potential_links = []

            for link in links:
                if not link.startswith('http') or any(bad in link for bad in ['<', '>', '"', ' ']):
                    continue
                potential_links.append(link)
                tasks.append(is_valid_image(client, link))
                if len(tasks) >= limit * 2:
                    break
            
            validity_results = await asyncio.gather(*tasks)

            for link, is_ok in zip(potential_links, validity_results):
                if is_ok:
                    img_hash = get_image_hash(link)
                    if img_hash not in seen_hashes:
                        seen_hashes.add(img_hash)
                        unique_results.append({
                            'url': link,
                            'id': img_hash
                        })
                
                if len(unique_results) >= limit:
                    break
            
            return unique_results
    except Exception as e:
        logging.error(f"Ошибка поиска: {e}")
        return []

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "*🤖 Бот работает в асинхронном inline режиме!*\n\n"
        "Чтобы использовать бота, откройте любой чат и введите:\n"
        "`@имя_бота ваш_запрос`\n\n"
        "⚠️ *Дисклеймер*\n\n"
        "Данный бот автоматически обрабатывает поисковые запросы пользователей и\n"
        "показывает результаты из *открытых источников* в интернете.\n\n"
        "*Создатель бота:*\n"
        "— не хранит контент\n"
        "— не загружает его на сервер\n"
        "— не контролирует и не модерирует поисковые запросы пользователей\n\n"
        "Вся ответственность за вводимые запросы и использование полученных материалов\n"
        "лежит *исключительно на пользователе*.\n\n"
        "Используя бота, вы подтверждаете, что:\n"
        "• соблюдаете законы своей страны\n"
        "• не используете бота для незаконных целей"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.inline_query(F.query.len() > 0)
async def inline_handler(inline_query: InlineQuery):
    try:
        query = inline_query.query
        offset = int(inline_query.offset) if inline_query.offset else 0
        
        image_data = await search_images(query, start_index=offset + 1, limit=30)
        
        results = []
        for item in image_data:
            results.append(
                InlineQueryResultPhoto(
                    id=item['id'],
                    photo_url=item['url'],
                    thumbnail_url=item['url']
                )
            )

        next_offset = str(offset + 30) if len(image_data) > 0 else ""

        await inline_query.answer(
            results=results,
            next_offset=next_offset,
            cache_time=60,
            is_personal=False
        )
    except Exception as e:
        logging.error(f"Inline Error: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
