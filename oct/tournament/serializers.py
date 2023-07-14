from rest_framework import serializers
from tournament.models import MappoolBeatmap

class MappoolBeatmapSerializer(serializers.ModelSerializer):
    class Meta:
        model = MappoolBeatmap
        fields = ['beatmap_id', 'modification', 'artist', 'title', 'difficulty', 'star_rating', 'overall_difficulty', 'approach_rate', 'circle_size', 'health_drain', 'cover']
