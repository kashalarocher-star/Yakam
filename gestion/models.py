

# Create your models here.
# gestion/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from datetime import datetime


# ============================================================
# MODÈLE ÉCOLE
# ============================================================
class Ecole(models.Model):
    """Modèle pour les écoles"""
    nom = models.CharField(max_length=200, unique=True)
    adresse = models.CharField(max_length=300, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = "École"
        verbose_name_plural = "Écoles"

# ============================================================
# MODÈLE SECTION
# ============================================================
class Section(models.Model):
    """Modèle pour les sections scolaires"""
    NOM_SECTIONS = [
        ('PRIMAIRE', 'Primaire'),
        ('SECONDAIRE', 'Secondaire'),
        ('MATERNELLE', 'Maternelle'),
    ]
    nom = models.CharField(max_length=20, choices=NOM_SECTIONS, unique=True)
    
    def __str__(self):
        return self.get_nom_display()
    
    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"

# ============================================================
# MODÈLE CLASSE
# ============================================================
class Classe(models.Model):
    """Modèle pour les classes"""
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='classes')
    nom = models.CharField(max_length=10)
    
    class Meta:
        unique_together = ['section', 'nom']
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
    
    def __str__(self):
        return f"{self.section.get_nom_display()} - {self.nom}"

# ============================================================
# MODÈLE ÉLÈVE
# ============================================================
class Eleve(models.Model):
    """Modèle pour les élèves"""
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='eleves', null=True, blank=True)
    matricule = models.CharField(max_length=20, unique=True)
    nom_complet = models.CharField(max_length=200, db_index=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='eleves')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='eleves')
    option = models.CharField(max_length=100, blank=True, null=True)
    telephone_parent = models.CharField(max_length=20, blank=True, null=True)
    date_inscription = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.matricule} - {self.nom_complet}"
    
    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"

# ============================================================
# MODÈLE PAIEMENT (AVEC MOIS)
# ============================================================
class Paiement(models.Model):
    """Modèle pour les paiements avec suivi des mois"""
    
    TYPES_MONTANT = [
        ('FC', 'FC'),
        ('USD', 'USD'),
    ]
    
    STATUT_CHOICES = [
        ('VALIDE', '✅ Valide'),
        ('INVALIDE', '❌ Invalide'),
        ('ANNULE', '⛔ Annulé'),
    ]
    
    MOIS_CHOICES = [
        (1, 'Janvier'), (2, 'Février'), (3, 'Mars'),
        (4, 'Avril'), (5, 'Mai'), (6, 'Juin'),
        (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'),
        (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre'),
    ]
    
    # --- Informations du paiement ---
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='paiements', null=True, blank=True)
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='paiements')
    motif = models.CharField(max_length=200)
    annee_scolaire = models.CharField(max_length=20)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    type_montant = models.CharField(max_length=3, choices=TYPES_MONTANT, default='FC')
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='INVALIDE')
    notes = models.TextField(blank=True, null=True)
    
    # ---  NOUVEAU : Suivi des mois ---
    mois_paye = models.IntegerField(choices=MOIS_CHOICES, help_text="Mois où le paiement a été effectué")
    mois_concerne = models.IntegerField(choices=MOIS_CHOICES, help_text="Mois pour lequel le paiement est effectué")
    annee_paye = models.IntegerField(default=datetime.now().year, help_text="Année où le paiement a été effectué")
    annee_concerne = models.IntegerField(default=datetime.now().year, help_text="Année pour laquelle le paiement est effectué")
    
    # ---  TRACABILITÉ FINANCIÈRE ---
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_crees')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_modifies')
    modified_at = models.DateTimeField(auto_now=True)
    annule_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_annules')
    annule_at = models.DateTimeField(null=True, blank=True)
    raison_annulation = models.TextField(blank=True, null=True)
    
    # Historique des modifications (stocké en JSON)
    historique_modifications = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"{self.eleve.nom_complet} - {self.motif} - {self.montant} {self.type_montant} ({self.get_mois_concerne_display()} {self.annee_concerne})"
    
    def save(self, *args, **kwargs):
        # Si le statut passe à ANNULE, on enregistre la date d'annulation
        if self.statut == 'ANNULE' and not self.annule_at:
            from django.utils import timezone
            self.annule_at = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-created_at']
        
class Sortie(models.Model):
    """
    Modèle pour les sorties de caisse (dépenses de l'école)
    """
    CATEGORIES = [
        ('FOURNITURES', 'Achat fournitures'),
        ('ELECTRICITE', 'Électricité'),
        ('EAU', 'Eau'),
        ('LOYER', 'Loyer'),
        ('SALAIRES', 'Salaires'),
        ('REPARATION', 'Réparation'),
        ('TRANSPORT', 'Transport'),
        ('FRAIS_ADMIN', 'Frais administratifs'),
        ('AUTRE', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('VALIDE', '✅ Valide'),
        ('ANNULE', '⛔ Annulé'),
    ]
    
    ecole = models.ForeignKey(
        'Ecole', 
        on_delete=models.CASCADE, 
        related_name='sorties', 
        null=True, 
        blank=True
    )
    designation = models.CharField(max_length=200)
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='AUTRE')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    type_montant = models.CharField(
        max_length=3, 
        choices=[('FC', 'FC'), ('USD', 'USD')], 
        default='USD'
    )
    date_sortie = models.DateField(default=datetime.now)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='VALIDE')
    
    # 🔐 TRACABILITÉ
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sorties_creees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sorties_modifiees'
    )
    modified_at = models.DateTimeField(auto_now=True)
    annule_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sorties_annulees'
    )
    annule_at = models.DateTimeField(null=True, blank=True)
    raison_annulation = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.designation} - {self.montant} {self.type_montant}"
    
    class Meta:
        verbose_name = "Sortie"
        verbose_name_plural = "Sorties"
        ordering = ['-date_sortie', '-created_at']        