# booking/admin.py - ОБНОВЛЕННАЯ ВЕРСИЯ ДЛЯ ВАШЕЙ СТРУКТУРЫ
from django.utils.html import format_html
from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.db.models import Count, Sum, Q
from django.http import HttpResponse
import csv
import io
from datetime import datetime, date, timedelta
from .models import Court, Booking, TimeSlot
from users.models import CustomUser


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'court_type', 'location',
                    'price_weekday', 'price_weekend', 'is_active', 'get_bookings_count']
    list_filter = ['court_type', 'location', 'is_active']
    search_fields = ['number', 'name']
    ordering = ['number']
    actions = ['export_schedule_csv', 'mark_inactive', 'mark_active']

    def get_bookings_count(self, obj):
        """Количество активных бронирований для корта"""
        today = timezone.now().date()
        count = Booking.objects.filter(
            court=obj,
            date__gte=today,
            payment_status__in=['paid', 'pending']
        ).count()
        return f"📅 {count}"
    get_bookings_count.short_description = 'Бронирования'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Добавляем аннотацию для сортировки по количеству бронирований
        return queryset.annotate(
            bookings_count=Count('booking', filter=Q(
                booking__payment_status__in=['paid', 'pending']))
        )

    def export_schedule_csv(self, request, queryset):
        """Экспорт расписания выбранных кортов в CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="court_schedule.csv"'

        # Используем кодировку UTF-8 с BOM для корректного отображения в Excel
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=',')

        writer.writerow(['Корт', 'Дата', 'День недели', 'Время',
                        'Статус', 'Пользователь', 'Телефон'])

        # На 14 дней вперед (2 недели)
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=14)

        for court in queryset:
            # Получаем все бронирования на этот период
            bookings = Booking.objects.filter(
                court=court,
                date__range=[start_date, end_date],
                payment_status__in=['paid', 'pending']
            ).select_related('user').order_by('date', 'start_time')

            # Создаем словарь для быстрого поиска бронирований
            bookings_dict = {}
            for booking in bookings:
                key = f"{booking.date}_{booking.start_time.strftime('%H:%M')}"
                bookings_dict[key] = booking

            # Генерируем слоты с 8:00 до 22:00
            time_slots = []
            for hour in range(8, 22):
                time_slots.append(f"{hour:02d}:00")
                time_slots.append(f"{hour:02d}:30")

            # Заполняем данные
            for single_date in (start_date + timedelta(days=n) for n in range(15)):
                day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг',
                             'Пятница', 'Суббота', 'Воскресенье']
                day_name = day_names[single_date.weekday()]

                for time_slot in time_slots:
                    key = f"{single_date}_{time_slot}"
                    if key in bookings_dict:
                        booking = bookings_dict[key]
                        writer.writerow([
                            f"Корт {court.number}",
                            single_date.strftime('%d.%m.%Y'),
                            day_name,
                            time_slot,
                            'Занято',
                            booking.user.get_full_name() or booking.user.username,
                            booking.user.phone if hasattr(
                                booking.user, 'phone') else ''
                        ])
                    else:
                        writer.writerow([
                            f"Корт {court.number}",
                            single_date.strftime('%d.%m.%Y'),
                            day_name,
                            time_slot,
                            'Свободно',
                            '',
                            ''
                        ])

        return response
    export_schedule_csv.short_description = "📤 Экспорт расписания (CSV)"

    def mark_inactive(self, request, queryset):
        """Сделать выбранные корты неактивными"""
        updated = queryset.update(is_active=False)
        messages.success(request, f'{updated} кортов помечены как неактивные')
    mark_inactive.short_description = "⏸️ Сделать неактивными"

    def mark_active(self, request, queryset):
        """Сделать выбранные корты активными"""
        updated = queryset.update(is_active=True)
        messages.success(request, f'{updated} кортов помечены как активные')
    mark_active.short_description = "▶️ Сделать активными"


# booking/admin.py - исправленная версия для TimeSlotAdmin

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['court', 'date', 'start_time',
                    'is_available', 'get_booking_info']
    list_filter = ['date', 'is_available', 'court']
    search_fields = ['court__number', 'court__name']
    ordering = ['-date', 'start_time']
    actions = ['mark_available', 'mark_unavailable']
    change_list_template = 'admin/booking/timeslot/change_list.html'

    def get_urls(self):
        """Добавляем кастомные URL"""
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_from_csv),
                 name='booking_timeslot_import_csv'),
        ]
        return custom_urls + urls

    def get_booking_info(self, obj):
        """Показываем информацию о бронировании слота"""
        try:
            booking = Booking.objects.filter(
                court=obj.court,
                date=obj.date,
                start_time__hour=obj.start_time.hour,
                start_time__minute=obj.start_time.minute,
                payment_status__in=['paid', 'pending']
            ).first()

            if booking:
                user_info = booking.user.get_full_name() or booking.user.username
                return f"👤 {user_info} ({booking.get_payment_status_display()})"
        except:
            pass
        return "✅ Свободен"
    get_booking_info.short_description = 'Информация'

    def import_from_csv(self, request):
        """Импорт временных слотов из CSV файла"""
        if request.method == 'POST' and 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']

            # Проверяем расширение файла
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Пожалуйста, загрузите CSV файл')
                return redirect('..')

            # Читаем файл
            try:
                # Пробуем разные кодировки
                content = csv_file.read().decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_file.seek(0)
                    content = csv_file.read().decode('cp1251')
                except UnicodeDecodeError:
                    messages.error(
                        request, 'Ошибка кодировки файла. Используйте UTF-8 или Windows-1251')
                    return redirect('..')

            io_string = io.StringIO(content)
            reader = csv.reader(io_string, delimiter=',')

            imported_count = 0
            error_count = 0
            skipped_count = 0

            # Пропускаем заголовок, если он есть
            try:
                header = next(reader)
                # Проверяем, есть ли заголовок
                if any(word in str(header[0]).lower() for word in ['court', 'корт', 'дата', 'date']):
                    pass  # Пропускаем заголовок
                else:
                    # Если это не заголовок, возвращаемся к началу
                    io_string.seek(0)
                    reader = csv.reader(io_string, delimiter=',')
            except StopIteration:
                io_string.seek(0)
                reader = csv.reader(io_string, delimiter=',')

            for row_num, row in enumerate(reader, 1):
                if len(row) >= 3:
                    try:
                        court_id = int(row[0].strip())

                        # Парсим дату
                        date_str = row[1].strip()
                        date_formats = ['%Y-%m-%d',
                                        '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y']
                        date_obj = None
                        for fmt in date_formats:
                            try:
                                date_obj = datetime.strptime(
                                    date_str, fmt).date()
                                break
                            except ValueError:
                                continue

                        if not date_obj:
                            raise ValueError(
                                f"Неверный формат даты: {date_str}")

                        # Парсим время
                        time_str = row[2].strip()
                        time_formats = ['%H:%M', '%H.%M', '%H %M']
                        time_obj = None
                        for fmt in time_formats:
                            try:
                                time_obj = datetime.strptime(
                                    time_str, fmt).time()
                                break
                            except ValueError:
                                continue

                        if not time_obj:
                            raise ValueError(
                                f"Неверный формат времени: {time_str}")

                        # Доступность
                        is_available = True
                        if len(row) >= 4:
                            avail_str = row[3].strip().lower()
                            is_available = avail_str in [
                                'true', '1', 'yes', 'да', 'доступно']

                        court = Court.objects.get(id=court_id)

                        # Проверяем, не занят ли слот
                        existing_booking = Booking.objects.filter(
                            court=court,
                            date=date_obj,
                            start_time=time_obj,
                            payment_status__in=['paid', 'pending']
                        ).exists()

                        if existing_booking:
                            skipped_count += 1
                            continue

                        TimeSlot.objects.update_or_create(
                            court=court,
                            date=date_obj,
                            start_time=time_obj,
                            defaults={'is_available': is_available}
                        )

                        imported_count += 1

                    except Court.DoesNotExist:
                        messages.warning(
                            request, f'Строка {row_num}: Корт с ID {row[0]} не найден')
                        error_count += 1
                    except Exception as e:
                        messages.warning(
                            request, f'Строка {row_num}: {str(e)}')
                        error_count += 1

            messages.success(request,
                             f'✅ Импортировано: {imported_count}<br>'
                             f'⚠️ Пропущено (уже занято): {skipped_count}<br>'
                             f'❌ Ошибок: {error_count}'
                             )
            return redirect('..')

        # Если GET запрос, показываем форму загрузки
        courts = Court.objects.all()
        context = {
            'title': 'Импорт расписания из CSV',
            'opts': self.model._meta,
            'courts': courts,
        }
        return render(request, 'admin/booking/timeslot/import_csv.html', context)

    def mark_available(self, request, queryset):
        """Пометить выбранные слоты как доступные"""
        updated = queryset.update(is_available=True)
        messages.success(request, f'{updated} слотов помечены как доступные')
    mark_available.short_description = "✅ Пометить доступными"

    def mark_unavailable(self, request, queryset):
        """Пометить выбранные слоты как недоступные"""
        updated = queryset.update(is_available=False)
        messages.success(request, f'{updated} слотов помечены как недоступные')
    mark_unavailable.short_description = "❌ Пометить недоступными"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'get_user_info', 'court', 'date',
                    'start_time', 'duration', 'total_price',
                    'payment_status_badge', 'payment_method', 'created_at']
    list_filter = ['date', 'payment_status',
                   'court', 'payment_method', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name',
                     'user__last_name', 'court__number', 'notes']
    readonly_fields = ['created_at', 'total_price', 'get_user_details']
    ordering = ['-date', '-start_time']
    actions = ['export_bookings_csv', 'mark_as_paid', 'mark_as_pending',
               'mark_as_cancelled', 'export_receipt']
    list_per_page = 50
    date_hierarchy = 'date'

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'court', 'date', 'start_time', 'duration', 'total_price')
        }),
        ('Информация о пользователе', {
            'fields': ('get_user_details',),
            'classes': ('collapse',)
        }),
        ('Статус и оплата', {
            'fields': ('payment_status', 'payment_method', 'created_at')
        }),
        ('Дополнительно', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def payment_status_badge(self, obj):
        """Красивые бейджи статуса оплаты"""
        colors = {
            'paid': 'success',
            'pending': 'warning',
            'cancelled': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.payment_status, 'secondary'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Статус'
    payment_status_badge.admin_order_field = 'payment_status'

    def get_user_info(self, obj):
        """Информация о пользователе"""
        user = obj.user
        name = user.get_full_name()
        if name:
            return format_html('<strong>{}</strong><br><small>{}</small>', name, user.email)
        return format_html('<strong>{}</strong><br><small>{}</small>', user.username, user.email)
    get_user_info.short_description = 'Пользователь'
    get_user_info.admin_order_field = 'user__username'

    def get_user_details(self, obj):
        """Детальная информация о пользователе"""
        user = obj.user
        details = []

        if user.first_name and user.last_name:
            details.append(
                f"<strong>ФИО:</strong> {user.last_name} {user.first_name}")
        if user.email:
            details.append(f"<strong>Email:</strong> {user.email}")
        if hasattr(user, 'phone') and user.phone:
            details.append(f"<strong>Телефон:</strong> {user.phone}")
        if user.date_joined:
            details.append(
                f"<strong>Зарегистрирован:</strong> {user.date_joined.strftime('%d.%m.%Y')}")

        # Статистика пользователя
        bookings_count = Booking.objects.filter(user=user).count()
        total_spent = Booking.objects.filter(user=user, payment_status='paid').aggregate(
            Sum('total_price'))['total_price__sum'] or 0

        details.append(
            f"<strong>Всего бронирований:</strong> {bookings_count}")
        details.append(f"<strong>Всего потрачено:</strong> {total_spent} ₽")

        return format_html('<br>'.join(details))
    get_user_details.short_description = 'Детали пользователя'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'court')

    def changelist_view(self, request, extra_context=None):
        """Добавляем статистику в список"""
        extra_context = extra_context or {}

        # Статистика
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        extra_context.update({
            'today_bookings': Booking.objects.filter(date=today).count(),
            'pending_payments': Booking.objects.filter(payment_status='pending').count(),
            'total_revenue_today': Booking.objects.filter(
                date=today,
                payment_status='paid'
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'weekly_bookings': Booking.objects.filter(
                date__gte=week_ago
            ).count(),
            'weekly_revenue': Booking.objects.filter(
                date__gte=week_ago,
                payment_status='paid'
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
        })

        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        """Добавляем кастомные URL"""
        urls = super().get_urls()
        custom_urls = [
            path('stats/', self.admin_site.admin_view(self.booking_stats),
                 name='booking-stats'),
            path('export-all/', self.admin_site.admin_view(self.export_all_bookings),
                 name='export-all-bookings'),
        ]
        return custom_urls + urls

    # booking/admin.py - исправленная версия для метода booking_stats

    def booking_stats(self, request):
        """Страница статистики"""
        from django.db.models import Count, Sum, Avg
        from datetime import datetime, timedelta

        # Периоды
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Общая статистика
        stats = {
            'total_bookings': Booking.objects.count(),
            'total_revenue': Booking.objects.filter(
                payment_status='paid'
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,

            'today_bookings': Booking.objects.filter(date=today).count(),
            'today_revenue': Booking.objects.filter(
                date=today,
                payment_status='paid'
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,

            'week_bookings': Booking.objects.filter(date__gte=week_start).count(),
            'week_revenue': Booking.objects.filter(
                date__gte=week_start,
                payment_status='paid'
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,

            'month_bookings': Booking.objects.filter(date__gte=month_start).count(),
            'month_revenue': Booking.objects.filter(
                date__gte=month_start,
                payment_status='paid'
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
        }

        # Статистика по кортам
        court_stats = Court.objects.annotate(
            bookings_count=Count('booking'),
            revenue=Sum('booking__total_price', filter=Q(
                booking__payment_status='paid'))
        ).order_by('-bookings_count')[:10]

        # Статистика по пользователям - ИСПРАВЛЕНО
        user_stats = []
        try:
            user_stats = Booking.objects.values(
                'user__username', 'user__email', 'user__first_name', 'user__last_name'
            ).annotate(
                bookings_count=Count('id'),
                total_spent=Sum('total_price', filter=Q(payment_status='paid'))
            ).order_by('-total_spent')[:10]
        except Exception as e:
            print(f"Error getting user stats: {e}")
            user_stats = []

        context = {
            **self.admin_site.each_context(request),
            'title': 'Статистика бронирований',
            'today': today,
            'stats': stats,
            'court_stats': court_stats,
            'user_stats': user_stats,
            'opts': self.model._meta,
        }

        return render(request, 'admin/booking/booking_stats.html', context)

    def import_bookings_from_csv(self, request):
        """Импорт бронирований из CSV файла"""
        # Импортируем все необходимые модули внутри метода
        from decimal import Decimal
        from datetime import datetime, timedelta
        from users.models import CustomUser
        import csv
        import io
        
        if request.method == 'POST' and 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            # Проверяем расширение файла
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Пожалуйста, загрузите CSV файл')
                return redirect('..')
            
            # Читаем файл
            try:
                content = csv_file.read().decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_file.seek(0)
                    content = csv_file.read().decode('cp1251')
                except UnicodeDecodeError:
                    messages.error(request, 'Ошибка кодировки файла. Используйте UTF-8 или Windows-1251')
                    return redirect('..')
            
            io_string = io.StringIO(content)
            reader = csv.reader(io_string, delimiter=',')
            
            imported_count = 0
            error_count = 0
            skipped_count = 0
            errors_list = []
            
            # Пропускаем заголовок, если он есть
            try:
                header = next(reader)
            except StopIteration:
                pass
            
            for row_num, row in enumerate(reader, 2):  # начинаем со 2 строки
                if len(row) >= 6:  # Минимум 6 полей
                    try:
                        # Формат: court_id, username/email, date, time, duration, payment_status
                        court_id = int(row[0].strip())
                        user_identifier = row[1].strip()
                        date_str = row[2].strip()
                        time_str = row[3].strip()
                        duration = Decimal(row[4].strip())
                        payment_status = row[5].strip().lower()
                        
                        # Находим корт
                        court = Court.objects.get(id=court_id)
                        
                        # Находим пользователя
                        user = None
                        if '@' in user_identifier:
                            user = CustomUser.objects.filter(email=user_identifier).first()
                        else:
                            user = CustomUser.objects.filter(username=user_identifier).first()
                        
                        if not user:
                            user = CustomUser.objects.filter(is_staff=True).first()
                            if not user:
                                user = CustomUser.objects.first()
                        
                        if not user:
                            raise ValueError(f"Пользователь {user_identifier} не найден")
                        
                        # Парсим дату
                        date_formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']
                        date_obj = None
                        for fmt in date_formats:
                            try:
                                date_obj = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                        
                        if not date_obj:
                            raise ValueError(f"Неверный формат даты: {date_str}")
                        
                        # Парсим время
                        time_formats = ['%H:%M', '%H.%M']
                        time_obj = None
                        for fmt in time_formats:
                            try:
                                time_obj = datetime.strptime(time_str, fmt).time()
                                break
                            except ValueError:
                                continue
                        
                        if not time_obj:
                            raise ValueError(f"Неверный формат времени: {time_str}")
                        
                        # Проверяем на конфликт
                        start_datetime = datetime.combine(date_obj, time_obj)
                        end_datetime = start_datetime + timedelta(hours=float(duration))
                        
                        conflicting = Booking.objects.filter(
                            court=court,
                            date=date_obj,
                            payment_status__in=['paid', 'pending']
                        )
                        
                        conflict = False
                        for booking in conflicting:
                            booking_start = datetime.combine(date_obj, booking.start_time)
                            booking_end = booking_start + timedelta(hours=float(booking.duration))
                            
                            if not (end_datetime <= booking_start or start_datetime >= booking_end):
                                conflict = True
                                break
                        
                        if conflict:
                            skipped_count += 1
                            continue
                        
                        # Рассчитываем цену
                        is_weekend = date_obj.weekday() >= 5
                        price_per_hour = court.price_weekend if is_weekend else court.price_weekday
                        total_price = price_per_hour * duration
                        
                        # Создаем бронирование
                        Booking.objects.create(
                            user=user,
                            court=court,
                            date=date_obj,
                            start_time=time_obj,
                            duration=duration,
                            total_price=total_price,
                            payment_status=payment_status if payment_status in ['paid', 'pending', 'cancelled'] else 'pending',
                            payment_method='card_transfer',  # Значение по умолчанию
                            notes='Импортировано из CSV'
                        )
                        
                        imported_count += 1
                        
                    except Court.DoesNotExist:
                        error_count += 1
                        errors_list.append(f"Строка {row_num}: Корт с ID {row[0]} не найден")
                    except ValueError as e:
                        error_count += 1
                        errors_list.append(f"Строка {row_num}: {str(e)}")
                    except Exception as e:
                        error_count += 1
                        errors_list.append(f"Строка {row_num}: {str(e)}")
                else:
                    error_count += 1
                    errors_list.append(f"Строка {row_num}: Недостаточно полей (нужно минимум 6)")
            
            # Формируем сообщение об ошибках
            error_message = ""
            if errors_list:
                error_message = "<br>".join(errors_list[:5])  # Показываем первые 5 ошибок
                if len(errors_list) > 5:
                    error_message += f"<br>... и еще {len(errors_list) - 5} ошибок"
            
            messages.success(request, 
                f'✅ Импортировано: {imported_count}<br>'
                f'⚠️ Пропущено (конфликт): {skipped_count}<br>'
                f'❌ Ошибок: {error_count}<br>'
                f'{error_message}'
            )
            return redirect('..')
        
        # GET запрос - показываем форму
        courts = Court.objects.all()
        users = CustomUser.objects.all()[:10]
        
        context = {
            'title': 'Импорт бронирований из CSV',
            'opts': self.model._meta,
            'courts': courts,
            'users': users,
        }
        return render(request, 'admin/booking/import_bookings.html', context)

    

    def export_all_bookings(self, request):
        """Экспорт всех бронирований"""
        # Реализация аналогична export_bookings_csv, но для всех записей
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="all_bookings.csv"'
        response.write('\ufeff')

        writer = csv.writer(response, delimiter=',')
        writer.writerow([
            'ID', 'Пользователь', 'Email', 'Телефон', 'Корт', 'Дата', 'Время начала',
            'Длительность', 'Стоимость', 'Статус оплаты', 'Способ оплаты',
            'Дата создания', 'Примечания'
        ])

        bookings = Booking.objects.select_related('user', 'court').all()
        for booking in bookings:
            user = booking.user
            phone = getattr(user, 'phone', '') if hasattr(
                user, 'phone') else ''

            writer.writerow([
                booking.id,
                user.get_full_name() or user.username,
                user.email,
                phone,
                f"Корт {booking.court.number}",
                booking.date.strftime('%d.%m.%Y'),
                booking.start_time.strftime('%H:%M'),
                booking.duration,
                booking.total_price,
                booking.get_payment_status_display(),
                booking.get_payment_method_display(),
                booking.created_at.strftime('%d.%m.%Y %H:%M'),
                booking.notes
            ])

        return response

    def export_bookings_csv(self, request, queryset):
        """Экспорт выбранных бронирований в CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="bookings_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff')

        writer = csv.writer(response, delimiter=',')
        writer.writerow([
            'ID', 'Пользователь', 'Email', 'Корт', 'Дата', 'Время начала',
            'Длительность', 'Стоимость', 'Статус оплаты', 'Способ оплаты', 'Дата создания'
        ])

        for booking in queryset.select_related('user', 'court'):
            writer.writerow([
                booking.id,
                booking.user.get_full_name() or booking.user.username,
                booking.user.email,
                f"Корт {booking.court.number}",
                booking.date.strftime('%d.%m.%Y'),
                booking.start_time.strftime('%H:%M'),
                booking.duration,
                booking.total_price,
                booking.get_payment_status_display(),
                booking.get_payment_method_display(),
                booking.created_at.strftime('%d.%m.%Y %H:%M')
            ])

        return response
    export_bookings_csv.short_description = "📤 Экспорт выбранных (CSV)"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-bookings/', self.admin_site.admin_view(
                self.import_bookings_from_csv), name='booking_import_bookings'),
        ]
        return custom_urls + urls

    def export_receipt(self, request, queryset):
        """Экспорт квитанций для оплаты"""
        # Можно реализовать генерацию PDF квитанций
        messages.info(request, 'Генерация квитанций в разработке')
        return redirect('..')
    export_receipt.short_description = "🧾 Экспорт квитанций"

    def mark_as_paid(self, request, queryset):
        """Пометить выбранные бронирования как оплаченные"""
        updated = queryset.update(payment_status='paid')
        messages.success(
            request, f'{updated} бронирований помечены как оплаченные')
    mark_as_paid.short_description = "✅ Пометить как оплачено"

    def mark_as_pending(self, request, queryset):
        """Пометить выбранные бронирования как ожидающие оплаты"""
        updated = queryset.update(payment_status='pending')
        messages.success(
            request, f'{updated} бронирований помечены как ожидающие оплаты')
    mark_as_pending.short_description = "⏳ Пометить как ожидает оплаты"

    def mark_as_cancelled(self, request, queryset):
        """Пометить выбранные бронирования как отмененные"""
        updated = queryset.update(payment_status='cancelled')
        messages.success(request, f'{updated} бронирований отменены')
    mark_as_cancelled.short_description = "❌ Отменить бронирования"
