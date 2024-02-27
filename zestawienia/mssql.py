class ZapytaniaSql:
    ODPRAWIONY = "probki.DATA_ODPRAWIENIA BETWEEN CAST('{data_start}' AS DateTime) AND CAST('{data_koniec}' AS DateTime)"
    NIEODPRAWIONY = "zlecenie_badania.DATA_ZLECENIA BETWEEN CAST('{data_start}' AS DateTime) AND CAST('{data_koniec}' AS DateTime)"

    # ustawiam na sztywno ceny antybiogramów
    # pozycja w liście oznacza ile kosztuje tyle antybiogramów, 0 antybiogramów kosztuje 0, potem sumy
    ANTYBIOGRM = {
    'wszystko':{'MOCZ':[0, 0, 0, 0, 0, 0, 0], 'INNY':[0, 0, 0, 0, 0, 0, 0], 'MYKO':[0, 20, 40, 60, 80, 100]},
        }
    
    # grupy badań
    sql1 = """
    select GRUPY_BADAN.NAZWA_GRUPY,
    probki.ILOSC_WYKONAN,
    probki.DATA_ODPRAWIENIA,
    dane_personelu.NAZWISKO,
    dane_personelu.IMIE,
    listamaterialow.NAZWA as NAZWA_MATERIALU,
    posiew_master.ID_MASTER_POSIEW
    from zlecenie_badania
    join probki on zlecenie_badania.ID_ZLECENIA = probki.ID_ZLECENIA
    join GRUPY_BADAN on GRUPY_BADAN.ID_GRUPY = probki.ID_PROFILU
    join dane_personelu on dane_personelu.ID_PERSONELU = zlecenie_badania.LEKARZ_ZLECAJACY
    full outer join listamaterialow on probki.KOD_MATERIALU = listamaterialow.KOD
    full outer join posiew_master on zlecenie_badania.ID_ZLECENIA = posiew_master.ID_ZLECENIA
    where
    GRUPY_BADAN.ZLEC_W_CAL = 'T'
    and
    probki.PROF_ODPRAWIONY = 'T'
    """
    # badania nie zlecone w całości
    sql2 = """
    select BADANIA.NAZWA_BADANIA, 
    WYNIKI_BADAN.ILOSC_WYKONAN,
    probki.DATA_ODPRAWIENIA,
    ceny_badan.CENA,
    ceny_materialow.CENA as CENA_MATERIALU,
    oddzialy.NAZWA_ODDZIALU,
    oddzialy.ID_ODDZIALU,
    zlecenie_badania.DATA_ZLECENIA,
    zlecenie_badania.NUMER_ZLECENIA,
    PACJENCI.NAZWISKO,
    PACJENCI.IMIE,
    PACJENCI.PESEL,
    PACJENCI.DATA_URODZENIA,
    dane_personelu.NAZWISKO as LEKARZ_NAZWISKO,
    dane_personelu.IMIE as LEKARZ_IMIE,
    platnik.NAZWA_PLATNIKA,
    platnik.ID_PLATNIKA,
    listamaterialow.NAZWA as NAZWA_MATERIALU,
    posiew_master.ID_MASTER_POSIEW
    from WYNIKI_BADAN
    join zlecenie_badania on zlecenie_badania.ID_ZLECENIA = WYNIKI_BADAN.ID_ZLECENIA
    join probki on WYNIKI_BADAN.ID_ZLECENIA = probki.ID_ZLECENIA
    and WYNIKI_BADAN.ID_PROFILU = probki.ID_PROFILU
    join GRUPY_BADAN on GRUPY_BADAN.ID_GRUPY = probki.ID_PROFILU
    join BADANIA on BADANIA.ID_BADANIA = WYNIKI_BADAN.ID_BADANIA
    full outer join platnik on zlecenie_badania.ID_PLATNIKA = platnik.ID_PLATNIKA
    full outer join ceny_badan on ceny_badan.ID_CENY = platnik.ID_TYPU_CENY
    and ceny_badan.ID_BADANIA = WYNIKI_BADAN.ID_BADANIA
    full outer join ceny_materialow on ceny_materialow.ID_CENY = platnik.ID_TYPU_CENY
    and ceny_materialow.KOD_MATERIALU = probki.KOD_MATERIALU
    join oddzialy on oddzialy.ID_ODDZIALU = zlecenie_badania.ID_ODDZIALU
    join PACJENCI on PACJENCI.ID_PACJENTA = zlecenie_badania.ID_PACJENTA
    join dane_personelu on dane_personelu.ID_PERSONELU = zlecenie_badania.LEKARZ_ZLECAJACY
    full outer join listamaterialow on probki.KOD_MATERIALU = listamaterialow.KOD
    full outer join posiew_master on zlecenie_badania.ID_ZLECENIA = posiew_master.ID_ZLECENIA
    where
    GRUPY_BADAN.ZLEC_W_CAL = 'N'
    and
    BADANIA.NIE_UWZGL_STAT = 'N'
    and
    probki.PROF_ODPRAWIONY = '{odprawione}'
    and
    {odprawione_daty}
    """
    # zapytanie mikrobiologiczne, sprawdza i ilość antybiogramów
    sql3 = """		
    SELECT posiew_antybiogram.LP
    FROM posiew_antybiogram
    WHERE
    posiew_antybiogram.ID_MASTER_POSIEW = {}
    ORDER BY posiew_antybiogram.LP
    """
    
    # pobierz tabelę płatnik-oddział
    # po zmianie rejestracji czasami zostaje stary id płatnika
    # wtedy pojawia się zła cena
    sql5 = """
    select platnik_oddzial.ID_ODDZIALU, platnik_oddzial.ID_PLATNIKA_PRZYP
    from platnik_oddzial
    """
    # pobierz nazwę oddziału
    sql4 = """
    select oddzialy.ID_ODDZIALU, oddzialy.NAZWA_ODDZIALU
    from klinika_oddzial
    join kliniki on kliniki.ID_KLINIKI = klinika_oddzial.ID_KLINIKI
    join oddzialy on klinika_oddzial.ID_ODDZIALU = oddzialy.ID_ODDZIALU
    where kliniki.NAZWA = '{}'
    """
    sql4all = """
    select oddzialy.ID_ODDZIALU, oddzialy.NAZWA_ODDZIALU
    from oddzialy
    where oddzialy.NIEAKTYWNY = 'N'
    """



