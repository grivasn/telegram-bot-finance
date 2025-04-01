📊 Telegram Piyasa Özeti Botu Projesi
Bu proje, Python, yFinance ve Telegram Bot API kullanarak günlük piyasa verilerini Telegram üzerinden kullanıcılara ileten bir bot uygulamasıdır. Bot, BIST endeksleri, döviz kurları, değerli metaller (Altın, Gümüş) ve kripto para birimleri (Bitcoin, Ethereum) gibi piyasa verilerini kullanıcılarla paylaşır.

📌 Proje Özeti
Projenin amacı, kullanıcılara günlük piyasa özetini hızlı bir şekilde sunmak. Telegram botu kullanılarak veriler, kullanıcıların chat ID'lerine gönderilir. Bot, belirli piyasa araçları hakkında bilgi sunarak, fiyat değişim oranlarıyla birlikte bir özet oluşturur.

🛠️ Kullanılan Teknolojiler
Python: Uygulamanın ana programlama dili olarak kullanılmıştır.
yFinance: Piyasa verilerini almak için kullanılan Python kütüphanesidir.
Telegram Bot API: Kullanıcılarla etkileşim sağlamak ve mesaj göndermek için Telegram’ın bot API'si kullanılır.
JSON: Kullanıcıların chat ID bilgilerini saklamak için JSON formatında dosyalar kullanılır.

🚀 Özellikler
📈 Günlük Piyasa Özeti:
Bot, BIST100, BIST30, USD/TRY, EUR/TRY, Altın, Gümüş, Bitcoin ve Ethereum gibi finansal araçlar için günlük piyasa verilerini alır.
Fiyat değişim oranları hesaplanarak, olumlu ya da olumsuz değişimler emoji ile birlikte gösterilir.
🟢 Olumlu değişim
🔴 Olumsuz değişim
⚪️ Değişim yok
👥 Kullanıcı Yönetimi:
Bot, kullanıcıların chat ID'lerini kaydeder. Bunun için get_and_save_chat_ids() fonksiyonu kullanılır ve bu fonksiyon, Telegram API'si aracılığıyla kullanıcıların chat ID'lerini alarak bir dosyada saklar.
send_market_summary_to_all() fonksiyonu ise, kaydedilen chat ID'lerine piyasa özetini göndermek için kullanılır.

🖱️ Manuel Tetikleme:
Bot, belirli zamanlamalarla otomatik çalışmak yerine, manuel olarak tetiklenebilir.
Bu, terminal üzerinden botu çalıştırarak, piyasa verilerini tüm kullanıcılara göndermeyi sağlar.
app.py dosyasındaki bu fonksiyon, terminalden python main.py komutu ile çalıştırılabilir ve tüm kullanıcılar aynı anda bilgilendirilir.

📂 Dosya Yapısı
app.py: Botun ana mantığını içerir. Piyasa verilerini alır ve Telegram üzerinden kullanıcılarla paylaşır.
veritabani.py: Telegram bot token’ını içerir.
users.json: Bot ile etkileşimde bulunan kullanıcıların chat ID bilgilerini saklar.

📌 Notlar
🔑 Kullanıcı Ekleme: get_and_save_chat_ids() fonksiyonu, bot ile etkileşimde bulunan kullanıcıların chat ID bilgilerini toplar ve bu bilgiyi users.json dosyasına kaydeder.
📤 Piyasa Özeti Gönderme: send_market_summary_to_all() fonksiyonu, tüm kullanıcılara günlük piyasa özetini gönderir. Bu fonksiyon, botu çalıştırarak kullanıcılara verileri iletir.

