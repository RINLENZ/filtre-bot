import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import PeerIdInvalid, ChannelInvalid, UserNotParticipant
from dotenv import load_dotenv
import logging

# --- Configuration de la journalisation ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Charger les variables d'environnement
load_dotenv()

# --- Configuration du bot ---
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN") # Le token de votre bot, obtenu via BotFather

# L'ID du groupe cible où le bot écoutera les messages.
# Assurez-vous que le bot est administrateur dans ce groupe.
# Un ID de groupe commence généralement par -100.
groupe_cible_id = int(os.getenv("GROUPE_CIBLE"))

# Liste des canaux où le bot va rechercher les fichiers.
# Les ID numériques (ex: -1001234567890) sont souvent plus fiables que les usernames/liens.
# Si vous utilisez des usernames (ex: @mycanals237), le bot doit être membre ou avoir accès.
channels_to_search = [
    "@mycanals237",
    "@Mycanalsfr",
    "@spartacus_tv",
    "https://t.me/+0-3FLuSLHR5iOWVk", # Canal privé - le bot doit y être membre
    "https://t.me/+XX7l6O4z4WRkOTRk", # Canal privé
    "https://t.me/+dq3-YQ3nfBxmZDNk", # Canal privé
    "https://t.me/+BebUcBgRYBJhOWY0"  # Canal privé
]

PHOTO_PATH = "result_image.jpg" # Chemin vers votre image de résultat

# Initialisation du client Pyrogram
app = Client(
    "filtre_bot_session", # Nom de la session
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

# --- Fonction utilitaire pour obtenir le nom affichable d'un canal ---
async def get_channel_display_name(chat_id_or_username):
    try:
        chat = await app.get_chat(chat_id_or_username)
        if chat.username:
            return f"@{chat.username}"
        elif chat.title:
            return chat.title
        return "Canal inconnu"
    except Exception as e:
        logging.warning(f"Impossible d'obtenir le nom affichable pour '{chat_id_or_username}': {e}")
        return chat_id_or_username # Retourne l'input si échec

# --- Gestionnaire des nouveaux messages ---
@app.on_message(filters.group & filters.chat(groupe_cible_id) & filters.text)
async def filtre_handler(client, message):
    query = message.text.strip().lower()

    # Pyrogram fournit directement les informations de l'expéditeur et du chat
    sender_name = message.from_user.first_name if message.from_user else "Utilisateur inconnu"
    group_name = message.chat.title if message.chat else "Groupe inconnu"

    logging.info(f"Requête reçue : '{query}' de '{sender_name}' dans le groupe '{group_name}'.")

    all_buttons = []
    max_results_per_query = 5
    results_count = 0
    found_any_file = False

    response_text = f"""🌿 **Résultats de votre recherche pour : `{query}`**

🙋 Demandé par : `{sender_name}`
👥 Dans le groupe : `{group_name}`

---
"""

    for channel_input in channels_to_search:
        if results_count >= max_results_per_query:
            logging.info(f"Nombre maximum de résultats ({max_results_per_query}) atteint pour la requête '{query}'. Arrêt de la recherche.")
            break

        try:
            # Récupérer l'ID du canal. Pyrogram peut gérer usernames, ID et liens d'invitation.
            chat_info = await client.get_chat(channel_input)
            channel_id = chat_info.id
            channel_display_name = await get_channel_display_name(channel_id)
            logging.debug(f"Début de la recherche dans le canal : {channel_display_name} (ID: {channel_id})")

            # Itérer sur les messages du canal avec la requête de recherche
            async for msg in client.search_messages(chat_id=channel_id, query=query, limit=2):
                file_info = None
                file_name = "Fichier sans nom"
                file_size_mb = 0

                if msg.document:
                    file_info = msg.document
                    file_name = file_info.file_name or "Fichier sans nom"
                    file_size_mb = round(file_info.file_size / (1024 * 1024), 2) if file_info.file_size else 0
                elif msg.photo:
                    # Pour les photos, utilisez la dernière taille disponible (généralement la plus grande)
                    file_info = msg.photo
                    file_name = f"Photo_{msg.id}.jpg"
                    file_size_mb = round(file_info.file_size / (1024 * 1024), 2) if file_info.file_size else 0
                elif msg.video:
                    file_info = msg.video
                    file_name = file_info.file_name or f"Vidéo_{msg.id}.mp4"
                    file_size_mb = round(file_info.file_size / (1024 * 1024), 2) if file_info.file_size else 0
                else:
                    logging.debug(f"Message {msg.id} dans {channel_display_name} ne contient ni fichier, ni photo, ni vidéo. Ignoré.")
                    continue

                if file_info:
                    found_any_file = True
                    results_count += 1

                    # Construire l'URL du message.
                    # Pour les canaux privés, Pyrogram peut générer des liens `t.me/c/ID/message_id`.
                    # Pour les canaux publics, `t.me/username/message_id`.
                    message_url = msg.link
                    
                    if message_url:
                        response_text += (
                            f"📁 **{file_name}**\n"
                            f"💾 Taille : `{file_size_mb} Mo`\n"
                            f"🔗 Canal : {channel_display_name}\n"
                            f"---\n"
                        )
                        all_buttons.append([InlineKeyboardButton(f"📥 {file_name}", url=message_url)])
                    else:
                        logging.warning(f"Saut du bouton pour '{file_name}' en raison d'une URL non générée.")
                    
                    if results_count >= max_results_per_query:
                        logging.debug(f"Limite de résultats atteinte pour le canal actuel : {channel_display_name}")
                        break

        except (PeerIdInvalid, ChannelInvalid, UserNotParticipant) as e:
            logging.warning(f"Problème d'accès au canal '{channel_input}': {e}. Le bot est-il membre ou administrateur?")
        except Exception as e:
            logging.error(f"Erreur inattendue lors de la recherche dans le canal '{channel_input}' : {e}", exc_info=True)
            pass

    response_text += "\n🎁 Code promo 1XBET : `1KAT` (utilisez ce code pour vos paris !)"

    try:
        reply_markup = InlineKeyboardMarkup(all_buttons) if all_buttons else None
        
        photo_to_send = PHOTO_PATH if os.path.exists(PHOTO_PATH) else None

        if found_any_file:
            if photo_to_send:
                await message.reply_photo(
                    photo=photo_to_send,
                    caption=response_text,
                    reply_markup=reply_markup
                )
                logging.info(f"Résultats envoyés avec photo et boutons pour la requête '{query}'.")
            else:
                await message.reply_text(
                    text=response_text,
                    reply_markup=reply_markup
                )
                logging.info(f"Résultats envoyés sans photo mais avec boutons pour la requête '{query}'.")
        else:
            await message.reply_text(
                text=f"❌ **Désolé, aucun fichier trouvé** pour la requête : `{query}`.\n\n"
                     "Vérifiez l'orthographe ou essayez un autre mot-clé. Nous ajoutons du nouveau contenu régulièrement !",
                parse_mode='markdown'
            )
            logging.info(f"Aucun fichier trouvé pour la requête '{query}'. Message 'aucun résultat' envoyé.")
    except Exception as e:
        logging.error(f"Échec de l'envoi de la réponse pour la requête '{query}' : {e}", exc_info=True)

# --- Démarrage du client Pyrogram ---
if __name__ == "__main__":
    logging.info("✅ Démarrage du bot Pyrogram...")
    app.run() # Bloque l'exécution et maintient le bot en ligne
    logging.info("Bot Pyrogram déconnecté.")