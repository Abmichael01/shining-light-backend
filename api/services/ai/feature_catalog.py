"""
Default AI features seeded on first run / via management command.

The catalog is database-driven (`AIFeature` model) so admins can toggle
features on/off without code changes. This file just defines the initial
seed data — once seeded, edits happen via Django admin or the API.
"""

DEFAULT_FEATURES = [
    {
        'slug': 'question-generator',
        'name': 'AI Question Generator',
        'description': (
            'Generate exam questions instantly from a subject and topic. '
            'Choose difficulty, question type and count — review, edit and '
            'save into your question bank with one click.'
        ),
        'audience': 'admin',
        'status': 'available',
        'icon': 'Sparkles',
        'route': '/school-admin/question-bank?ai=open',
        'is_active': True,
        'order': 1,
    },
]


def seed_default_features():
    """Idempotently create default AI features. Safe to call repeatedly."""
    from api.models import AIFeature

    created = []
    for feature_data in DEFAULT_FEATURES:
        slug = feature_data['slug']
        feature, was_created = AIFeature.objects.get_or_create(
            slug=slug,
            defaults=feature_data,
        )
        if was_created:
            created.append(slug)
    return created
