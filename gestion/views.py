
# Create your views here.
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from .models import Eleve, Paiement, Section, Classe, Ecole, Sortie
from .forms import EleveForm, PaiementForm, RechercheEleveForm, SortieForm, AnnulerSortieForm
from datetime import datetime
from calendar import month_name

# ============================================================
# AUTHENTIFICATION
# ============================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('gestion:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"👋 Bienvenue à vous {user.username} !")
            return redirect('gestion:dashboard')
        else:
            messages.error(request, "❌ Nom d'utilisateur ou mot de passe incorrect")
    
    return render(request, 'gestion/login.html')

def logout_view(request):
    logout(request)
    return redirect('gestion:login')

# ============================================================
# TABLEAU DE BORD
# ============================================================

@login_required
def dashboard(request):
    """
    Tableau de bord complet avec :
    - Statistiques des élèves
    - Statistiques des paiements
    - 💰 Gestion de la caisse (Entrées / Sorties / Solde en USD)
    """
    
    # ============================================================
    # 1. STATISTIQUES DES ÉLÈVES
    # ============================================================
    total_eleves = Eleve.objects.filter(est_actif=True).count()
    stats_sections = Section.objects.annotate(total_eleves=Count('eleves'))
    
    # ============================================================
    # 2. STATISTIQUES DES PAIEMENTS
    # ============================================================
    total_paiements = Paiement.objects.count()
    paiements_valides = Paiement.objects.filter(statut='VALIDE').count()
    paiements_invalides = Paiement.objects.filter(statut='INVALIDE').count()
    
    # ============================================================
    # 3. 💰 GESTION DE LA CAISSE (ENTRÉES / SORTIES / SOLDE)
    # ============================================================
    
    # --- TAUX DE CHANGE ---
    TAUX_CHANGE = Decimal('2300')  # 1 USD = 2300 FC
    
    # --- ENTRÉES (Paiements reçus) ---
    entrees_usd = Paiement.objects.filter(
        type_montant='USD', 
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    entrees_fc = Paiement.objects.filter(
        type_montant='FC', 
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # Conversion des FC en USD pour le calcul de la caisse
    entrees_fc_en_usd = entrees_fc / TAUX_CHANGE
    total_entrees_usd = entrees_usd + entrees_fc_en_usd
    
    # --- SORTIES (Dépenses) ---
    sorties_usd = Sortie.objects.filter(
        type_montant='USD',
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    sorties_fc = Sortie.objects.filter(
        type_montant='FC',
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # Conversion des FC en USD
    sorties_fc_en_usd = sorties_fc / TAUX_CHANGE
    total_sorties_usd = sorties_usd + sorties_fc_en_usd
    
    # --- SOLDE DISPONIBLE (en USD) ---
    solde_usd = total_entrees_usd - total_sorties_usd
    
    # Équivalent en FC (pour affichage indicatif)
    solde_fc = solde_usd * TAUX_CHANGE
    
    # ============================================================
    # 4. DERNIERS MOUVEMENTS
    # ============================================================
    derniers_paiements = Paiement.objects.filter(
        statut='VALIDE'
    ).order_by('-created_at')[:10]
    
    dernieres_sorties = Sortie.objects.filter(
        statut='VALIDE'
    ).order_by('-date_sortie', '-created_at')[:10]
    
    # ============================================================
    # 5. STATISTIQUES PAR MOIS (Paiements)
    # ============================================================
    paiements_par_mois = Paiement.objects.filter(statut='VALIDE').values(
        'mois_concerne', 'annee_concerne'
    ).annotate(
        total=Sum('montant'),
        count=Count('id')
    ).order_by('-annee_concerne', '-mois_concerne')[:12]
    
    # ============================================================
    # 6. STATISTIQUES PAR CATÉGORIE (Sorties)
    # ============================================================
    sorties_par_categorie = Sortie.objects.filter(
        statut='VALIDE'
    ).values('categorie').annotate(
        total=Sum('montant'),
        count=Count('id')
    ).order_by('-total')
    
    # ============================================================
    # 7. CONTEXTE
    # ============================================================
    context = {
        # Élèves
        'total_eleves': total_eleves,
        'stats_sections': stats_sections,
        
        # Paiements
        'total_paiements': total_paiements,
        'paiements_valides': paiements_valides,
        'paiements_invalides': paiements_invalides,
        'derniers_paiements': derniers_paiements,
        'paiements_par_mois': paiements_par_mois,
        
        # 💰 CAISSE - ENTRÉES
        'entrees_usd': entrees_usd,
        'entrees_fc': entrees_fc,
        'total_entrees_usd': total_entrees_usd,
        
        # 💰 CAISSE - SORTIES
        'sorties_usd': sorties_usd,
        'sorties_fc': sorties_fc,
        'total_sorties_usd': total_sorties_usd,
        
        # 💰 CAISSE - SOLDE
        'solde_usd': solde_usd,
        'solde_fc': solde_fc,
        'taux_change': TAUX_CHANGE,
        
        # Dernières sorties
        'dernieres_sorties': dernieres_sorties,
        'sorties_par_categorie': sorties_par_categorie,
    }
    
    return render(request, 'gestion/dashboard.html', context)

# ============================================================
# 💰 SORTIES (DÉPENSES)
# ============================================================

@login_required
def enregistrer_sortie(request):
    """Vue pour enregistrer une sortie de caisse"""
    if request.method == 'POST':
        form = SortieForm(request.POST)
        if form.is_valid():
            sortie = form.save(commit=False)
            sortie.created_by = request.user
            sortie.save()
            
            messages.success(
                request, 
                f"✅ Sortie de {sortie.montant} {sortie.type_montant} enregistrée !"
            )
            return redirect('gestion:historique_sorties')
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs ci-dessous.")
    else:
        form = SortieForm()
    
    return render(request, 'gestion/enregistrer_sortie.html', {'form': form})


@login_required
def modifier_sortie(request, sortie_id):
    """Vue pour modifier une sortie"""
    sortie = get_object_or_404(Sortie, id=sortie_id)
    
    if request.method == 'POST':
        form = SortieForm(request.POST, instance=sortie)
        if form.is_valid():
            sortie_modifiee = form.save(commit=False)
            sortie_modifiee.modified_by = request.user
            sortie_modifiee.save()
            
            messages.success(request, f"✅ Sortie modifiée avec succès !")
            return redirect('gestion:historique_sorties')
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs ci-dessous.")
    else:
        form = SortieForm(instance=sortie)
    
    return render(request, 'gestion/modifier_sortie.html', {
        'form': form,
        'sortie': sortie,
    })


@login_required
def supprimer_sortie(request, sortie_id):
    """Vue pour supprimer une sortie"""
    sortie = get_object_or_404(Sortie, id=sortie_id)
    
    if request.method == 'POST':
        designation = sortie.designation
        montant = sortie.montant
        sortie.delete()
        messages.warning(request, f"🗑️ Sortie '{designation}' ({montant}) supprimée !")
        return redirect('gestion:historique_sorties')
    
    return render(request, 'gestion/supprimer_sortie.html', {'sortie': sortie})


@login_required
def annuler_sortie(request, sortie_id):
    """Vue pour annuler une sortie (changer le statut)"""
    sortie = get_object_or_404(Sortie, id=sortie_id)
    
    if request.method == 'POST':
        form = AnnulerSortieForm(request.POST)
        if form.is_valid():
            sortie.statut = 'ANNULE'
            sortie.annule_by = request.user
            sortie.annule_at = datetime.now()
            sortie.raison_annulation = form.cleaned_data['raison_annulation']
            sortie.save()
            
            messages.warning(request, f"⛔ Sortie annulée avec succès !")
            return redirect('gestion:historique_sorties')
    else:
        form = AnnulerSortieForm()
    
    return render(request, 'gestion/annuler_sortie.html', {
        'form': form,
        'sortie': sortie,
    })


@login_required
def historique_sorties(request):
    """Vue pour l'historique des sorties avec filtres"""
    sorties = Sortie.objects.all().order_by('-date_sortie', '-created_at')
    
    # Filtres
    categorie = request.GET.get('categorie')
    statut = request.GET.get('statut')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    if categorie:
        sorties = sorties.filter(categorie=categorie)
    if statut:
        sorties = sorties.filter(statut=statut)
    if date_debut:
        sorties = sorties.filter(date_sortie__gte=date_debut)
    if date_fin:
        sorties = sorties.filter(date_sortie__lte=date_fin)
    
    # Totaux
    total_usd = sorties.filter(
        type_montant='USD', statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    total_fc = sorties.filter(
        type_montant='FC', statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    context = {
        'sorties': sorties,
        'total_sorties': sorties.count(),
        'total_usd': total_usd,
        'total_fc': total_fc,
        'categories': Sortie.CATEGORIES,
    }
    return render(request, 'gestion/historique_sorties.html', context)

# ============================================================
# ÉLÈVES
# ============================================================

@login_required
def ajouter_eleve(request):
    if request.method == 'POST':
        form = EleveForm(request.POST)
        if form.is_valid():
            eleve = form.save()
            messages.success(request, f"✅ Élève {eleve.nom_complet} inscrit avec succès !")
            return redirect('gestion:liste_eleves')
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs ci-dessous.")
    else:
        form = EleveForm()
    
    return render(request, 'gestion/ajouter_eleve.html', {'form': form})

@login_required
def liste_eleves(request):
    form = RechercheEleveForm(request.GET or None)
    eleves = Eleve.objects.filter(est_actif=True).order_by('nom_complet')
    
    if form.is_valid() and form.cleaned_data.get('nom'):
        nom = form.cleaned_data.get('nom')
        eleves = eleves.filter(nom_complet__icontains=nom)
    
    context = {
        'form': form,
        'eleves': eleves,
        'total_eleves': eleves.count(),
    }
    return render(request, 'gestion/liste_eleves.html', context)

@login_required
def detail_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    paiements = Paiement.objects.filter(eleve=eleve).order_by('-created_at')
    
    total_paye_fc = paiements.filter(type_montant='FC', statut='VALIDE').aggregate(
        total=Sum('montant'))['total'] or 0
    total_paye_usd = paiements.filter(type_montant='USD', statut='VALIDE').aggregate(
        total=Sum('montant'))['total'] or 0
    
    #  Paiements par mois pour cet élève
    paiements_par_mois = paiements.filter(statut='VALIDE').values(
        'mois_concerne', 'annee_concerne'
    ).annotate(
        total=Sum('montant')
    ).order_by('-annee_concerne', '-mois_concerne')
    
    context = {
        'eleve': eleve,
        'paiements': paiements,
        'total_paye_fc': total_paye_fc,
        'total_paye_usd': total_paye_usd,
        'paiements_par_mois': paiements_par_mois,
    }
    return render(request, 'gestion/detail_eleve.html', context)

# ============================================================
# PAIEMENTS
# ============================================================

# gestion/views.py
@login_required
def enregistrer_paiement(request):
    # Récupérer les paramètres GET
    eleve_id = request.GET.get('eleve_id')
    
    
    if request.method == 'POST':
        form = PaiementForm(request.POST)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.created_by = request.user
            paiement.save()
            
            mois_noms = dict(Paiement.MOIS_CHOICES)
            messages.success(
                request, 
                f"✅ Paiement de {paiement.montant} {paiement.type_montant} enregistré ! "
                f"📅 Payé en {mois_noms[paiement.mois_paye]} {paiement.annee_paye} "
                f"pour {mois_noms[paiement.mois_concerne]} {paiement.annee_concerne}"
            )
            return redirect('gestion:detail_eleve', eleve_id=paiement.eleve.id)
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs ci-dessous.")
    else:
        # ✅ Pré-remplir le formulaire avec les paramètres
        initial_data = {}
        if eleve_id:
            try:
                eleve = Eleve.objects.get(id=eleve_id)
                initial_data['eleve'] = eleve
            except Eleve.DoesNotExist:
                pass
        
        form = PaiementForm(initial=initial_data)
    
    return render(request, 'gestion/enregistrer_paiement.html', {'form': form})

@login_required
def historique_paiements(request):
    """
    Historique des paiements avec filtres avancés :
    - Élève (recherche par nom ou matricule)
    - Statut (VALIDE / INVALIDE / ANNULE)
    - Devise (FC / USD)
    - Mois concerné
    - Année concernée
    - Date de début / fin
    """
    
    # ============================================================
    # 1. REQUÊTE DE BASE
    # ============================================================
    paiements = Paiement.objects.all().order_by('-created_at')
    
    # ============================================================
    # 2. RÉCUPÉRATION DES FILTRES (GET)
    # ============================================================
    eleve_nom = request.GET.get('eleve_nom', '').strip()
    statut = request.GET.get('statut', '').strip()
    type_montant = request.GET.get('type_montant', '').strip()
    mois = request.GET.get('mois', '').strip()
    annee = request.GET.get('annee', '').strip()
    date_debut = request.GET.get('date_debut', '').strip()
    date_fin = request.GET.get('date_fin', '').strip()
    
    # ============================================================
    # 3. APPLICATION DES FILTRES
    # ============================================================
    
    # 🔍 Filtre par nom d'élève ou matricule
    if eleve_nom:
        paiements = paiements.filter(
            Q(eleve__nom_complet__icontains=eleve_nom) |
            Q(eleve__matricule__icontains=eleve_nom)
        )
    
    # ✅ Filtre par statut
    if statut:
        paiements = paiements.filter(statut=statut)
    
    # 💰 Filtre par devise
    if type_montant:
        paiements = paiements.filter(type_montant=type_montant)
    
    # 📅 Filtre par mois concerné
    if mois:
        try:
            paiements = paiements.filter(mois_concerne=int(mois))
        except (ValueError, TypeError):
            pass
    
    # 📅 Filtre par année concernée
    if annee:
        try:
            paiements = paiements.filter(annee_concerne=int(annee))
        except (ValueError, TypeError):
            pass
    
    # 📅 Filtre par date de début (création)
    if date_debut:
        try:
            paiements = paiements.filter(created_at__date__gte=date_debut)
        except (ValueError, TypeError):
            pass
    
    # 📅 Filtre par date de fin (création)
    if date_fin:
        try:
            paiements = paiements.filter(created_at__date__lte=date_fin)
        except (ValueError, TypeError):
            pass
    
    # ============================================================
    # 4. CALCUL DES TOTAUX (selon les filtres appliqués)
    # ============================================================
    total_usd = paiements.filter(
        type_montant='USD',
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    total_fc = paiements.filter(
        type_montant='FC',
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # ============================================================
    # 5. CONTEXTE
    # ============================================================
    context = {
        'paiements': paiements,
        'total_paiements': paiements.count(),
        'total_usd': total_usd,
        'total_fc': total_fc,
        
        # Choix pour les filtres
        'mois_choices': Paiement.MOIS_CHOICES,
        'statut_choices': Paiement.STATUT_CHOICES,
        'type_choices': Paiement.TYPES_MONTANT,
        
        # Valeurs actuelles des filtres (pour pré-remplir les champs)
        'filtre_eleve_nom': eleve_nom,
        'filtre_statut': statut,
        'filtre_type_montant': type_montant,
        'filtre_mois': mois,
        'filtre_annee': annee,
        'filtre_date_debut': date_debut,
        'filtre_date_fin': date_fin,
    }
    
    return render(request, 'gestion/historique_paiements.html', context)
# ============================================================
# RAPPORT
# ============================================================

# gestion/views.py
from .models import Sortie
from decimal import Decimal

@login_required
def rapport(request):
    
    # ============================================================
    # 1. TAUX DE CHANGE
    # ============================================================
    TAUX_CHANGE = Decimal('2300')
    
    # ============================================================
    # 2. PAIEMENTS PAR MOIS (pour le tableau des statistiques)
    # ============================================================
    paiements_par_mois = Paiement.objects.filter(
        statut='VALIDE'
    ).values(
        'mois_concerne',
        'annee_concerne',
        'type_montant'
    ).annotate(
        total=Sum('montant'),
        count=Count('id')
    ).order_by('-annee_concerne', '-mois_concerne', 'type_montant')

    # ============================================================
    # 3. TOTAUX GÉNÉRAUX (tous les paiements)
    # ============================================================
    total_fc = Paiement.objects.filter(
        type_montant='FC', statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    total_usd = Paiement.objects.filter(
        type_montant='USD', statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    total_usd_en_fc = total_usd * TAUX_CHANGE
    total_general_fc = total_fc + total_usd_en_fc
    
    total_fc_en_usd = total_fc / TAUX_CHANGE
    total_general_usd = total_usd + total_fc_en_usd

    # ============================================================
    # 4. ÉVOLUTION (12 derniers mois) EN USD
    # ============================================================
    evolution_data = []
    for mois in range(1, 13):
        total_fc_mois = Paiement.objects.filter(
            mois_concerne=mois, type_montant='FC', statut='VALIDE'
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        total_usd_mois = Paiement.objects.filter(
            mois_concerne=mois, type_montant='USD', statut='VALIDE'
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        total_fc_en_usd_mois = total_fc_mois / TAUX_CHANGE
        total_general_mois = total_usd_mois + total_fc_en_usd_mois
        
        evolution_data.append({
            'mois': mois,
            'nom_mois': month_name[mois][:3],
            'total': total_general_mois,
            'count': Paiement.objects.filter(mois_concerne=mois, statut='VALIDE').count(),
        })

    # ============================================================
    # 5. MONTANT ANTÉRIEUR (en USD)
    # ============================================================
    mois_actuel = datetime.now().month
    annee_actuelle = datetime.now().year
    
    premier_mois_graph = mois_actuel - 11
    premiere_annee_graph = annee_actuelle
    if premier_mois_graph <= 0:
        premier_mois_graph += 12
        premiere_annee_graph -= 1

    montant_anterieur_fc = Paiement.objects.filter(
        statut='VALIDE', type_montant='FC'
    ).exclude(
        mois_concerne__gte=premier_mois_graph,
        annee_concerne__gte=premiere_annee_graph
    ).exclude(
        mois_concerne__lt=premier_mois_graph,
        annee_concerne__gt=premiere_annee_graph
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

    montant_anterieur_usd = Paiement.objects.filter(
        statut='VALIDE', type_montant='USD'
    ).exclude(
        mois_concerne__gte=premier_mois_graph,
        annee_concerne__gte=premiere_annee_graph
    ).exclude(
        mois_concerne__lt=premier_mois_graph,
        annee_concerne__gt=premiere_annee_graph
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    montant_anterieur = (montant_anterieur_fc / TAUX_CHANGE) + montant_anterieur_usd
    total_periode = total_general_usd - montant_anterieur

    # ============================================================
    # 6. POURCENTAGES
    # ============================================================
    if total_general_usd > 0:
        pourcentage_anterieur = (montant_anterieur / total_general_usd) * Decimal('100')
        pourcentage_fc = (total_fc / total_general_fc) * Decimal('100')
        pourcentage_usd = (total_usd / total_general_usd) * Decimal('100')
    else:
        pourcentage_anterieur = Decimal('0')
        pourcentage_fc = Decimal('0')
        pourcentage_usd = Decimal('0')

    # ============================================================
    # 7. SORTIES (DÉPENSES)
    # ============================================================
    sorties_usd = Sortie.objects.filter(
        type_montant='USD', statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    sorties_fc = Sortie.objects.filter(
        type_montant='FC', statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    sorties_fc_en_usd = sorties_fc / TAUX_CHANGE
    total_sorties_usd = sorties_usd + sorties_fc_en_usd

    # ============================================================
    # 8. SOLDE DISPONIBLE
    # ============================================================
    solde_usd = total_general_usd - total_sorties_usd
    solde_fc = solde_usd * TAUX_CHANGE

    # ============================================================
    # 9. TOP 10 PAYEURS
    # ============================================================
    top_eleves = Paiement.objects.filter(
        statut='VALIDE', type_montant='USD'
    ).values('eleve__nom_complet').annotate(
        total_paye=Sum('montant')
    ).order_by('-total_paye')[:10]

    # ============================================================
    # 10. TOTAL PAIEMENTS
    # ============================================================
    total_paiements = Paiement.objects.filter(statut='VALIDE').count()

    # ============================================================
    # 11. CONTEXTE COMPLET
    # ============================================================
    context = {
        # ✅ PAIEMENTS PAR MOIS (pour le tableau)
        'paiements_par_mois': paiements_par_mois,
        
        # Totaux généraux
        'total_paiements': total_paiements,
        'montant_total_fc': total_fc,
        'montant_total_usd': total_usd,
        'total_general_fc': total_general_fc,
        'total_general_usd': total_general_usd,
        'taux_change': TAUX_CHANGE,
        
        # Évolution
        'evolution_data': evolution_data,
        'total_periode': total_periode,
        'montant_anterieur': montant_anterieur,
        'pourcentage_anterieur': pourcentage_anterieur,
        
        # Répartition
        'pourcentage_fc': pourcentage_fc,
        'pourcentage_usd': pourcentage_usd,
        
        # Top payeurs
        'top_eleves': top_eleves,
        
        # 💰 CAISSE
        'entrees_usd': total_usd,
        'entrees_fc': total_fc,
        'total_entrees_usd': total_general_usd,
        
        'sorties_usd': sorties_usd,
        'sorties_fc': sorties_fc,
        'total_sorties_usd': total_sorties_usd,
        
        'solde_usd': solde_usd,
        'solde_fc': solde_fc,
    }
    
    return render(request, 'gestion/rapport.html', context)# ============================================================
# ✏️ MODIFIER UN PAIEMENT
# ============================================================
@login_required
def modifier_paiement(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)
    eleve = paiement.eleve
    
    if request.method == 'POST':
        form = PaiementForm(request.POST, instance=paiement)
        if form.is_valid():
            # 🔐 TRACABILITÉ : Enregistrer qui a modifié
            paiement_modifie = form.save(commit=False)
            paiement_modifie.modified_by = request.user
            
            # Stocker l'historique des modifications
            historique = paiement_modifie.historique_modifications or []
            historique.append({
                'date': str(datetime.now()),
                'utilisateur': request.user.username,
                'champs_modifies': 'Voir les changements ci-dessus'
            })
            paiement_modifie.historique_modifications = historique
            
            paiement_modifie.save()
            messages.success(request, f"✅ Paiement de {paiement_modifie.montant} {paiement_modifie.type_montant} modifié avec succès !")
            return redirect('gestion:detail_eleve', eleve_id=eleve.id)
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PaiementForm(instance=paiement)
    
    return render(request, 'gestion/modifier_paiement.html', {
        'form': form,
        'paiement': paiement,
        'eleve': eleve,
    })

# ============================================================
# 🗑️ SUPPRIMER UN PAIEMENT
# ============================================================
@login_required
def supprimer_paiement(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)
    eleve = paiement.eleve
    
    if request.method == 'POST':
        # 🔐 TRACABILITÉ : Enregistrer la suppression
        montant = paiement.montant
        type_montant = paiement.type_montant
        motif = paiement.motif
        
        paiement.delete()
        messages.warning(request, f"🗑️ Paiement de {montant} {type_montant} ({motif}) supprimé avec succès !")
        return redirect('gestion:detail_eleve', eleve_id=eleve.id)
    
    return render(request, 'gestion/supprimer_paiement.html', {
        'paiement': paiement,
        'eleve': eleve,
    })
# ============================================================
# API
# ============================================================

def api_get_classes(request):
    """API pour récupérer les classes d'une section"""
    section_id = request.GET.get('section')
    if section_id:
        classes = Classe.objects.filter(section_id=section_id).values('id', 'nom')
        return JsonResponse({'classes': list(classes)})
    return JsonResponse({'classes': []})

def api_recherche_eleve(request):
    """
    API pour rechercher un élève par nom ou matricule
    Utilisée par Select2 pour les suggestions en temps réel
    """
    term = request.GET.get('term', '').strip()
    
    # Recherche uniquement si au moins 2 caractères
    if len(term) < 2:
        return JsonResponse({'results': []})
    
    # Recherche par nom ou matricule
    eleves = Eleve.objects.filter(
        Q(nom_complet__icontains=term) |
        Q(matricule__icontains=term)
    ).filter(est_actif=True)[:15]  # Limite à 15 résultats
    
    # Formatage des résultats pour Select2
    results = [{
        'id': e.id,
        'text': f"{e.nom_complet} ({e.matricule}) - {e.classe.nom}",
        'nom_complet': e.nom_complet,
        'matricule': e.matricule,
        'classe': e.classe.nom,
        'section': e.section.get_nom_display(),
    } for e in eleves]
    
    return JsonResponse({'results': results})

@login_required
def annuler_paiement(request, paiement_id):
    """Vue pour annuler un paiement (changer le statut)"""
    paiement = get_object_or_404(Paiement, id=paiement_id)
    
    if request.method == 'POST':
        paiement.statut = 'ANNULE'
        paiement.annule_by = request.user
        paiement.annule_at = datetime.now()
        paiement.save()
        
        messages.warning(request, f"⛔ Paiement annulé avec succès !")
        return redirect('gestion:historique_paiements')
    
    return render(request, 'gestion/annuler_paiement.html', {'paiement': paiement})