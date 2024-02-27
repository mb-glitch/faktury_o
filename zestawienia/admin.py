from django.contrib import admin

from .models import Serwer, Ustawienia, DaneBazy, DoPoprawy

@admin.register(Serwer, Ustawienia, DoPoprawy)
class ZestawieniaAdmin(admin.ModelAdmin):
    pass


@admin.register(DaneBazy)
class DaneBazyAdmin(admin.ModelAdmin):
    list_display = ['numer_zlecenia',
                    'pacjent',
                    'lekarz',
                    'nazwa_badania',
                    'cena',
                    ]
    list_filter = ['nazwa_platnika', 'serwer']
    search_fields = ['numer_zlecenia',
                     'nazwa_badania',
                     'nazwisko'
                     ]
