from offres_emploi import Api
from offres_emploi.utils import dt_to_str_iso
import datetime
import time
import pandas as pd
import matplotlib.pyplot as plt
import tweepy
import apprise

# Get today's date
today = datetime.datetime.today()
# Yesterday date
yesterday = today - datetime.timedelta(days = 1)

mois_en_francais = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
]
jours_semaine_en_francais = [
    'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'
]
jour_semaine_today = jours_semaine_en_francais[today.weekday()]
mois_today = mois_en_francais[today.month - 1]
heure_today = today.strftime('%H:%M')
jour_semaine_yesterday = jours_semaine_en_francais[yesterday.weekday()]
mois_yesterday = mois_en_francais[yesterday.month - 1]
heure_yesterday = yesterday.strftime('%H:%M')


# API pole emploi
client = Api(client_id="API is free on Francetravail.io",
             client_secret="secret")

# recherche global :
basic_search = client.search()

print()
print("Nombre total d'offre disponible sur l'API pole emploi : \n")
bs = basic_search['Content-Range']
nombre_total_offre = bs["max_results"]
print(nombre_total_offre)
print()

# recherche avec paramètres
start_dt = yesterday
end_dt = today
# recherche par liste de commune (boucle for) plus pertinente
departement = 69
region = 69
sort = 2 # Tri par distance croissante, pertinence décroissante, date de création décroissante
communes_de_recherche = [69381, 69382, 69383, 69384, 69385, 69386, 69387, 69388, 69389, 69266] # Attention utiliser les code INSSE et pas de code postal

distance = 10  # Spécificité de la ville de Lyon, l’ensemble des offres de Lyon sont remontées dès que le centre de Lyon est atteint par le rayon de distance recherché.

# https://pole-emploi.io/data/api/offres-emploi?tabgroup-api=documentation&doc-section=api-doc-section-rechercher-par-crit%C3%A8res

parametres = []
for each in communes_de_recherche :
     box = {
          "commune": each,
          "sort": sort,
          'minCreationDate': dt_to_str_iso(start_dt),
          'maxCreationDate': dt_to_str_iso(end_dt)
     }
     parametres.append(box)

# recherche pour chaques communes =
print(f"Je recherche les offres d'emploi de la journée des communes suivantes : {communes_de_recherche}")


#creer un dataframe vide
big_job_df = pd.DataFrame()

for param_commune in parametres :

     search_on_big_data = client.search(params=param_commune)
     results =  search_on_big_data['resultats']
     search = search_on_big_data['Content-Range']
     nombre_depuis_hier = search["max_results"]

     # division euclidienne pour obtenir le nombre de page et le reste
     nb_pages = int(nombre_depuis_hier) // 150
     nb_pages_reste = int(nombre_depuis_hier) % 150

     debutpage = 0
     nombre_de_ligne_max_par_page = 150
     liste_pages = []
     for i in range(nb_pages):
          finpage = debutpage + nombre_de_ligne_max_par_page - 1
          liste_pages.append(f"{debutpage}-{finpage}")
          debutpage = finpage + 1
     if nb_pages_reste > 0:
          liste_pages.append(f"{debutpage}-{debutpage + nb_pages_reste - 1}")
     print("voici les pages : ")
     print(liste_pages)
     print()

     #creer un dataframe vide
     job_df = pd.DataFrame()

     for page in liste_pages :

          # ajouter le paramètre page (range) à param
          def ajouter_parametre_range(range_value):
               param_commune["range"] = range_value
          ajouter_parametre_range(page)
          print(param_commune)

          search_on_big_data = client.search(params=param_commune)
          results =  search_on_big_data['resultats']
          # enregistrer les résultats dans un dataframe
          results_df = pd.DataFrame(results)
          job_df = pd.concat([job_df, results_df])
          # alimenter un plus gros dataframe
          big_job_df = pd.concat([big_job_df, job_df])

          time.sleep(0.5)

# travail sur big_job_df de simplification
# supprimer les doubles car rayon de recherche si commune limitrophe
big_job_df = big_job_df.drop_duplicates("id")

# 1) Simplifier lieuTravail dans le dataframe par la valeur "commune" du sous dictionnaire attention les DOM TOM n'on pas de commune
commune = []
for each in big_job_df["lieuTravail"] :
     commune.append(each['libelle'])
