# gestion/management/commands/init_data.py
"""
COMMANDE D'INITIALISATION DES DONNÉES - YAKAM
Exécutez : python manage.py init_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from gestion.models import Section, Classe, Ecole


class Command(BaseCommand):
    help = 'Initialise les données de base pour l\'application YAKAM'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🚀 INITIALISATION DES DONNÉES YAKAM'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # ============================================================
        # 1. CRÉATION DES SECTIONS
        # ============================================================
        self.stdout.write('\n📌 Création des sections...')
        sections_data = ['PRIMAIRE', 'SECONDAIRE', 'MATERNELLE']
        sections = {}

        for nom in sections_data:
            section, created = Section.objects.get_or_create(nom=nom)
            sections[nom] = section
            if created:
                self.stdout.write(f'  ✅ Section "{section.get_nom_display()}" créée')
            else:
                self.stdout.write(f'  ⏳ Section "{section.get_nom_display()}" existe déjà')

        # ============================================================
        # 2. CRÉATION DES CLASSES
        # ============================================================
        self.stdout.write('\n📌 Création des classes...')

        # 2.1. MATERNELLE : 1A à 6D
        section = sections['MATERNELLE']
        lettres = ['A', 'B', 'C', 'D']
        count_maternelle = 0

        for niveau in range(1, 7):
            for lettre in lettres:
                nom = f'{niveau}{lettre}'
                classe, created = Classe.objects.get_or_create(section=section, nom=nom)
                if created:
                    count_maternelle += 1
                    self.stdout.write(f'  ✅ MATERNELLE - {nom} créée')

        self.stdout.write(f'  📊 Maternelle : {count_maternelle} classes créées')

        # 2.2. PRIMAIRE : 1A à 6D
        section = sections['PRIMAIRE']
        count_primaire = 0

        for niveau in range(1, 7):
            for lettre in lettres:
                nom = f'{niveau}{lettre}'
                classe, created = Classe.objects.get_or_create(section=section, nom=nom)
                if created:
                    count_primaire += 1
                    self.stdout.write(f'  ✅ PRIMAIRE - {nom} créée')

        self.stdout.write(f'  📊 Primaire : {count_primaire} classes créées')

        # 2.3. SECONDAIRE : 1e à 8e
        section = sections['SECONDAIRE']
        count_secondaire = 0

        for i in range(1, 9):
            nom = f'{i}e'
            classe, created = Classe.objects.get_or_create(section=section, nom=nom)
            if created:
                count_secondaire += 1
                self.stdout.write(f'  ✅ SECONDAIRE - {nom} créée')

        self.stdout.write(f'  📊 Secondaire : {count_secondaire} classes créées')

        # ============================================================
        # 3. CRÉATION D'UNE ÉCOLE PAR DÉFAUT
        # ============================================================
        self.stdout.write('\n📌 Création de l\'école par défaut...')

        ecole, created = Ecole.objects.get_or_create(
            nom="YAKAM School",
            defaults={
                'adresse': 'Kinshasa, RDC',
                'telephone': '+243 999 999 999'
            }
        )
        if created:
            self.stdout.write(f'  ✅ École "{ecole.nom}" créée')
        else:
            self.stdout.write(f'  ⏳ École "{ecole.nom}" existe déjà')

        # ============================================================
        # 4. CRÉATION D'UN ADMIN PAR DÉFAUT
        # ============================================================
        self.stdout.write('\n📌 Création du compte administrateur...')

        admin_username = 'admin'
        admin_password = 'admin123'
        admin_email = 'admin@yakam.com'

        if not User.objects.filter(username=admin_username).exists():
            User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )
            self.stdout.write(f'  ✅ Admin "{admin_username}" créé')
            self.stdout.write(f'  🔑 Mot de passe : {admin_password}')
            self.stdout.write(f'  📧 Email : {admin_email}')
        else:
            self.stdout.write(f'  ⏳ Admin "{admin_username}" existe déjà')

        # ============================================================
        # 5. RÉSUMÉ
        # ============================================================
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 RÉSUMÉ DES DONNÉES CRÉÉES'))
        self.stdout.write('=' * 60)

        self.stdout.write(f'\n🏫 Sections : {Section.objects.count()}')
        for section in Section.objects.all():
            classes = Classe.objects.filter(section=section).count()
            self.stdout.write(f'   ├─ {section.get_nom_display()} : {classes} classes')

        self.stdout.write(f'\n🏫 Écoles : {Ecole.objects.count()}')
        for ecole in Ecole.objects.all():
            self.stdout.write(f'   ├─ {ecole.nom}')

        self.stdout.write(f'\n👤 Utilisateurs : {User.objects.count()}')
        self.stdout.write(f'   ├─ Admins : {User.objects.filter(is_superuser=True).count()}')
        self.stdout.write(f'   ├─ Staff : {User.objects.filter(is_staff=True).count()}')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ INITIALISATION TERMINÉE AVEC SUCCÈS !'))
        self.stdout.write('=' * 60)

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🔑 IDENTIFIANTS DE CONNEXION'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'   👤 Nom d\'utilisateur : {admin_username}')
        self.stdout.write(f'   🔑 Mot de passe      : {admin_password}')
        self.stdout.write('=' * 60)

        self.stdout.write('\n🌐 Pour vous connecter : http://127.0.0.1:8000/login/')
        self.stdout.write('\n🚀 Pour lancer le serveur : python manage.py runserver\n')