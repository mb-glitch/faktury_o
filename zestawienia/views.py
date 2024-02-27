import time
import datetime

from collections import OrderedDict

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Count, Sum
from django.contrib import messages
from .forms import UstawieniaForm
from .models import DaneBazy, Serwer, Ustawienia, DoPoprawy

from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

def index(requets):
    return HttpResponseRedirect('/zestawienia')

class UstawieniaView(LoginRequiredMixin, FormView):
    template_name = 'zestawienia/zestawienia_form.html'
    form_class = UstawieniaForm
    success_url = '/zestawienia/'

    def form_valid(self, form):
        # usuwam wszystko z aktualnej bazy
        # if form.cleaned_data['usunac_baze']:
        DaneBazy.objects.all().delete()
        Ustawienia.objects.all().delete()
        DoPoprawy.objects.all().delete()

        u = Ustawienia.objects.create(
                            status = Ustawienia.AKTYWNE,
                            data_start = form.cleaned_data['data_start'],
                            data_koniec = form.cleaned_data['data_koniec'],
                            )
        u.save()

        for serwer in form.cleaned_data['serwer']:
            u.serwer.add(serwer)
            data_start = u.data_start
            data_koniec = u.data_koniec

            serwer.polacz_z_baza()
            z = serwer.pobierz_dane(data_start, data_koniec)            
            z = serwer.oczysc_dane_zestawienia(z)
            serwer.rozlacz_z_baza()
            serwer.dodaj_dane_zestawienia_do_bazy(z)
        return super(UstawieniaView, self).form_valid(form)    
    
class ZestawieniaListView(LoginRequiredMixin, ListView):
    model = DaneBazy

    def get_context_data(self, **kwargs):
        context = super(ZestawieniaListView, self).get_context_data(**kwargs)
        context['laboratoria'] = Serwer.objects.order_by('nazwa').all()
        filtr_platnikow = DaneBazy.objects.order_by('nazwa_platnika')
        filtr_platnikow = filtr_platnikow.values_list('nazwa_platnika', 'slug')
        filtr_platnikow = filtr_platnikow.distinct()     
        context['platnicy'] = filtr_platnikow
        u = Ustawienia.objects.get(status=Ustawienia.AKTYWNE)
        context['data_start'] = u.data_start 
        context['data_koniec'] = u.data_koniec
        return context

class DoPoprawyListView(LoginRequiredMixin, ListView):
    model = DoPoprawy
    
    def get_context_data(self, **kwargs):
        context = super(DoPoprawyListView, self).get_context_data(**kwargs)
        context['object_list'] = DoPoprawy.objects. \
                select_related(). \
                values('serwer__nazwa', 'text'). \
                distinct(). \
                order_by('serwer', 'text')
        return context

@login_required
def u_usun_badania_zlecone_7_16(request):
    DaneBazy.objects.filter(data_zlecenia__hour__gte=7). \
        filter(data_zlecenia__hour__lte=16). \
        update(usuniete_z_zestawien=True)
    messages.info(request, 'Badanie zlecone pomiędzy 7:00 a 16:00 usunięte z zestawień')
    return HttpResponseRedirect('/zestawienia')

@login_required
def u_usun_badania_zlecone_16_7(request):
    a = DaneBazy.objects.all()
    a.filter(data_zlecenia__hour__lte=7).update(usuniete_z_zestawien=True)
    a.filter(data_zlecenia__hour__gte=16).update(usuniete_z_zestawien=True)
    messages.info(request, 'Badanie zlecone przed 7:00 oraz po 16:00 usunięte z zestawień')
    return HttpResponseRedirect('/zestawienia')

@login_required
def u_usun_sporale(request):
    DaneBazy.objects.filter(sporal=True).update(usuniete_z_zestawien=True)
    messages.info(request, 'Sporale usunięte z zestawień')
    return HttpResponseRedirect('/zestawienia')

@login_required
def u_usun_lekarzy(request):
    a = DaneBazy.objects.all()
    a.lekarz_usun()
    messages.info(request, 'Lekarze usunięci z zestawień')
    return HttpResponseRedirect('/zestawienia')

@login_required
def u_przywroc_lekarzy(request):
    a = DaneBazy.objects.all()
    for row in a:
        row.lekarz_przywroc()
    messages.info(request, 'Lekarze przywróceni do zestawień')
    return HttpResponseRedirect('/zestawienia')


@login_required
def u_przywroc_sporale(request):
    DaneBazy.objects.filter(sporal=True).update(usuniete_z_zestawien=False)
    messages.info(request, 'Sporale przywrócone do zestawień')
    return HttpResponseRedirect('/zestawienia')

@login_required
def u_zostaw_tylko_sporale(request):
    DaneBazy.objects.filter(sporal=False).update(usuniete_z_zestawien=True)
    messages.info(request, 'W zestawieniach pozostały tylko badania Sporal i ATTEST')
    return HttpResponseRedirect('/zestawienia')

@login_required
def u_przywroc_wszystko(request):
    DaneBazy.objects.all().update(usuniete_z_zestawien=False)
    messages.success(request, 'Wszystkie badania w bazie przywrócone do zestawień')
    return HttpResponseRedirect('/zestawienia')

