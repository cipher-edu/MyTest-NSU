# Dockerfile

# 1. Asosiy obrazni tanlash
# Python'ning rasmiy, optimallashtirilgan obrazidan foydalanamiz
FROM python:3.11-slim

# 2. Ishchi papkani belgilash
# Keyingi barcha buyruqlar shu papka ichida bajariladi
WORKDIR /app

# 3. Tizim o'zgaruvchilarini sozlash
# Python'ning buferlashini o'chiramiz, loglar darhol ko'rinishi uchun
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 4. Tizim bog'liqliklarini o'rnatish (masalan, postgresql-client, gettext)
# Bu mysqlclient yoki psycopg2-binary to'g'ri ishlashi uchun kerak
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. Virtual muhit yaratish
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 6. Bog'liqliklarni o'rnatish
# Avval requirements.txt faylini nusxalab, keyin o'rnatamiz.
# Bu Docker keshidan unumli foydalanish imkonini beradi.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Butun loyiha kodini konteynerga nusxalash
COPY . .

# 8. Statik fayllarni yig'ish (agar kerak bo'lsa)
# RUN python manage.py collectstatic --noinput

# 9. Portni ochish (Gunicorn shu portda ishlaydi)
EXPOSE 8000

# 10. Konteyner ishga tushganda bajariladigan buyruq
# Gunicorn serverini ishga tushiramiz
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "external_auth_project.wsgi:application"]