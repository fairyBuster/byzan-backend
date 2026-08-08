# Alur Pembayaran Course — Byzan API

## Ringkasan Endpoint

| Method | Endpoint | Kapan Dipakai |
|--------|----------|---------------|
| `POST` | `/api/courses/buy/` | Course **gratis** (price=0) — langsung enroll |
| `POST` | `/api/courses/buy/balance/` | Course **berbayar** pakai saldo internal |
| `POST` | `/api/courses/buy/midtrans/` | Course **berbayar** via Midtrans |
| `GET`  | `/api/courses/transactions/` | Riwayat transaksi user |

**Semua endpoint butuh auth:** `Authorization: Bearer <jwt_token>`

---

## 1. Course Gratis (price = 0)

```
┌──────────┐    POST /api/courses/buy/     ┌──────────┐
│ Frontend │ ────────────────────────────> │ Backend  │
│          │    { course_id: 1 }           │          │
│          │                               │          │──> Buat transaksi amount=0, status=paid
│          │    201 Created                │          │──> Enroll user langsung
│          │ <──────────────────────────── │          │
│          │                               └──────────┘
│          │    ✅ User langsung bisa akses course
```

### Request

```json
{
  "course_id": 1
}
```

### Response (201)

```json
{
  "message": "Berhasil membeli kursus \"Belajar Django Pemula\"",
  "transaction": {
    "id": 15,
    "trx_code": "TRX-A1B2C3D4E5",
    "course": 1,
    "course_title": "Belajar Django Pemula",
    "amount": "0.00",
    "status": "paid",
    "provider": "balance",
    "paid_at": "2026-08-09T12:30:00+07:00",
    "created_at": "2026-08-09T12:30:00+07:00",
    "snap_redirect_url": null
  }
}
```

### Error: Sudah terdaftar (400)

```json
{
  "error": "Sudah terdaftar di kursus ini"
}
```

---

## 2. Course Berbayar — Pakai Saldo

```
┌──────────┐    POST /api/courses/buy/balance/     ┌──────────┐
│ Frontend │ ────────────────────────────────────> │ Backend  │
│          │    { course_id: 1 }                   │          │
│          │                                       │          │──> Cek user.balance >= course.price
│          │    201 Created                        │          │──> Potong saldo
│          │ <──────────────────────────────────── │          │──> Buat transaksi paid
│          │                                       │          │──> Enroll user
│          │    ✅ User langsung bisa akses        └──────────┘
```

### Request

```json
{
  "course_id": 1
}
```

### Response (201)

```json
{
  "message": "Berhasil membeli kursus \"Belajar Django Pemula\" dengan saldo",
  "transaction": {
    "id": 16,
    "trx_code": "TRX-F6G7H8I9J0",
    "course": 1,
    "course_title": "Belajar Django Pemula",
    "amount": "150000.00",
    "status": "paid",
    "provider": "balance",
    "paid_at": "2026-08-09T12:35:00+07:00",
    "created_at": "2026-08-09T12:35:00+07:00",
    "snap_redirect_url": null
  },
  "remaining_balance": "350000.00"
}
```

### Error: Saldo tidak cukup (400)

```json
{
  "error": "Saldo tidak mencukupi"
}
```

---

## 3. Course Berbayar — Via Midtrans (Snap)

```
┌──────────┐                                          ┌──────────┐
│ Frontend │──① POST /api/courses/buy/midtrans/ ────>│ Backend  │
│          │    { course_id: 1 }                      │          │
│          │                                          │          │──② Panggil Midtrans Snap API
│          │  ③ Response: snap_redirect_url           │          │   (bikin transaksi di Midtrans)
│          │<─────────────────────────────────────────│          │
│          │                                          │          │──③ Simpan transaksi pending
│          │  ④ Redirect user ke Midtrans             │          │   di DB (status=pending)
│          │─────────────────────────────────────────>│          │
│          │                                          └──────────┘
│          │
│   User   │──⑤ Bayar di halaman Midtrans
│          │   (credit card, bank transfer, gopay, dll.)
│          │
│          │
│ Midtrans │──⑥ POST notifikasi ─────────────────> POST /api/courses/midtrans/notify/
│          │    { order_id, transaction_status,      │
│          │      fraud_status, signature_key }      │──⑦ Validasi signature
│          │                                         │──⑧ Update transaksi → paid
│          │                                         │──⑨ Auto-enroll user
│          │  ⑩ 200 OK                              │
│          │<─────────────────────────────────────── │
│          │
│  User    │──⑪ Redirect balik ke frontend (finish_url / custom)
│          │    ✅ User bisa akses course
```

### Step ①-③: Inisiasi

**Request:**
```json
{
  "course_id": 1
}
```

