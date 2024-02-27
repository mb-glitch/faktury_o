import subprocess
import pymssql
import time
import datetime
import os
import signal
import shlex
from collections import OrderedDict

from django.db import models
from django.utils.text import slugify
from .mssql import ZapytaniaSql as sql

from django.db.models import Count, Sum
from django.db import connection, transaction # na potrzeby VACUUM


class Serwer(models.Model):
    SSH = 'ssh -p 53232 -L {port}:{ip}:{lokalny_port_bazy} -N -f maciek@*********'
    
    nazwa = models.CharField(max_length=100)
    baza_nazwa = models.CharField(max_length=100)
    baza_port = models.IntegerField()
    baza_lokalny_port_bazy = models.IntegerField()
    baza_ip = models.CharField(max_length=20)
    odprawione = models.BooleanField(default=True)

    def __str__(self):
        return self.nazwa

    class Meta:
        verbose_name_plural = "Serwery"
    
    def ssh_command(self):
        command = self.SSH.format(
                port=self.baza_port, 
                ip=self.baza_ip, 
                lokalny_port_bazy=self.baza_lokalny_port_bazy
                )
        return shlex.split(command)


    def ssh_connect(self):
        try:
            self.ssh_conn = subprocess.Popen(
                self.ssh_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
                )
        except:
            pass
        while self.ssh_conn.poll()==None:
            time.sleep(1)

    def ssh_disconnect(self):
        try:
            self.ssh_conn.terminate()
            self.ssh_conn.wait()
        except:
            pass

    def polacz_z_baza(self):
        _serwer = "127.0.0.1"
        _port = self.baza_port
        _user = "ADMIN"
        _password = "***"
        _database = self.baza_nazwa
        
        self.ssh_connect()
        try:
            self.conn = pymssql.connect(
                 server = _serwer,
                 port = _port,
                 user = _user,
                 password = _password,
                 database = _database,
                 charset = 'cp1250'
                 )
        except pymssql.OperationalError:
            print('Nie udało połączyć się z bazą', self.nazwa)
            time.sleep(60)
            self.polacz_z_baza()

    def rozlacz_z_baza(self):
        self.conn.close()
        self.ssh_disconnect()
    
    def ustaw_date_wykonania_dla_nieodprawionych(self, row):
        if not self.odprawione:
            row['DATA_ODPRAWIENIA'] = row['DATA_ZLECENIA']
        return row

    def usun_pesel_jezeli_brak(self, row):
        row = row
        if '      ' in row['PESEL']:
            row['PESEL'] = ''
        return row
    
    def sprawdz_czy_sporal(self, row):
        row['SPORAL'] = False
        if 'SPORAL' in str(row['NAZWA_MATERIALU']).upper():
            row['SPORAL'] = True
        elif 'ATTEST' in str(row['NAZWA_MATERIALU']).upper():
            row['SPORAL'] = True
        elif 'SPORAL' in str(row['NAZWA_BADANIA']).upper():
            row['SPORAL'] = True
        elif 'ATTEST' in str(row['NAZWA_BADANIA']).upper():
            row['SPORAL'] = True
        return row        

    def dodaj_do_poprawy(self, text):
        d = DoPoprawy.objects.create(serwer=self, text=text)
        d.save()
    
    def dodaj_do_poprawy_jezeli_pusta_cena(self, row):
        if row['CENA'] == None:
            text = 'Płatnik: {platnik} --- Brak ceny badania: {badanie}'.format(
                        badanie=row['NAZWA_BADANIA'],
                        platnik=row['NAZWA_PLATNIKA']
                        )
            self.dodaj_do_poprawy(text)

    def tabela_oddzial_platnik(self):
        with self.conn.cursor() as cursor:
            cursor.execute(sql.sql5)
            return cursor.fetchall()
    
    def dodaj_do_poprawy_jezeli_zly_platnik(self, row, tabela_oddzial_platnik):
        if (row['ID_ODDZIALU'], row['ID_PLATNIKA']) not in tabela_oddzial_platnik:
            text = 'Błędny płatnik! Numer zlecenia: {zlecenie} z dnia: {data_zlecenia}'.format(
                        zlecenie=row['NUMER_ZLECENIA'],
                        data_zlecenia=row['DATA_ZLECENIA']
                        )
            self.dodaj_do_poprawy(text)

    def zmien_nazwy_posiewow(self, row):
        row = row
        if row['NAZWA_BADANIA'] == 'Posiew':
            row['NAZWA_BADANIA'] = row['NAZWA_MATERIALU']
            row['CENA'] = row['CENA_MATERIALU']
            with self.conn.cursor() as cursor:
                cursor.execute(sql.sql3.format(row['ID_MASTER_POSIEW']))
                ile_antybiogramow = cursor.fetchall()
                if ile_antybiogramow:
                    ile_antybiogramow = max(ile_antybiogramow)[0]  # [0] bo max daje listę
                    if 'MOCZ' in row['NAZWA_MATERIALU']:
                        if row['CENA']:
                            row['CENA'] += sql.ANTYBIOGRM[row['NAZWA_PLATNIKA']]['MOCZ'][ile_antybiogramow]
                            row['NAZWA_BADANIA'] += ' ({} x antybiogram)'.format(ile_antybiogramow) 
                    elif ('MYKO' in row['NAZWA_MATERIALU']) or ('GRZYB' in row['NAZWA_MATERIALU']):
                        if row['CENA']:
                            row['CENA'] += sql.ANTYBIOGRM[row['NAZWA_PLATNIKA']]['MOCZ'][ile_antybiogramow]
                        row['NAZWA_BADANIA'] += ' ({} x mykogram)'.format(ile_antybiogramow) 
                    else:
                        if row['CENA']:
                            row['CENA'] += sql.ANTYBIOGRM[row['NAZWA_PLATNIKA']]['INNY'][ile_antybiogramow]
                        row['NAZWA_BADANIA'] += ' ({} x antybiogram)'.format(ile_antybiogramow) 
        return row 

    def oczysc_dane_zestawienia(self, zestawienie_listadict):
        zestawienie = zestawienie_listadict
        zestawienie_filtr = list()
        tabela_oddzial_platnik = self.tabela_oddzial_platnik()
        for row in zestawienie:
            row = self.zmien_nazwy_posiewow(row)
            row = self.usun_pesel_jezeli_brak(row)
            row = self.ustaw_date_wykonania_dla_nieodprawionych(row)
            row = self.sprawdz_czy_sporal(row)
            self.dodaj_do_poprawy_jezeli_pusta_cena(row)
            self.dodaj_do_poprawy_jezeli_zly_platnik(row, tabela_oddzial_platnik)
            zestawienie_filtr.append(row)

        return zestawienie_filtr
    
    def oczysc_baze_sqlite(self):
        cursor = connection.cursor()
        # Data modifying operation - commit required
        cursor.execute("VACUUM")
        transaction.commit()
    
    def dodaj_dane_zestawienia_do_bazy(self, zestawienie_listadict):
        zestawienie = zestawienie_listadict
        lista_wpisow = list()
        for row in zestawienie:
            lista_wpisow.append(DaneBazy(
                nazwa_badania = row['NAZWA_BADANIA'],
                ilosc_wykonan = 1,
                data_odprawienia = row['DATA_ODPRAWIENIA'],
                cena = row['CENA'],
                nazwa_oddzialu = row['NAZWA_ODDZIALU'],
                data_zlecenia =row['DATA_ZLECENIA'],
                numer_zlecenia =row['NUMER_ZLECENIA'],
                nazwisko =row['NAZWISKO'],      
                imie = row['IMIE'],
                pesel= row['PESEL'],
                data_urodzenia = row['DATA_URODZENIA'],
                lekarz_nazwisko = row['LEKARZ_NAZWISKO'],
                lekarz_imie = row['LEKARZ_IMIE'],
                lekarz_nazwisko_usuniete = row['LEKARZ_NAZWISKO'],
                lekarz_imie_usuniete = row['LEKARZ_IMIE'],
                nazwa_platnika = row['NAZWA_PLATNIKA'], 
                slug = slugify(row['NAZWA_PLATNIKA']), 
                serwer  = self,
                usuniete_z_zestawien = False,
                sporal = row['SPORAL']
                ))
        self.oczysc_baze_sqlite()
        DaneBazy.objects.bulk_create(lista_wpisow)



    def pobierz_dane(self, data_start, data_koniec):
        conn = self.conn
        _data_start = data_start.strftime("%Y-%m-%d %H:%M:%S")
        _data_koniec = data_koniec.strftime("%Y-%m-%d %H:%M:%S")
        _odprawione = 'T' if self.odprawione else 'N'
        _odprawione_daty = sql.ODPRAWIONY if self.odprawione else sql.NIEODPRAWIONY
        _odprawione_daty = _odprawione_daty.format(data_start=_data_start, data_koniec=_data_koniec)
        _sql1 = sql.sql1.format(
                            odprawione=_odprawione, 
                            odprawione_daty=_odprawione_daty
                            )
        _sql2 = sql.sql2.format(
                            odprawione=_odprawione, 
                            odprawione_daty=_odprawione_daty
                            )
        _sql_list = [_sql1, _sql2]
        _zestawienie = list()

        for sql_command in _sql_list:
            with conn.cursor(as_dict=True) as cursor:
                cursor.execute(sql_command)
                _zestawienie += cursor.fetchall()
        return _zestawienie


