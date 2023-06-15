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
    
final_map_list = []

quals_map_ids = {
    "round": "qualifiers",
    "nm": [3832960, 3205100, 2784412, 2218604],
    "hd": [3580554, 65233],
    "hr": [3767159, 665543],
    "dt": [1101062, 155049, 91796]
}

ro32_map_ids = {
    "round": "round of 32",
    "nm": [2784506, 3266455, 3477179, 2709210],
    "hd": [1596848, 2806440],
    "hr": [44406, 2244053],
    "dt": [3358427, 3299370, 2260961],
    "tb": [3423336]
}

map_ids = [quals_map_ids, ro32_map_ids]

for id_set in map_ids:
    map_list = []

    iter_dict = iter(id_set)
    next(iter_dict)

    for key in iter_dict:
        
        for index, map_id in enumerate(id_set[key], 1):
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
                    "mod": f"{key.upper()}{index}",
                    "id": map.id,
                }
            )
    round = id_set["round"]
    final_map_list.append({"stage": round.capitalize(), "maps": map_list})


with open('map_list.json', 'w') as f:
    json.dump(final_map_list, f)
    