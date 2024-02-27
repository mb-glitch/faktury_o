from django.conf.urls import url

from . import views
app_name = 'zestawienia'
urlpatterns = [
        url(r'^$', views.index, name='index'),
        url(r'^pobieranie-danych/$', views.UstawieniaView.as_view(), name='pobieranie_danych'),
        url(r'^zestawienia/$', 
            views.ZestawieniaListView.as_view(), name='zestawienia'),
        url(r'^zestawienia/poprawki$', 
            views.DoPoprawyListView.as_view(), name='poprawki'),
        url(r'^zestawienia/usun_7_16$', 
            views.u_usun_badania_zlecone_7_16, name='usun_badania_zlecone_7_16'),
        url(r'^zestawienia/usun_16_7$', 
            views.u_usun_badania_zlecone_16_7, name='usun_badania_zlecone_16_7'),
        url(r'^zestawienia/usun_sporale$', 
            views.u_usun_sporale, name='usun_sporale'),
        url(r'^zestawienia/przywroc_sporale$', 
            views.u_przywroc_sporale, name='przywroc_sporale'),       
        url(r'^zestawienia/usun_lekarzy$', 
            views.u_usun_lekarzy, name='usun_lekarzy'),
        url(r'^zestawienia/przywroc_lekarzy$', 
            views.u_przywroc_lekarzy, name='przywroc_lekarzy'),
        url(r'^zestawienia/zostaw_tylko_sporale$', 
            views.u_zostaw_tylko_sporale, name='zostaw_tylko_sporale'),
        url(r'^zestawienia/przywroc_wszystko$', 
            views.u_przywroc_wszystko, name='przywroc_wszystko'),
        
        url(r'^zestawienia/(?P<slug>[-\w]+)$', views.lista_zestawien, name='lista_zestawien'),
        url(r'^zestawienia/(?P<slug>[-\w]+)/2fs$', views.zestawienie_2fs, name='2fs'),
        url(r'^zestawienia/(?P<slug>[-\w]+)/2f$', views.zestawienie_2f, name='2f'),
        url(r'^zestawienia/(?P<slug>[-\w]+)/1b$', views.zestawienie_1b, name='1b'),
        url(r'^zestawienia/baza/(?P<slug>[-\w]+)$', views.zestawienie_all, name='zestawienie_all'), 
        ]
