import telebot
import requests
import re
import urllib.parse
import hashlib
from telebot import types

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "*🤖 Бот работает в inline режиме!*\n\n"
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

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )

def get_image_hash(url):
    try:
        clean_url = url.split('?')[0].split('#')[0].lower().strip()
        return hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    except Exception:
        return hashlib.md5(url.encode('utf-8')).hexdigest()

def search_images(query, start_index=1, limit=50):
    encoded_query = urllib.parse.quote(query)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    cookies = {'SRCHHPGUSR': 'ADLT=OFF'}

    try:
        fetch_url = f"https://www.bing.com/images/search?q={encoded_query}&adlt=off&first={start_index}"
        response = requests.get(fetch_url, headers=headers, cookies=cookies, timeout=10)
        response.raise_for_status()
        
        links = re.findall(r'murl&quot;:&quot;(.*?)&quot;', response.text)
        
        unique_results = []
        seen_hashes = set()

        for link in links:
            if not link.startswith('http') or any(bad in link for bad in ['<', '>', '"', ' ']):
                continue

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
        print(f"Error: {e}")
        return []

@bot.inline_handler(lambda query: len(query.query) > 0)
def query_text(inline_query):
    try:
        query = inline_query.query
        offset = int(inline_query.offset) if inline_query.offset else 0
        
        image_data = search_images(query, start_index=offset + 1, limit=50)
        
        results = []
        for item in image_data:
            results.append(
                types.InlineQueryResultPhoto(
                    id=item['id'],
                    photo_url=item['url'],
                    thumbnail_url=item['url']
                )
            )

        next_offset = str(offset + len(image_data)) if len(image_data) > 0 else ""

        bot.answer_inline_query(
            inline_query.id, 
            results, 
            next_offset=next_offset, 
            cache_time=300
        )
    except Exception as e:
        print(f"Inline Error: {e}")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)



