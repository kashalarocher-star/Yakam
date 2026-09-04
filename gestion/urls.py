# gestion/urls.py
from django.urls import path
from . import views

app_name = 'gestion'

urlpatterns = [
    # Authentification
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Élèves
    path('eleves/', views.liste_eleves, name='liste_eleves'),
    path('eleves/ajouter/', views.ajouter_eleve, name='ajouter_eleve'),
    path('eleves/<int:eleve_id>/', views.detail_eleve, name='detail_eleve'),
    
    # Paiements
    path('paiements/enregistrer/', views.enregistrer_paiement, name='enregistrer_paiement'),
    path('paiements/historique/', views.historique_paiements, name='historique_paiements'),
    path("paiements/modifier/<int:paiement_id>", views.modifier_paiement, name="modifier_paiement"),
    path('paiements/supprimer/int<int:paiement_id>/', views.supprimer_paiement, name='supprimer_paiement'),
    
    # Rapport
    path('rapport/', views.rapport, name='rapport'),
    
    # API
    path('api/get-classes/', views.api_get_classes, name='api_get_classes'),
    path('api/recherche-eleve/', views.api_recherche_eleve, name='api_recherche_eleve'),
]