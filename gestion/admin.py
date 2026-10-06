
# gestion/admin.py
from django.contrib import admin
from .models import Ecole, Section, Classe, Eleve, Paiement

@admin.register(Ecole)
class EcoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'telephone', 'date_creation']
    search_fields = ['nom']

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom']
    list_display_links = ['nom']

@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'section']
    list_filter = ['section']
    search_fields = ['nom']

@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ['id', 'matricule', 'nom_complet', 'section', 'classe', 'est_actif', 'date_inscription']
    list_filter = ['section', 'classe', 'est_actif']
    search_fields = ['matricule', 'nom_complet']
    list_editable = ['est_actif']

@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'eleve', 'motif', 'montant', 'type_montant', 
        'statut', 'mois_paye', 'mois_concerne', 'created_by'
    ]
    list_filter = ['statut', 'type_montant', 'annee_scolaire', 'mois_concerne']
    search_fields = ['eleve__nom_complet', 'motif']
    readonly_fields = ['created_by', 'created_at', 'modified_at', 'annule_at']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)