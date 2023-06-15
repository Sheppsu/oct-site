from osu import Client
from dotenv import load_dotenv
import os
import json

load_dotenv()

redirect_url = os.getenv('OSU_CLIENT_REDIRECT')
client_id = os.getenv('OSU_CLIENT_ID')
client_secret = os.getenv('OSU_CLIENT_SECRET')

client = Client.from_client_credentials(
        client_id, client_secret, redirect_url)
    
map_list = []
map_ids = [3832960, 3205100, 2784412, 2218604, 3580554, 65233, 3767159, 665543, 1101062, 155049, 91796]
for map_id in map_ids:
    map = client.get_beatmap(map_id)
    map_list.append(
        {
            "artist": map.beatmapset.artist,
            "title": map.beatmapset.title,
            "difficulty": map.version,
            "sr": map.difficulty_rating,
            "cs": map.cs,
            "hp": map.drain,
            "od": map.accuracy,
            "ar": map.ar,
            "background": map.beatmapset.covers.cover_2x,
        }
    )

# write the map_list to a json file
with open('map_list.json', 'w') as f:
    json.dump(map_list, f)
    