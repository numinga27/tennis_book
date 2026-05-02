# booking/management/commands/create_initial_courts.py
from django.core.management.base import BaseCommand
from booking.models import Court

class Command(BaseCommand):
    help = 'Создает начальные корты согласно спецификации'
    
    def handle(self, *args, **kwargs):
        # Удаляем старые корты
        Court.objects.all().delete()
        
        # Крытые корты 1-8 (хард)
        indoor_courts = [
            # Корты 1-4: 1700 в будни, 1500 в выходные
            {'number': 1, 'name': 'Крытый корт 1', 'court_type': 'hard', 'location': 'indoor', 
             'price_weekday': 1700, 'price_weekend': 1500, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            {'number': 2, 'name': 'Крытый корт 2', 'court_type': 'hard', 'location': 'indoor',
             'price_weekday': 1700, 'price_weekend': 1500, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            {'number': 3, 'name': 'Крытый корт 3', 'court_type': 'hard', 'location': 'indoor',
             'price_weekday': 1700, 'price_weekend': 1500, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            {'number': 4, 'name': 'Крытый корт 4', 'court_type': 'hard', 'location': 'indoor',
             'price_weekday': 1700, 'price_weekend': 1500, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            # Корты 5-8: 1300 в будни, 1300 в выходные
            {'number': 5, 'name': 'Крытый корт 5', 'court_type': 'hard', 'location': 'indoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            {'number': 6, 'name': 'Крытый корт 6', 'court_type': 'hard', 'location': 'indoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            {'number': 7, 'name': 'Крытый корт 7', 'court_type': 'hard', 'location': 'indoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            {'number': 8, 'name': 'Крытый корт 8', 'court_type': 'hard', 'location': 'indoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Крытый корт с покрытием хард', 'is_active': True},
            # Уличные корты 9-12 (хард) - не активны зимой
            {'number': 9, 'name': 'Уличный корт 9', 'court_type': 'hard', 'location': 'outdoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Уличный корт с покрытием хард', 'is_active': False},
            {'number': 10, 'name': 'Уличный корт 10', 'court_type': 'hard', 'location': 'outdoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Уличный корт с покрытием хард', 'is_active': False},
            {'number': 11, 'name': 'Уличный корт 11', 'court_type': 'hard', 'location': 'outdoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Уличный корт с покрытием хард', 'is_active': False},
            {'number': 12, 'name': 'Уличный корт 12', 'court_type': 'hard', 'location': 'outdoor',
             'price_weekday': 1300, 'price_weekend': 1300, 'description': 'Уличный корт с покрытием хард', 'is_active': False},
            # Центральный уличный корт
            {'number': 13, 'name': 'Центральный корт', 'court_type': 'hard', 'location': 'outdoor',
             'price_weekday': 1500, 'price_weekend': 1800, 'description': 'Центральный уличный корт (не работает зимой)', 'is_active': False},
            # Грунтовые корты 14-16
            {'number': 14, 'name': 'Грунтовый корт 14', 'court_type': 'clay', 'location': 'outdoor',
             'price_weekday': 1200, 'price_weekend': 1500, 'description': 'Уличный грунтовый корт (не работает зимой)', 'is_active': False},
            {'number': 15, 'name': 'Грунтовый корт 15', 'court_type': 'clay', 'location': 'outdoor',
             'price_weekday': 1200, 'price_weekend': 1500, 'description': 'Уличный грунтовый корт (не работает зимой)', 'is_active': False},
            {'number': 16, 'name': 'Грунтовый корт 16', 'court_type': 'clay', 'location': 'outdoor',
             'price_weekday': 1200, 'price_weekend': 1500, 'description': 'Уличный грунтовый корт (не работает зимой)', 'is_active': False},
        ]
        
        for court_data in indoor_courts:
            Court.objects.create(**court_data)
        
        self.stdout.write(self.style.SUCCESS(f'Успешно создано {Court.objects.count()} кортов'))
        self.stdout.write('Крытые корты 1-8: активны (работают зимой)')
        self.stdout.write('Уличные корты 9-16: не активны (не работают зимой)')