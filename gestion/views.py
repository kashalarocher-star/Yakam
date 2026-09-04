
# Create your views here.
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from .models import Eleve, Paiement, Section, Classe, Ecole
from .forms import EleveForm, PaiementForm, RechercheEleveForm
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
    total_eleves = Eleve.objects.filter(est_actif=True).count()
    stats_sections = Section.objects.annotate(total_eleves=Count('eleves'))
    
    total_paiements = Paiement.objects.count()
    paiements_valides = Paiement.objects.filter(statut='VALIDE').count()
    paiements_invalides = Paiement.objects.filter(statut='INVALIDE').count()
    
    montant_fc = Paiement.objects.filter(type_montant='FC', statut='VALIDE').aggregate(
        total=Sum('montant'))['total'] or 0
    montant_usd = Paiement.objects.filter(type_montant='USD', statut='VALIDE').aggregate(
        total=Sum('montant'))['total'] or 0
    
    derniers_paiements = Paiement.objects.filter(statut='VALIDE').order_by('-created_at')[:10]
    
    #  Statistiques par mois
    paiements_par_mois = Paiement.objects.filter(statut='VALIDE').values(
        'mois_concerne', 'annee_concerne'
    ).annotate(
        total=Sum('montant'),
        count=Count('id')
    ).order_by('-annee_concerne', '-mois_concerne')[:12]
    
    context = {
        'total_eleves': total_eleves,
        'stats_sections': stats_sections,
        'total_paiements': total_paiements,
        'paiements_valides': paiements_valides,
        'paiements_invalides': paiements_invalides,
        'montant_fc': montant_fc,
        'montant_usd': montant_usd,
        'derniers_paiements': derniers_paiements,
        'paiements_par_mois': paiements_par_mois,
    }
    return render(request, 'gestion/dashboard.html', context)

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
    paiements = Paiement.objects.all().order_by('-created_at')
    
    eleve_id = request.GET.get('eleve')
    statut = request.GET.get('statut')
    mois = request.GET.get('mois')
    
    if eleve_id:
        paiements = paiements.filter(eleve_id=eleve_id)
    if statut:
        paiements = paiements.filter(statut=statut)
    if mois:
        paiements = paiements.filter(mois_concerne=mois)
    
    context = {
        'paiements': paiements,
        'total_paiements': paiements.count(),
    }
    return render(request, 'gestion/historique_paiements.html', context)

# ============================================================
# RAPPORT
# ============================================================

