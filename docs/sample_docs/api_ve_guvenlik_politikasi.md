# API Mimarisi, Entegrasyon ve Güvenlik Politikası Kılavuzu

## 1. Kimlik Doğrulama ve Token Yönetimi (Authentication & JWT)
- Access Token Türü: JSON Web Token (JWT), RS256 algoritması ile asimetrik olarak imzalanır.
- Access Token Geçerlilik Süresi (TTL): 15 dakika.
- Refresh Token Geçerlilik Süresi: 7 gün.
- Token Yenileme (Refresh Flow): Sliding expiration yöntemi kullanılır; her refresh işleminde eski token geçersiz kılınır (Token Rotation).
- Yetkilendirme Başlığı (Authorization Header): `Authorization: Bearer <token>` formatında iletilmelidir.

## 2. API İstek Sınırları ve Hız Sınırlama (Rate Limiting)
- Anonim / Herkese Açık Uç Noktalar (Public Endpoints): IP başına dakikada maksimum 60 istek (60 req/min).
- Kimliği Doğrulanmış Uç Noktalar (Authenticated Endpoints): Kullanıcı başına dakikada maksimum 300 istek (300 req/min).
- Ani Yük Toleransı (Burst Allowance): Saniyede en fazla 10 istek anlık patlamaya izin verilir.
- Sınır Aşıldığında HTTP Durum Kodu: `429 Too Many Requests` döner ve `Retry-After` başlığı eklenir.

## 3. Veri Şifreleme ve Güvenlik Standartları (Data Protection)
- Aktarım Sırasındaki Veri Güvenliği (In-Transit): Yalnızca TLS 1.3 zorunludur. TLS 1.0, 1.1 ve 1.2 bağlantıları reddedilir.
- Veritabanı ve Disk Şifreleme (At-Rest): AES-256-GCM algoritması ile hassas veritabanı alanları şifrelenir.
- Parola Özetleme (Password Hashing): Argon2id algoritması (64 MB bellek maliyeti, 3 yineleme) ile tuzlanarak (salt) saklanır.

## 4. Loglama ve Hata Yönetimi İlkeleri (Logging & Error Standards)
- Hassas Veri Maskeleme (PII Masking): Log dosyalarında kredi kartı numaraları, CVV, kullanıcı parolaları ve TC kimlik numaraları ASLA açık metin olarak tutulamaz.
- Standart Hata Formatı: Tüm hata yanıtları RFC-7807 (Problem Details for HTTP APIs) standardına uygun JSON formatında döndürülür (`type`, `title`, `status`, `detail`, `instance`).
