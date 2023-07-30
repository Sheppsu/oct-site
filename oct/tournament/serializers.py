from .models import *

from typing import Type, List, Union, Iterable
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor, ManyToManyDescriptor
from time import monotonic


_SERIALIZERS: List[Type['Serializer']] = []


class Serializer:
    model: Type[models.Model]
    fields: List[str]

    def __init__(self, obj: Union[models.Model, Iterable], many: bool = False):
        self.obj: Union[models.Model, Iterable] = obj
        self.many: bool = many

    def _get_serializer(self, obj) -> Type['Serializer']:
        for serializer in _SERIALIZERS:
            if isinstance(obj, serializer.model):
                return serializer
        raise NotImplementedError(f"Could not find serializer for {obj.__class__.__name__}")

    def _transform(self, obj, fields):
        data = {}
        for field in fields:
            field_type = getattr(self.model, field)
            value = getattr(obj, field)
            if value is None:
                data[field] = value
                continue
            if isinstance(field_type, ForwardManyToOneDescriptor):
                serializer = self._get_serializer(value)
                data[field] = serializer(value).serialize()
            elif isinstance(field_type, ManyToManyDescriptor):
                serializer = self._get_serializer(value.model)
                data[field] = list(map(lambda o: serializer(o).serialize(), value))
            else:
                data[field] = value
        return data

    def serialize(self, exclude=None, extra=None):
        start = monotonic()
        fields = set(self.fields)
        if exclude is not None: fields -= set(exclude)
        if extra is not None: fields += set(extra)

        transform = lambda obj: self._transform(obj, fields)
        ret = transform(self.obj) if not self.many else list(map(transform, self.obj))
        return ret


def serializer(cls):
    new_cls = type(cls.__name__, (Serializer, cls), {})
    _SERIALIZERS.append(new_cls)
    return new_cls


@serializer
class MappoolBeatmapSerializer:
    model = MappoolBeatmap
    fields = [
        'beatmap_id',
        'modification',
        'artist',
        'title',
        'difficulty',
        'star_rating',
        'overall_difficulty',
        'approach_rate',
        'circle_size',
        'health_drain',
        'cover'
    ]


@serializer
class UserSerializer:
    model = User
    fields = ['osu_id', 'osu_username', 'osu_avatar', 'osu_cover', 'is_admin']


@serializer
class TournamentIterationSerializer:
    model = TournamentIteration
    fields = ['name', 'full_name', 'users', 'start_date', 'end_date', 'thumbnail', 'links']


@serializer
class TournamentInvolvementSerializer:
    model = TournamentInvolvement
    fields = ['user', 'tournament_iteration', 'roles', 'join_date']