**Response (201):**
```json
{
  "message": "Transaksi dibuat. Selesaikan pembayaran via Midtrans",
  "transaction": {
    "id": 17,
    "trx_code": "MID-K1L2M3N4O5",
    "course": 1,
    "course_title": "Belajar Django Pemula",
    "amount": "150000.00",
    "status": "pending",
    "provider": "midtrans",
    "paid_at": null,
    "created_at": "2026-08-09T12:40:00+07:00",
    "snap_redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/abc123..."
  },
  "snap_token": "abc123-def456-ghi789",
  "snap_redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/abc123..."
}
```

### Step ④: Tampilkan Halaman Pembayaran ke User

Ada dua cara di frontend. **Pilih salah satu:**

#### Opsi A: Redirect langsung (direkomendasikan — paling simpel)

User di-redirect ke halaman Midtrans, setelah bayar di-redirect balik ke frontend.
**Tidak butuh** Midtrans Client Key, tidak perlu load `snap.js`.

```js
// Setelah dapat response dari backend
window.location.href = response.snap_redirect_url;
```

#### Opsi B: Snap Popup / Embed (tanpa pindah halaman)

Popup Midtrans muncul di halaman yang sama (iframe). **Butuh Midtrans Client Key** karena `snap.js` di-load di browser dan Client Key adalah public key yang didesain Midtrans untuk operasi client-side. **Server Key tetap hanya di backend** — jangan pernah taruh Server Key di frontend.

```html
<!-- Load Midtrans Snap JS di <head> -->
<!-- data-client-key = Client Key (public), BUKAN Server Key (secret) -->
<script
  src="https://app.sandbox.midtrans.com/snap/snap.js"
  data-client-key="YOUR_SANDBOX_CLIENT_KEY"
></script>
```

```js
// Gunakan snap_token dari response backend
window.snap.pay(response.snap_token, {
  onSuccess: function(result) {
    // Arahkan user ke halaman sukses / course
    window.location.href = "/payment/success?order_id=" + result.order_id;
  },
  onPending: function(result) {
    console.log("Menunggu pembayaran:", result);
  },
  onError: function(result) {
    console.log("Pembayaran gagal:", result);
  },
  onClose: function() {
    console.log("User menutup popup tanpa menyelesaikan");
  }
});
```

| Key | Di mana | Buat apa | Aman di frontend? |
|-----|---------|----------|-------------------|
| **Server Key** | Backend aja | Panggil Snap API, validasi webhook | **TIDAK** — ini rahasia |
| **Client Key** | Frontend (opsi B aja) | Inisialisasi `snap.js` | **AMAN** — emang untuk public |

> Kalau pakai Opsi A, kamu **tidak butuh Client Key sama sekali** dan tidak perlu load `snap.js`.

### Step ⑥-⑩: Notifikasi (otomatis, backend-only)

Midtrans otomatis kirim POST notifikasi setelah user selesai bayar. Backend akan:
1. Validasi `signature_key`
2. Update transaksi `status=paid`, `paid_at=now`
3. Auto-enroll user ke course

User tidak perlu melakukan apa-apa di tahap ini.

### Error: Course gratis lewat Midtrans (400)

```json
{
  "error": "Kursus ini gratis. Gunakan endpoint POST /api/courses/buy/ untuk langsung enroll."
}
```

---

## 4. Cek Status Transaksi

### `GET /api/courses/transactions/`

**Response:**
```json
[
  {
    "id": 17,
    "trx_code": "MID-K1L2M3N4O5",
    "course": 1,
    "course_title": "Belajar Django Pemula",
    "amount": "150000.00",
    "status": "paid",
    "provider": "midtrans",
    "paid_at": "2026-08-09T12:45:00+07:00",
    "created_at": "2026-08-09T12:40:00+07:00",
    "snap_redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/abc123..."
  }
]
```

> **Tip frontend**: Setelah redirect balik dari Midtrans, polling `GET /api/courses/transactions/` untuk cek apakah status sudah berubah dari `pending` → `paid`.

---

## Decision Tree Frontend

```
User klik "Beli Course"
│
├── price == 0 (Gratis)
│   └── POST /api/courses/buy/
│       └── Langsung akses course ✅
│
└── price > 0 (Berbayar)
    │
    ├── Bayar pakai saldo?
    │   └── POST /api/courses/buy/balance/
    │       ├── 201 → Akses course ✅
    │       └── 400 "Saldo tidak mencukupi"
    │           └── Tawarkan Midtrans
    │
    └── Bayar via Midtrans?
        └── POST /api/courses/buy/midtrans/
            ├── 201 → Redirect ke snap_redirect_url (atau snap.pay)
            │         └── Polling /api/courses/transactions/
            │             └── status=paid → Akses course ✅
            ├── 400 "Sudah terdaftar" → Akses course ✅
            └── 400 "Kursus gratis"   → Pakai endpoint /buy/
```
