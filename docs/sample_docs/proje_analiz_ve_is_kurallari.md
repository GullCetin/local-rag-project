# Proje Analiz Raporu ve İş Kuralları Şartnamesi (PRD & Business Rules)

## 1. Ana Sayfa Mimarisi ve Ekran Düzeni (Home Page Requirements)
Ana sayfa (Home Page) açıldığında yukarıdan aşağıya doğru sırasıyla şu bileşenler yer almalıdır:
- Üst Çubuk (App Header): Sol tarafta profil avatarı, ortada şirket logosu, sağ tarafta bildirim çanı ikonu.
- Arama Çubuğu (Search Bar): 44px yükseklik, 10px köşe yuvarlama, "Ürün, hizmet veya kategori ara..." placeholder metni.
- Carousel Banner: Otomatik kayan (auto-scroll: 5 saniye) promosyon banner alanı, 12px köşe yuvarlama.
- Hızlı Kategori Listesi (Category Grid): 4 sütunlu ızgara yapısında simge ve alt başlık içeren butonlar.
- Kampanyalar Bölümü: Yatay kaydırılabilir (horizontal scroll) kampanya kartları.
- Önerilen Ürünler / Hizmetler (Feed): 2 sütunlu dinamik yüklenen sonsuz kaydırma (infinite scroll) liste.
- Alt Navigasyon Çubuğu (Bottom Tab Bar): Ana Sayfa, Arama, Sepetim, Profilim olmak üzere 4 ana sekme.

## 2. Kullanıcı Girişi ve Güvenlik Kuralları (Authentication & Security)
- Parola Karmaşıklık Kuralı: En az 8 karakter uzunluğunda olmalı; en az 1 büyük harf, 1 küçük harf, 1 rakam ve 1 özel karakter içermelidir.
- Yanlış Giriş Sınırı (Max Login Retries): Üst üste 3 kez yanlış parola girildiğinde hesap 15 dakika boyunca kilitlenir (Account Lockout).
- İki Aşamalı Doğrulama (2FA / OTP): SMS ile gönderilen tek kullanımlık şifre (OTP) süresi 180 saniyedir (3 dakika).
- Oturum Zaman Aşımı: Kullanıcı işlem yapmadığında 30 gün boyunca "Beni Hatırla" seçeneğiyle oturum açık tutulur.

## 3. Sepet ve Sipariş İş Kuralları (Cart & Checkout Rules)
- Ücretsiz Kargo Limiti (Free Shipping Threshold): Sepet toplamı 500 TL ve üzeri olan siparişlerde kargo ücretsizdir. 500 TL altı siparişlerde standart 49.90 TL kargo ücreti yansıtılır.
- Maksimum Ürün Adedi: Kullanıcı aynı üründen tek siparişte en fazla 10 adet satın alabilir.
- Sepet Rezervasyon Süresi: Sepete eklenen ürünlerin stok rezervasyon süresi 30 dakikadır. 30 dakika içinde ödemeye geçilmezse sepet zaman aşımına uğrar.
- Ödeme Ağ Geçidi Zaman Aşımı (Payment Timeout): 3D Secure ödeme ekranında işlem süresi maksimum 45 saniyedir.

## 4. Sipariş Takip Durumları (Order Lifecycle)
Sipariş aşamaları sistemde şu sıra ile işletilir:
1. Sipariş Alındı (Order Placed / Pending)
2. Hazırlanıyor (Processing)
3. Kargoya Verildi (Shipped - Takip numarası ile SMS bildirimi)
4. Teslim Edildi (Delivered)
5. İptal / İade (Cancelled / Returned)
