# gestion/forms.py
from django import forms
from .models import Eleve, Paiement, Classe, Section, Ecole
from django.contrib.auth.models import User
from datetime import datetime

# ============================================================
# FORMULAIRE ÉLÈVE
# ============================================================
class EleveForm(forms.ModelForm):
    """Formulaire d'inscription d'un élève"""
    
    class Meta:
        model = Eleve
        fields = ['ecole', 'matricule', 'nom_complet', 'section', 'classe', 'option', 'telephone_parent']
        widgets = {
            'ecole': forms.Select(attrs={'class': 'form-select'}),
            'matricule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: YK2026001'}),
            'nom_complet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet de l\'élève'}),
            'section': forms.Select(attrs={'class': 'form-select', 'id': 'id_section'}),
            'classe': forms.Select(attrs={'class': 'form-select', 'id': 'id_classe'}),
            'option': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Scientifique, Littéraire...'}),
            'telephone_parent': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 0812345678'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classe'].queryset = Classe.objects.none()
        self.fields['option'].required = False
        self.fields['ecole'].empty_label = "Sélectionner une école"
        self.fields['section'].empty_label = "Sélectionner une section"
        self.fields['classe'].empty_label = "Sélectionner une classe"
        
        if 'section' in self.data:
            try:
                section_id = int(self.data.get('section'))
                self.fields['classe'].queryset = Classe.objects.filter(section_id=section_id).order_by('nom')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['classe'].queryset = self.instance.section.classes.order_by('nom')

    def clean_option(self):
        option = self.cleaned_data.get('option')
        classe = self.cleaned_data.get('classe')
        section = self.cleaned_data.get('section')
        
        if section and section.nom == 'SECONDAIRE':
            if classe and classe.nom in ['1e', '2e', '3e', '4e'] and not option:
                raise forms.ValidationError("L'option est obligatoire pour les classes 1e à 4e du secondaire")
        
        return option
    
    def clean_nom_complet(self):
        nom = self.cleaned_data.get('nom_complet')
        if len(nom.strip()) < 3:
            raise forms.ValidationError("Le nom complet doit contenir au moins 3 caractères")
        return nom.strip().upper()
    
    def clean_matricule(self):
        matricule = self.cleaned_data.get('matricule')
        if Eleve.objects.filter(matricule=matricule).exists():
            raise forms.ValidationError("Ce matricule existe déjà")
        return matricule.upper()

# ============================================================
# FORMULAIRE PAIEMENT (AVEC MOIS)
# ============================================================
class PaiementForm(forms.ModelForm):
    """Formulaire d'enregistrement d'un paiement avec mois"""
    
    class Meta:
        model = Paiement
        fields = [
            'ecole', 'eleve', 'motif', 'annee_scolaire',
            'montant', 'type_montant', 'statut',
            'mois_paye', 'annee_paye',      #: mois payé
            'mois_concerne', 'annee_concerne',  #: mois concerné
            'notes'
        ]
        widgets = {
            'ecole': forms.Select(attrs={'class': 'form-select'}),
            'eleve': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_eleve',
                'placeholeder': 'Tapez le nom...',
                'autocomplete': 'off'}),
            'motif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Frais scolaires'}),
            'annee_scolaire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2025-2026'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'step': '0.01'}),
            'type_montant': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'mois_paye': forms.Select(attrs={'class': 'form-select'}),
            'annee_paye': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2025'}),
            'mois_concerne': forms.Select(attrs={'class': 'form-select'}),
            'annee_concerne': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2025'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes supplémentaires...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        self.fields['ecole'].empty_label = "Sélectionner une école"
        self.fields['eleve'].empty_label = "Sélectionner un élève"
        self.fields['type_montant'].initial = 'FC'
        self.fields['statut'].initial = 'VALIDE'
        
        # 📅 Initialisation des mois avec la date actuelle
        self.fields['mois_paye'].initial = current_month
        self.fields['annee_paye'].initial = current_year
        self.fields['mois_concerne'].initial = current_month
        self.fields['annee_concerne'].initial = current_year
    
    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à 0")
        return montant
    
    def clean(self):
        cleaned_data = super().clean()
        mois_paye = cleaned_data.get('mois_paye')
        annee_paye = cleaned_data.get('annee_paye')
        mois_concerne = cleaned_data.get('mois_concerne')
        annee_concerne = cleaned_data.get('annee_concerne')
        
        # Vérification que l'année de paiement n'est pas dans le futur
        current_year = datetime.now().year
        if annee_paye and annee_paye > current_year:
            raise forms.ValidationError("L'année de paiement ne peut pas être dans le futur")
        
        return cleaned_data

# ============================================================
# FORMULAIRE DE RECHERCHE
# ============================================================
class RechercheEleveForm(forms.Form):
    """Formulaire de recherche d'élève par nom"""
    nom = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher un élève par son nom complet...'
        })
    )