# rajouter la collone au dataframe :
big_job_df["ville"] = commune

# 1bis) Code postal pour vérification des filtres de l'API
code_postal = []
for each in big_job_df["lieuTravail"] :
     if "commune" in each :
          code_postal.append(each['commune'])
     else :
          code_postal.append("Pas d'information")
big_job_df["code_postal"] = code_postal

# 2) simplifier entreprise par le nom sans la description de l'entreprise.
entreprise = []
for each in big_job_df["entreprise"] :
     if "nom" in each :
          entreprise.append(each['nom'])
     else :
          entreprise.append("Pas d'information")
big_job_df["nom_entreprise"] = entreprise

# 3) idem pour les salaires, idée : utiliser une AI ou regular expression pour les trier facilement

salaires_simple = []
for each in big_job_df["salaire"] :
     if "libelle" in each :
          salaires_simple.append(each['libelle'])
     else :
          salaires_simple.append("Pas d'information")
big_job_df["info_salaire"] = salaires_simple


job_par_type = big_job_df.value_counts("typeContratLibelle")

top_10 = job_par_type.head(10)
top_10 = top_10.sort_values(ascending=True)

plt.figure(figsize=(20, 11))
plt.barh(top_10.index, top_10.values.T)
# Ajouter les valeurs numériques au-dessus de chaque barre
for i in range(len(top_10.index)):
    plt.text(top_10.values[i], i, str(top_10.values[i]), va='center')
plt.xlabel("Nombre d'annonce sur pole emploi")
plt.xticks(rotation=0)
plt.ylabel("Type de contrat")
plt.title("Top 10 des offres d'emploi par type de contrat", fontsize=30, pad=30)
plt.suptitle(f"Du {jour_semaine_yesterday} {yesterday.day} {mois_yesterday} {heure_yesterday} au {jour_semaine_today} {today.day} {mois_today} {heure_today} à Lyon", horizontalalignment='center')
plt.tight_layout()
plt.grid(True, linestyle='--', alpha=0.5)
plt.savefig("type", dpi=200)
# plt.show()

job_par_rome = big_job_df.value_counts("appellationlibelle")

top_10 = job_par_rome.head(10)
top_10 = top_10.sort_values(ascending=True)

plt.figure(figsize=(20, 11))
plt.barh(top_10.index, top_10.values.T)
# Ajouter les valeurs numériques au-dessus de chaque barre
for i in range(len(top_10.index)):
    plt.text(top_10.values[i], i, str(top_10.values[i]), va='center')
plt.xlabel("Nombre d'annonce sur pole emploi")
plt.xticks(rotation=0)
plt.ylabel("Code ROME")
plt.title("Top 10 des offres d'emploi par type de poste", fontsize=30, pad=30)
plt.suptitle(f"Du {jour_semaine_yesterday} {yesterday.day} {mois_yesterday} {heure_yesterday} au {jour_semaine_today} {today.day} {mois_today} {heure_today} à Lyon", horizontalalignment='center')
plt.tight_layout()
plt.grid(True, linestyle='--', alpha=0.5)
plt.savefig("rome", dpi=200)
# plt.show()

job_par_secteur_activite = big_job_df.value_counts("secteurActiviteLibelle")

top_10 = job_par_secteur_activite.head(10)
top_10 = top_10.sort_values(ascending=True)

plt.figure(figsize=(20, 11))
plt.barh(top_10.index, top_10.values.T)
# Ajouter les valeurs numériques au-dessus de chaque barre
for i in range(len(top_10.index)):
    plt.text(top_10.values[i], i, str(top_10.values[i]), va='center')
plt.xlabel("Nombre d'annonce sur pole emploi")
plt.xticks(rotation=0)
plt.ylabel("Secteur d'activité")
plt.title("Top 10 des offres d'emploi par Secteur d'activité", fontsize=30, pad=30)
plt.suptitle(f"Du {jour_semaine_yesterday} {yesterday.day} {mois_yesterday} {heure_yesterday} au {jour_semaine_today} {today.day} {mois_today} {heure_today} à Lyon", horizontalalignment='center')
plt.tight_layout()
plt.grid(True, linestyle='--', alpha=0.5)
plt.savefig("activite", dpi=200)
# plt.show()


