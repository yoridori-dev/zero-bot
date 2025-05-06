import random

completion_messages  = [
    "✅ いやぁー限界だったねぇ🥰おやんも🌙 {username} ",
    "✅ {username} すやぴしたの❔きゃわじゃん🥰また明日ね👋🏻",
    "✅ すーぐ寝るじゃん😪 {username} いい夢みろよ😘",
    "✅ え!? {username} どゆことぉ？寝たん？ねぇねぇ。",
]

def get_random_success_message(username):
    """移動完了メッセージをランダムで取得"""
    return random.choice(completion_messages ).replace("{username}", username)
