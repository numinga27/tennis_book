# booking/views.py
from datetime import datetime, date, timedelta, time as dt_time
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, date, timedelta
from decimal import Decimal
from .models import Court, Booking


def home(request):
    # Показываем только активные корты
    courts = Court.objects.filter(is_active=True)[:3]
    context = {
        'courts': courts,
    }
    return render(request, 'home.html', context)


@login_required
def courts_list(request):
    courts = Court.objects.all().order_by('number')
    context = {
        'courts': courts,
    }
    return render(request, 'booking/courts_list.html', context)


@login_required
def schedule(request):
    """Показываем расписание на календарную неделю для одного корта"""
    # Получаем корт из GET параметра
    court_id = request.GET.get('court')

    # Если корт не указан, показываем первый активный
    if court_id:
        try:
            court = Court.objects.get(id=court_id, is_active=True)
        except Court.DoesNotExist:
            court = Court.objects.filter(is_active=True).first()
    else:
        court = Court.objects.filter(is_active=True).first()

    # Получаем дату из GET параметра
    selected_date_str = request.GET.get('date')

    # Ограничения для обычных пользователей
    today = date.today()
    now = timezone.localtime(timezone.now())
    current_time = now.time()

    if not request.user.is_staff:
        # Обычные пользователи могут смотреть только ТЕКУЩУЮ неделю
        selected_date = today
        week_dates = get_week_dates(today)
    else:
        # Админы могут смотреть любую дату
        if selected_date_str:
            try:
                selected_date = datetime.strptime(
                    selected_date_str, '%Y-%m-%d').date()
                week_dates = get_week_dates(selected_date)
            except ValueError:
                selected_date = today
                week_dates = get_week_dates(today)
        else:
            selected_date = today
            week_dates = get_week_dates(today)

    week_start = week_dates[0]
    week_end = week_dates[-1]

    # Временные слоты (8:00 - 22:00 с шагом 30 минут)
    time_slots = []
    for hour in range(8, 22):
        time_slots.append(f"{hour:02d}:00")
        time_slots.append(f"{hour:02d}:30")

    # Получаем все бронирования для этого корта на эту неделю
    all_bookings = Booking.objects.filter(
        court=court,
        date__range=[week_start, week_end],
        payment_status__in=['paid', 'pending']
    )

    # Создаем словарь занятых слотов
    is_booked = {}
    for booking in all_bookings:
        start_time = booking.start_time
        duration_hours = float(booking.duration)
        start_datetime = datetime.combine(booking.date, start_time)
        end_datetime = start_datetime + timedelta(hours=duration_hours)

        current_slot_time = start_datetime
        while current_slot_time < end_datetime:
            time_key = current_slot_time.time().strftime('%H:%M')
            date_key = booking.date.strftime('%Y-%m-%d')  # ИСПРАВЛЕНО
            slot_key = f"{date_key}_{time_key}"  # ИСПРАВЛЕНО
            is_booked[slot_key] = True
            current_slot_time += timedelta(minutes=30)

    # Даты для навигации (только для админов)
    prev_week = selected_date - timedelta(days=7)
    next_week = selected_date + timedelta(days=7)

    # Только админы могут навигировать
    show_prev_week = request.user.is_staff
    show_next_week = request.user.is_staff

    # Русские названия
    months_ru = {
        1: 'янв', 2: 'фев', 3: 'мар', 4: 'апр', 5: 'май', 6: 'июн',
        7: 'июл', 8: 'авг', 9: 'сен', 10: 'окт', 11: 'ноя', 12: 'дек'
    }

    weekdays_ru = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    weekdays_full = ['Понедельник', 'Вторник', 'Среда',
                     'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

    # Форматируем даты недели для отображения
    formatted_dates = []
    for i, week_date in enumerate(week_dates):
        formatted_dates.append({
            'date_obj': week_date,  # Объект даты
            'day': week_date.day,
            'month': months_ru[week_date.month],
            'weekday': weekdays_full[i],
            'weekday_short': weekdays_ru[i],
            'is_today': week_date == today,
            'is_past': week_date < today,
        })

    # Номер недели в году
    week_number = selected_date.isocalendar()[1]

    # Все активные корты для выбора
    all_courts = Court.objects.filter(is_active=True).order_by('number')

    # Определяем, текущая ли это неделя
    is_current_week = (week_start <= today <= week_end)

    context = {
        'court': court,
        'all_courts': all_courts,
        'time_slots': time_slots,
        'selected_date': selected_date,
        'week_dates': formatted_dates,
        'week_number': week_number,
        'prev_week': prev_week,
        'next_week': next_week,
        'show_prev_week': show_prev_week,
        'show_next_week': show_next_week,
        'is_booked': is_booked,
        'today': today,
        'week_start': week_start,
        'week_end': week_end,
        'user_is_staff': request.user.is_staff,
        'is_current_week': is_current_week,
    }

    return render(request, 'booking/schedule.html', context)


def get_week_dates(base_date=None):
    """Получить даты недели (понедельник-воскресенье)"""
    if base_date is None:
        base_date = date.today()

    # Находим понедельник
    monday = base_date - timedelta(days=base_date.weekday())

    # Возвращаем все 7 дней
    return [monday + timedelta(days=i) for i in range(7)]


@login_required
def create_booking(request):
    if request.method == 'POST':
        court_id = request.POST.get('court')
        booking_date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        duration = request.POST.get('duration', '1')
        payment_method = request.POST.get('payment_method', 'card_transfer')
        notes = request.POST.get('notes', '')

        try:
            court = Court.objects.get(id=court_id, is_active=True)
            date_obj = datetime.strptime(booking_date, '%Y-%m-%d').date()
            time_obj = datetime.strptime(start_time, '%H:%M').time()

            # Преобразуем длительность в Decimal (уже импортирован в начале)
            duration_decimal = Decimal(duration)

            # Определяем будний или выходной день для цены
            is_weekend = date_obj.weekday() >= 5  # 5 = суббота, 6 = воскресенье
            price_per_hour = court.price_weekend if is_weekend else court.price_weekday

            # Проверяем на конфликты
            start_datetime = datetime.combine(date_obj, time_obj)
            end_datetime = start_datetime + \
                timedelta(hours=float(duration_decimal))

            # Проверяем все бронирования на этот день для этого корта
            conflicting_bookings = Booking.objects.filter(
                court=court,
                date=date_obj,
                payment_status__in=['paid', 'pending']
            )

            conflicting = False
            for booking in conflicting_bookings:
                booking_start = datetime.combine(date_obj, booking.start_time)
                booking_end = booking_start + \
                    timedelta(hours=float(booking.duration))

                # Проверяем пересечение временных интервалов
                if not (end_datetime <= booking_start or start_datetime >= booking_end):
                    conflicting = True
                    break

            if conflicting:
                messages.error(
                    request, 'Это время уже занято. Пожалуйста, выберите другое время.')
                return redirect('schedule')

            # Calculate total price - оба значения Decimal
            total_price = price_per_hour * duration_decimal

            # Create booking
            booking = Booking.objects.create(
                user=request.user,
                court=court,
                date=date_obj,
                start_time=time_obj,
                duration=duration_decimal,
                total_price=total_price,
                payment_status='pending',
                payment_method=payment_method,
                notes=notes
            )

            messages.success(
                request, f'Бронирование создано! Стоимость: {booking.total_price} ₽. Теперь перейдите к оплате.')
            return redirect('my_bookings')

        except Exception as e:
            messages.error(
                request, f'Ошибка при создании бронирования: {str(e)}')
            return redirect('schedule')

    # Если GET запрос - показываем форму бронирования
    court_id = request.GET.get('court')
    booking_date = request.GET.get('date')
    start_time = request.GET.get('time')

    if court_id and booking_date and start_time:
        try:
            court = Court.objects.get(id=court_id, is_active=True)

            # Определяем будний или выходной день для цены
            date_obj = datetime.strptime(booking_date, '%Y-%m-%d').date()
            is_weekend = date_obj.weekday() >= 5
            price_per_hour = court.price_weekend if is_weekend else court.price_weekday

            # Генерируем варианты длительности от 0.5 до 4 часов с шагом 0.5
            duration_options = []
            for hours in [Decimal('0.5'), Decimal('1.0'), Decimal('1.5'), Decimal('2.0'),
                          Decimal('2.5'), Decimal('3.0'), Decimal('3.5'), Decimal('4.0')]:
                total_price = price_per_hour * hours

                # Форматируем отображение длительности
                if hours == Decimal('0.5'):
                    display = "30 минут"
                elif hours == Decimal('1.0'):
                    display = "1 час"
                elif hours == Decimal('1.5'):
                    display = "1 час 30 минут"
                elif hours == Decimal('2.0'):
                    display = "2 часа"
                elif hours == Decimal('2.5'):
                    display = "2 часа 30 минут"
                elif hours == Decimal('3.0'):
                    display = "3 часа"
                elif hours == Decimal('3.5'):
                    display = "3 часа 30 минут"
                else:
                    display = "4 часа"

                duration_options.append({
                    'value': str(hours),
                    'display': display,
                    'price': total_price
                })

            context = {
                'court': court,
                'booking_date': booking_date,
                'start_time': start_time,
                'duration_options': duration_options,
                'price_per_hour': price_per_hour,
            }
            return render(request, 'booking/booking_form.html', context)
        except Court.DoesNotExist:
            messages.error(request, 'Корт не найден')
            return redirect('schedule')

    messages.error(request, 'Недостаточно данных для бронирования')
    return redirect('schedule')

# booking/views.py


@login_required
def confirm_payment(request, booking_id):
    """Подтверждение оплаты бронирования"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.payment_status == 'pending':
        booking.payment_status = 'paid'
        booking.save()
        messages.success(request, 'Оплата подтверждена! Бронирование активно.')
    else:
        messages.error(request, 'Невозможно подтвердить оплату.')

    return redirect('my_bookings')


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(
        user=request.user).order_by('-date', '-start_time')
    context = {
        'bookings': bookings,
    }
    return render(request, 'booking/my_bookings.html', context)


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.payment_status == 'pending':
        booking.payment_status = 'cancelled'
        booking.save()
        messages.success(request, 'Бронирование отменено.')
    else:
        messages.error(request, 'Невозможно отменить это бронирование.')

    return redirect('my_bookings')