@login_required
def rapport(request):
    paiements_par_mois = Paiement.objects.filter(
        statut='VALIDE'
    ).values(
        'mois_concerne',
        'annee_concerne',
        'type_montant'
    ).annotate(
        total=Sum('montant'),
        count=Count('id')
    ).order_by('-mois_concerne','-annee_concerne', 'type_montant')
    
    print(f" Nombre de groupe : {paiements_par_mois.count()}")
    for p in paiements_par_mois:
        print(f"  Mois: {p['mois_concerne']}, Anne: {p['annee_concerne']}, Count: {p['count']}, total: {p['total']}")
    # ============================================================
    # 1. TOTAUX GÉNÉRAUX (tous les paiements)
    # ============================================================
    TAUX_CHANGE = Decimal('2300')
    
    total_fc = Paiement.objects.filter(
        type_montant='FC',
        statut='VALIDE'  # ✅ CORRECTION : statut, pas status
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    total_usd = Paiement.objects.filter(
        type_montant='USD',
        statut='VALIDE'  # ✅ CORRECTION : statut, pas status
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    total_usd_en_fc = total_usd * TAUX_CHANGE
    total_general_fc = total_fc + total_usd_en_fc
    
    total_fc_en_usd = total_fc / TAUX_CHANGE
    total_general_usd = total_usd + total_fc_en_usd

    # ============================================================
    # 2. ÉVOLUTION (12 derniers mois)
    # ============================================================
    mois_actuel = datetime.now().month
    annee_actuelle = datetime.now().year

    evolution_data = []
    for mois in range(1, 13):
        
        total_fc_mois = Paiement.objects.filter(
            mois_concerne=mois,
            type_montant='FC',
            statut='VALIDE'
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

        total_usd_mois = Paiement.objects.filter(
            mois_concerne=mois,
            type_montant='USD',
            statut='VALIDE'
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

        total_usd_en_fc_mois = total_usd_mois * TAUX_CHANGE
        total_general_mois = total_fc_mois + total_usd_en_fc_mois
        
        evolution_data.append({
            'mois': mois,
            'nom_mois': month_name[mois][:3],
            'total': total_general_mois,
            'count': Paiement.objects.filter(
                mois_concerne=mois,
                statut='VALIDE'
            ).count(),
        })

    # ============================================================
    # 3. MONTANT ANTÉRIEUR (paiements avant la période)
    # ============================================================
    premier_mois_graph = mois_actuel - 11
    premiere_annee_graph = annee_actuelle
    if premier_mois_graph <= 0:
        premier_mois_graph += 12
        premiere_annee_graph -= 1
    
    # ✅ CORRECTION : Exclure correctement la période
    montant_anterieur = Paiement.objects.filter(
        statut='VALIDE'
    ).exclude(
        # On exclut les paiements de la période du graphique
        mois_concerne__gte=premier_mois_graph,
        annee_concerne__gte=premiere_annee_graph
    ).exclude(
        # On exclut aussi les cas où le mois est < premier_mois_graph
        # mais l'année est > premiere_annee_graph
        mois_concerne__lt=premier_mois_graph,
        annee_concerne__gt=premiere_annee_graph
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # ============================================================
    # 4. TOTAL DE LA PÉRIODE (somme des barres)
    # ============================================================
    total_periode = total_general_fc - montant_anterieur  # ✅ Plus simple et fiable
    
    # ============================================================
    # 5. POURCENTAGE ANTÉRIEUR
    # ============================================================
    if total_general_fc > 0:
        pourcentage_anterieur = (montant_anterieur / total_general_fc) * Decimal('100')  # ✅ 100, pas 10
    else:
        pourcentage_anterieur = Decimal('0')
    
    # ============================================================
    # 6. RÉPARTITION FC / USD
    # ============================================================
    if total_general_fc > 0:
        pourcentage_fc = (total_fc / total_general_fc) * Decimal('100')
        pourcentage_usd = (total_usd_en_fc / total_general_fc) * Decimal('100')
    else:
        pourcentage_fc = Decimal('0')
        pourcentage_usd = Decimal('0')
    
    # ============================================================
    # 7. TOP 10 PAYEURS
    # ============================================================
    top_eleves = Paiement.objects.filter(
        statut='VALIDE',  # ✅ CORRECTION : statut, pas status
        type_montant='USD'
    ).values('eleve__nom_complet').annotate(
        total_paye=Sum('montant')
    ).order_by('-total_paye')[:10]
    
    # ============================================================
    # 8. TOTAL PAIEMENTS
    # ============================================================
    total_paiements = Paiement.objects.filter(statut='VALIDE').count()
    
    # ============================================================
    # 9. CONTEXTE
    # ============================================================
    context = {
        'evolution_data': evolution_data,
        'total_periode': total_periode,
        'montant_anterieur': montant_anterieur,
        'pourcentage_anterieur': pourcentage_anterieur,
        'total_general_fc': total_general_fc,
        'total_general_usd': total_general_usd,
        'total_paiements': total_paiements,
        'montant_total_fc': total_fc,
        'montant_total_usd': total_usd,
        'pourcentage_fc': pourcentage_fc,
        'pourcentage_usd': pourcentage_usd,
        'taux_change': TAUX_CHANGE,
        'top_eleves': top_eleves,
        'paiements_par_mois': paiements_par_mois,
    }
    
    return render(request, 'gestion/rapport.html', context)

# ============================================================
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