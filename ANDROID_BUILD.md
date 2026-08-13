# Android Build — V11

Project ini sudah disiapkan dengan PWA + Capacitor foundation.

Persiapan production:
1. Install Node.js LTS dan Android Studio.
2. `npm install`
3. Siapkan frontend production di `android-web/`.
4. `npx cap add android`
5. `npx cap sync android`
6. `npx cap open android`
7. Test di HP/tablet.
8. Build signed `.aab` dari Android Studio untuk Play Store.

Catatan: Flask pada `127.0.0.1:5000` adalah development server. Untuk aplikasi production, backend harus berada di server HTTPS atau arsitektur offline-first perlu dipakai.