class DoPoprawy(models.Model):
    text = models.CharField(max_length=300)
    serwer = models.ForeignKey(Serwer)

    def __str__(self):
        return self.text
    
    
    class Meta:
        verbose_name_plural = "Do poprawy"

class Ustawienia(models.Model):
    AKTYWNE = 'a'
    NIEAKTYWNE = 'n'
    
    STATUS_CHOICES = (
            (AKTYWNE, 'Bierzące, aktywne ustawienia'),
            (NIEAKTYWNE, 'Stare, nieaktywne ustawienia'),
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    serwer = models.ManyToManyField(Serwer)
    data_start = models.DateTimeField()
    data_koniec = models.DateTimeField()
    usunac_baze = models.BooleanField(default=True)


    class Meta:
        verbose_name_plural = "Ustawienia"


class DaneBazyQuerySet(models.QuerySet):
    
    def aktywne(self):
        return self.filter(usuniete_z_zestawien=False)
    
    def oblicz_badanie_ilosc_wartosc(self):
        return self.values('nazwa_badania', 'cena'). \
            annotate(ilosc=Count('nazwa_badania')). \
            annotate(wartosc=Sum('cena')). \
            order_by('nazwa_badania') 
    
    def numery_zlecen(self):
        return self.values(
                'numer_zlecenia', 
                'imie',
                'nazwisko',
                'pesel',
                'data_urodzenia',
                'data_zlecenia',
                'data_odprawienia',
                ). \
                distinct().order_by('data_odprawienia') 

    def wartosc(self):
        return self.aggregate(wartosc=Sum('cena'))['wartosc']

    def oblicz_zlecenie_badania_ilosc_wartosc(self):
        numery_zlecen = self.numery_zlecen()
        zlecenia = OrderedDict()
        for zlecenie in numery_zlecen:
            numer_zlecenia = zlecenie['numer_zlecenia']
            badania_zlecenia = self.filter(numer_zlecenia=numer_zlecenia)
            zlecenia[numer_zlecenia] = zlecenie 
            zlecenia[numer_zlecenia]['ilosc'] = badania_zlecenia.count()
            zlecenia[numer_zlecenia]['wartosc'] = badania_zlecenia.wartosc()
            zlecenia[numer_zlecenia]['badania'] = badania_zlecenia.values_list('nazwa_badania', flat=True)
        return zlecenia 
        
    def nazwy_oddzialow(self):
        return self.values('nazwa_oddzialu').distinct().order_by('nazwa_oddzialu')

    def nazwy_lekarzy(self):
        return self.values('lekarz_nazwisko', 'lekarz_imie'). \
                distinct().order_by('lekarz_nazwisko', 'lekarz_imie')
    
    def lekarz_usun(self):
        self.update(lekarz_imie='', lekarz_nazwisko = 'Bez podziału na lekarzy')

class DaneBazy(models.Model):
    nazwa_badania = models.CharField(max_length=100, blank=True)
    ilosc_wykonan = models.IntegerField(default=1)
    data_odprawienia = models.DateTimeField(null=True, blank=True)
    cena = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    nazwa_oddzialu = models.CharField(max_length=100)
    data_zlecenia = models.DateTimeField(null=True, blank=True)
    numer_zlecenia = models.IntegerField(null=True, blank=True)
    nazwisko = models.CharField(max_length=100, blank=True)
    imie = models.CharField(max_length=100, blank=True)
    pesel  = models.CharField(max_length=100, blank=True)
    data_urodzenia = models.DateField(null=True, blank=True)
    lekarz_nazwisko = models.CharField(max_length=100, blank=True)
    lekarz_imie = models.CharField(max_length=100, blank=True, null=True)
    lekarz_nazwisko_usuniete = models.CharField(max_length=100, blank=True)
    lekarz_imie_usuniete = models.CharField(max_length=100, blank=True, null=True)
    nazwa_platnika = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True, null=True)
    serwer  = models.ForeignKey(Serwer)
    usuniete_z_zestawien = models.BooleanField(default=False)
    sporal = models.BooleanField(default=False)

    objects = DaneBazyQuerySet.as_manager()

    def __str__(self):
        return self.nazwa_badania

    def pacjent(self):
        pesel_lub_rok = self.pesel if self.pesel else self.data_urodzenia
        return '{} {}, {}'.format(self.imie, self.nazwisko, pesel_lub_rok)
    
    def lekarz(self):
        return '{} {}'.format(self.lekarz_nazwisko, self.lekarz_imie)



    def lekarz_przywroc(self):
        self.lekarz_imie = self.lekarz_imie_usuniete
        self.lekarz_nazwisko = self.lekarz_nazwisko_usuniete
        self.save()


    class Meta:
        verbose_name_plural = "Dane z bazy"



