# Mobil Uygulama UI/UX Tasarım Sistemi ve Arayüz Kılavuzu

## 1. Tipografi ve Yazı Tipleri (Typography)
- Birincil Yazı Tipi (Primary Font): Inter (iOS ve Android için desteklenen modern sans-serif).
- İkincil / Sistem Yazı Tipi: SF Pro (iOS) ve Roboto (Android).
- Başlık 1 (Heading 1): 24px, Kalın (Bold 700), Satır Yüksekliği: 32px.
- Başlık 2 (Heading 2): 20px, Yarı Kalın (Semi-bold 600), Satır Yüksekliği: 28px.
- Başlık 3 (Heading 3): 16px, Yarı Kalın (Semi-bold 600), Satır Yüksekliği: 24px.
- Gövde Metni (Body Regular): 14px, Normal (Regular 400), Satır Yüksekliği: 20px.
- Küçük / Açıklama Metni (Caption): 12px, Normal (Regular 400), Satır Yüksekliği: 16px.

## 2. Renk Paleti ve Temalar (Color Palette)
- Birincil Marka Rengi (Primary): `#0E2538` (Koyu Gece Mavisi / Kurumsal).
- İkincil / Vurgu Rengi (Secondary / Accent): `#2563EB` (Parlak Mavi).
- Arka Plan Rengi (Background): `#F0F4F8` (Açık Gri / Mavi alt tonlu).
- Yüzey / Kart Rengi (Surface): `#FFFFFF` (Saf Beyaz).
- Başarı Rengi (Success): `#16A34A` (Yeşil).
- Hata / Uyarı Rengi (Error): `#DC2626` (Kırmızı).
- Metin Ana Renk: `#0F172A` (Koyu Slate).
- Metin İkincil Renk: `#64748B` (Açık Slate Gri).
- Çerçeve / Kenarlık Rengi (Border): `#CBD5E1`.

## 3. Boşluklar ve Izgara Sistemi (Spacing & Grid)
- 4px baseline grid sistemi esas alınmıştır.
- Mikro Boşluk (XS): 4px
- Küçük Boşluk (S): 8px
- Standart İç Boşluk (M / Padding): 16px (Tüm standart kart ve ekran içi kenar boşluğu).
- Geniş Boşluk (L): 24px
- Ekstra Geniş Boşluk (XL): 32px
- Ekran Kenar Boşluğu (Screen Margin): Yatayda 16px veya 20px.

## 4. Bileşen Ölçüleri ve Köşe Yuvarlama (Corner Radius & Components)
- Kart Köşe Yuvarlama (Card Corner Radius): 12px
- Buton Köşe Yuvarlama (Button Corner Radius): 8px
- Modal ve Dialog Köşe Yuvarlama: 16px
- Input / Giriş Alanı Köşe Yuvarlama: 10px
- Etiket / Badge Köşe Yuvarlama: 6px
- Buton Standart Yüksekliği: 48px
- Input Standart Yüksekliği: 44px
- Dokunma Hedefi (Touch Target): Minimum 48x48px erişilebilirlik standardı.

## 5. Gölgelendirme ve Derinlik (Shadows & Elevation)
- Düşük Derinlik (Elevation 1 / Kartlar): `0 2px 4px rgba(0, 0, 0, 0.05)`
- Orta Derinlik (Elevation 2 / Dropdown & Popover): `0 4px 12px rgba(0, 0, 0, 0.08)`
- Yüksek Derinlik (Elevation 3 / Modallar & Bottom Sheet): `0 8px 24px rgba(0, 0, 0, 0.15)`
