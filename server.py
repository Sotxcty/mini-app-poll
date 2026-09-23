import os
from flask import Flask, request, jsonify
import requests
import hashlib
import hmac

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

def check_hash(data_init, raw_data):
    secret_key = hmac.new(
        b'WebAppData',
        msg=BOT_TOKEN.encode(),
        digestmod=hashlib.sha256
    ).digest()
    h = hmac.new(secret_key, msg=raw_data.encode(), digestmod=hashlib.sha256)
    return h.hexdigest()

@app.route('/receive-answer', methods=['POST'])
def receive_answer():
    data = request.json
    init_data = data.get('init_data')
    
    # Проверка подписи (если есть init_data)
    if init_data:
        # Извлекаем только поля кроме init_data и сортируем
        raw_pairs = [f"{k}={v}" for k, v in sorted(data.items()) if k != 'init_data']
        raw_data = '\n'.join(raw_pairs)
        
        # Достаём хеш из init_data
        try:
            hash_part = init_data.split('hash=')[1].split('&')[0]
        except IndexError:
            return jsonify({'status': 'error', 'msg': 'Invalid init_data'}), 403
        
        if check_hash(init_data, raw_data) != hash_part:
            # Для теста можно закомментировать эту строку, чтобы видеть ответы даже без проверки
            return jsonify({'status': 'error', 'msg': 'Signature mismatch'}), 403

    user = data.get('user', {})
    answers = '\n'.join(f"{k}: {v}" for k, v in data.items() if k not in ['init_data', 'user'])
    
    text = (
        f"📬 <b>Новый ответ на опрос!</b>\n\n"
        f"👤 <b>Пользователь:</b> {user.get('first_name', 'Неизвестно')} (@{user.get('username', 'нет')})\n"
        f"🆔 <b>ID:</b> <code>{user.get('id', 'нет')}</code>\n\n"
        f"📝 <b>Ответы:</b>\n{answers}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    requests.post(url, json=payload)

    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