job_par_code_postal = big_job_df.value_counts("code_postal")

top_10 = job_par_code_postal.head(10)
top_10 = top_10.sort_values(ascending=True)

plt.figure(figsize=(20, 11))
plt.barh(top_10.index, top_10.values.T)
# Ajouter les valeurs numériques au-dessus de chaque barre
for i in range(len(top_10.index)):
    plt.text(top_10.values[i], i, str(top_10.values[i]), va='center')
plt.xlabel("Nombre d'annonce sur pole emploi")
plt.xticks(rotation=0)
plt.ylabel("Code INSEE")
plt.title("Top 10 des offres d'emploi par code INSEE", fontsize=30, pad=30)
plt.suptitle(f"Du {jour_semaine_yesterday} {yesterday.day} {mois_yesterday} {heure_yesterday} au {jour_semaine_today} {today.day} {mois_today} {heure_today} à Lyon", horizontalalignment='center')
plt.tight_layout()
plt.grid(True, linestyle='--', alpha=0.5)
plt.savefig("insee", dpi=200)
# plt.show()



# eliminer les entreprise sans nom :
big_job_data_sans_noname_entreprise = big_job_df[big_job_df["nom_entreprise"] != "Pas d'information"]
big_job_data_sans_noname_entreprise = big_job_data_sans_noname_entreprise.value_counts("nom_entreprise")

top_10 = big_job_data_sans_noname_entreprise.head(10)
top_10 = top_10.sort_values(ascending=True)

plt.figure(figsize=(20, 11))
plt.barh(top_10.index, top_10.values.T)
# Ajouter les valeurs numériques au-dessus de chaque barre
for i in range(len(top_10.index)):
    plt.text(top_10.values[i], i, str(top_10.values[i]), va='center')
plt.xlabel("Nombre d'annonce sur pole emploi")
plt.xticks(rotation=0)
plt.ylabel("Entreprise")
plt.title("Top 10 des offres d'emploi par entreprise", fontsize=30, pad=30)
plt.suptitle(f"Du {jour_semaine_yesterday} {yesterday.day} {mois_yesterday} {heure_yesterday} au {jour_semaine_today} {today.day} {mois_today} {heure_today} à Lyon", horizontalalignment='center')
plt.tight_layout()
plt.grid(True, linestyle='--', alpha=0.5)
plt.savefig("entreprise", dpi=200)
# plt.show()



# Twitter / X credential
API_Key = "secret"
API_Key_Secret = "secret"
Bearer_Token = "secret"

OAuth2_ID = "secret"
OAuth2_Secret = "secret"

Access_Token = "secret"
Access_Token_Secret = "secret"


# Gainaing access and connecting to Twitter API using Credentials
client = tweepy.Client(Bearer_Token, API_Key, API_Key_Secret, Access_Token, Access_Token_Secret)

# Creating API instance. This is so we still have access to Twitter API V1 features
auth = tweepy.OAuth1UserHandler(API_Key, API_Key_Secret, Access_Token, Access_Token_Secret)
api = tweepy.API(auth)

# Creating a tweet to test the bot
#client.create_tweet(text="Hello World")

    # Your tweet text
tweet_text = "Offres d'emploi publiées à Lyon aujourd'hui.  Source = https://www.pole-emploi.fr"

# Path to the image file
# List of image file paths
image_paths = ["entreprise.png", "activite.png", "rome.png", "type.png"]


# Upload each image to Twitter's media server and collect the media IDs
media_ids = []
for image_path in image_paths:
    media = api.media_upload(filename=image_path)
    media_ids.append(media.media_id)

# Post a tweet with the uploaded images
client.create_tweet(text=tweet_text, media_ids=media_ids)

# Create an Apprise instance
apobj = apprise.Apprise()

# A sample pushbullet notification
apobj.add('tgram://secret')
apobj.add('discord://secret')

# Then notify these services any time you desire. The below would
# notify all of the services loaded into our Apprise object.
apobj.notify(body='Publication du bot twitter', title='Je viens de publier ceci : ', attach="entreprise.png")


