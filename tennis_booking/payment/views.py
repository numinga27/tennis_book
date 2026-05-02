# payment/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from booking.models import Booking

@login_required
def process_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.payment_status != 'pending':
        messages.error(request, 'Это бронирование уже оплачено или отменено.')
        return redirect('my_bookings')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'card_transfer')
        
        # Обновляем статус оплаты
        booking.payment_status = 'paid'
        booking.payment_method = payment_method
        booking.save()
        
        messages.success(request, f'✅ Оплата прошла успешно! Бронирование корта {booking.court.number} на {booking.date} подтверждено.')
        return redirect('my_bookings')
    
    # Если GET запрос - показываем страницу оплаты
    context = {
        'booking': booking,
    }
    return render(request, 'payment/process_payment.html', context)