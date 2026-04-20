import uuid

from django.db import migrations
from django.utils import timezone
from django.utils.text import slugify


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Category = apps.get_model("posts", "Category")
    Post = apps.get_model("posts", "Post")

    author = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first() or User.objects.first()
    if author is None:
        author = User(email="system@byzan.local", username="system", is_active=True, is_staff=False, is_superuser=False)
        author.set_unusable_password()
        author.save()

    categories = [
        ("Islam", "islam"),
        ("Aqidah", "aqidah"),
        ("Fiqh", "fiqh"),
        ("Akhlaq", "akhlaq"),
        ("Qur'an", "quran"),
        ("Hadits", "hadits"),
        ("Sejarah Islam", "sejarah-islam"),
    ]

    category_by_slug = {}
    for name, slug in categories:
        category, _ = Category.objects.get_or_create(slug=slug, defaults={"name": name})
        category_by_slug[slug] = category

    posts = [
        {
            "title": "Keutamaan Shalat Lima Waktu",
            "excerpt": "Ringkasan tentang pentingnya menjaga shalat sebagai tiang agama.",
            "content": "Shalat adalah ibadah utama yang menjadi penghubung langsung antara hamba dan Rabb-nya. Menjaga shalat tepat waktu melatih disiplin, ketenangan, dan ketaatan. Mulailah dengan memperbaiki wudhu, memahami bacaan, dan menjaga kekhusyukan.",
            "category_slug": "fiqh",
        },
        {
            "title": "Makna Ikhlas dalam Ibadah",
            "excerpt": "Ikhlas adalah pondasi diterimanya amal. Bagaimana cara menjaganya?",
            "content": "Ikhlas berarti memurnikan niat hanya untuk Allah, bukan untuk pujian atau penilaian manusia. Tanda ikhlas adalah amal tetap dikerjakan meski tidak dilihat orang lain, serta hati tidak bergantung pada apresiasi.",
            "category_slug": "aqidah",
        },
        {
            "title": "Adab Menuntut Ilmu",
            "excerpt": "Adab mendahului ilmu: niat, menghormati guru, dan konsisten belajar.",
            "content": "Menuntut ilmu butuh niat yang benar, kesabaran, dan adab. Mulai dari menjaga lisan, menghormati guru, mencatat pelajaran, dan mengamalkan ilmu sedikit demi sedikit. Ilmu yang bermanfaat adalah yang membuahkan amal dan akhlak.",
            "category_slug": "akhlaq",
        },
        {
            "title": "Mengenal Al-Qur'an: Petunjuk Hidup",
            "excerpt": "Al-Qur'an adalah pedoman bagi manusia. Mulai dari membaca hingga tadabbur.",
            "content": "Al-Qur'an diturunkan sebagai petunjuk. Rutinkan tilawah harian, perbaiki tajwid, dan luangkan waktu untuk memahami makna ayat. Tadabbur membuat kita lebih dekat dan peka terhadap perintah serta larangan.",
            "category_slug": "quran",
        },
        {
            "title": "Hadits dan Perannya dalam Syariat",
            "excerpt": "Hadits menjelaskan Al-Qur'an dan menjadi rujukan hukum setelahnya.",
            "content": "Hadits Nabi ﷺ menjelaskan rincian ibadah yang tidak selalu disebut detail dalam Al-Qur'an. Karena itu, memahami hadits sahih dan kaidah dasar ilmu hadits penting agar tidak salah dalam beramal.",
            "category_slug": "hadits",
        },
        {
            "title": "Pelajaran dari Hijrah Nabi",
            "excerpt": "Hijrah bukan hanya perpindahan tempat, tapi juga perubahan kualitas iman.",
            "content": "Hijrah Nabi ﷺ mengajarkan strategi, tawakal, dan persaudaraan. Hijrah juga bermakna meninggalkan dosa menuju ketaatan. Setiap muslim bisa berhijrah dengan memperbaiki kebiasaan dan lingkungan.",
            "category_slug": "sejarah-islam",
        },
    ]

    for item in posts:
        base_slug = slugify(item["title"])
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        Post.objects.create(
            author=author,
            category=category_by_slug.get(item["category_slug"]),
            title=item["title"],
            slug=slug,
            excerpt=item["excerpt"],
            content=item["content"],
            thumbnail="",
            status="published",
            published_at=timezone.now(),
        )


def backwards(apps, schema_editor):
    Category = apps.get_model("posts", "Category")
    Post = apps.get_model("posts", "Post")

    slugs = ["islam", "aqidah", "fiqh", "akhlaq", "quran", "hadits", "sejarah-islam"]
    Post.objects.filter(category__slug__in=slugs).delete()
    Category.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0001_initial"),
        ("accounts", "0003_user_profile_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

