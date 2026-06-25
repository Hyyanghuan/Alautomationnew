import requests
TOKEN = "8814614671:AAHm6YWqd89xYWhKpMgWZPtTd6yMVErXVEI"
# 群公开用户名 @testgroup
res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getChat", params={"chat_id":"@test_yh615_01_bot"})
print(res.json())