@login_required
def zestawienie_2fs(request, slug):
    ustawienia = Ustawienia.objects.get(status=Ustawienia.AKTYWNE)
    platnik_dane = DaneBazy.objects.aktywne().filter(slug=slug)
    platnik_nazwa = platnik_dane[0].nazwa_platnika
    
    platnik = OrderedDict()
    platnik['nazwa'] = platnik_nazwa
    platnik['ilosc'] = platnik_dane.count()
    platnik['wartosc'] = platnik_dane.aggregate(wartosc=Sum('cena'))['wartosc']
    platnik['data_start'] = ustawienia.data_start
    platnik['data_koniec'] = ustawienia.data_koniec   
    platnik['badania'] = platnik_dane.oblicz_badanie_ilosc_wartosc()

    return render(request, 'zestawienia/2fs.html', {'platnik': platnik})

@login_required
def zestawienie_2f(request, slug):
    ustawienia = Ustawienia.objects.get(status=Ustawienia.AKTYWNE)
    platnik_dane = DaneBazy.objects.aktywne().filter(slug=slug)
    platnik_nazwa = platnik_dane[0].nazwa_platnika
    
    platnik = OrderedDict()
    platnik['nazwa'] = platnik_nazwa
    platnik['ilosc'] = platnik_dane.count()
    platnik['wartosc'] = platnik_dane.wartosc()
    platnik['data_start'] = ustawienia.data_start
    platnik['data_koniec'] = ustawienia.data_koniec   
    platnik['oddzialy'] = OrderedDict()

    oddzialy_platnika = platnik_dane.nazwy_oddzialow()
    
    for o in oddzialy_platnika:
        nazwa = o['nazwa_oddzialu']
        badania_oddzialu = platnik_dane.filter(nazwa_oddzialu=nazwa)     
        platnik['oddzialy'][nazwa] = OrderedDict()
        platnik['oddzialy'][nazwa]['ilosc'] = badania_oddzialu.count()
        platnik['oddzialy'][nazwa]['wartosc'] = badania_oddzialu.wartosc()        
        platnik['oddzialy'][nazwa]['badania'] = badania_oddzialu.oblicz_badanie_ilosc_wartosc()

    return render(request, 'zestawienia/2f.html', {'platnik': platnik})


@login_required
def zestawienie_1b(request, slug):
    ustawienia = Ustawienia.objects.get(status=Ustawienia.AKTYWNE)
    platnik_dane = DaneBazy.objects.aktywne().filter(slug=slug)
    platnik_nazwa = platnik_dane[0].nazwa_platnika
    
    platnik = OrderedDict()
    platnik['nazwa'] = platnik_nazwa
    platnik['ilosc'] = platnik_dane.count()
    platnik['wartosc'] = platnik_dane.wartosc()
    platnik['data_start'] = ustawienia.data_start
    platnik['data_koniec'] = ustawienia.data_koniec   
    platnik['oddzialy'] = OrderedDict()

    oddzialy_platnika = platnik_dane.nazwy_oddzialow()
    
    for o in oddzialy_platnika:
        nazwa = o['nazwa_oddzialu']
        badania_oddzialu = platnik_dane.filter(nazwa_oddzialu=nazwa)     
        platnik['oddzialy'][nazwa] = OrderedDict()
        platnik['oddzialy'][nazwa]['ilosc'] = badania_oddzialu.count()
        platnik['oddzialy'][nazwa]['wartosc'] = badania_oddzialu.wartosc()        
        platnik['oddzialy'][nazwa]['lekarze'] = OrderedDict()        

        lekarze_oddzialu = badania_oddzialu.nazwy_lekarzy()
        
        for l in lekarze_oddzialu:
            lekarz_nazwisko = l['lekarz_nazwisko']
            lekarz_imie = l['lekarz_imie']
            zlecenia_lekarza = badania_oddzialu.filter(
                    lekarz_nazwisko=lekarz_nazwisko, 
                    lekarz_imie=lekarz_imie
                    )
            lekarz = '{nazwisko} {imie}'.format(
                    imie=lekarz_imie, 
                    nazwisko=lekarz_nazwisko
                    )
            platnik['oddzialy'][nazwa]['lekarze'][lekarz] = OrderedDict()
            platnik['oddzialy'][nazwa]['lekarze'][lekarz]['ilosc'] = zlecenia_lekarza.count()
            platnik['oddzialy'][nazwa]['lekarze'][lekarz]['wartosc'] = zlecenia_lekarza.wartosc()  
            platnik['oddzialy'][nazwa]['lekarze'][lekarz]['zlecenia'] = \
                    zlecenia_lekarza.oblicz_zlecenie_badania_ilosc_wartosc()
    return render(request, 'zestawienia/1b.html', {'platnik': platnik})

@login_required
def zestawienie_all(request, slug):
    ustawienia = Ustawienia.objects.get(status=Ustawienia.AKTYWNE)
    if slug == 'all':
        platnik_dane = DaneBazy.objects.aktywne()
    else:
        serwer = Serwer.objects.filter(nazwa=slug)
        platnik_dane = DaneBazy.objects.aktywne().filter(serwer=serwer)
    
    platnik = OrderedDict()
    platnik['nazwa'] = serwer[0].nazwa if slug != 'all' else 'all'
    platnik['ilosc'] = platnik_dane.count()
    platnik['wartosc'] = platnik_dane.aggregate(wartosc=Sum('cena'))['wartosc']
    platnik['data_start'] = ustawienia.data_start
    platnik['data_koniec'] = ustawienia.data_koniec
    platnik['badania'] = platnik_dane.oblicz_badanie_ilosc_wartosc()

    return render(request, 'zestawienia/2fs.html', {'platnik': platnik})

@login_required
def lista_zestawien(request, slug):
    return render(request, 'zestawienia/lista_zestawien.html', {
                        'platnik': slug,
                        }
                    ) 
