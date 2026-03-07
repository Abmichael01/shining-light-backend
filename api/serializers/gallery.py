from rest_framework import serializers
from api.models.academic.gallery import GalleryGroup, GalleryImage

class GalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryImage
        fields = ['id', 'image', 'group', 'title', 'uploaded_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.image:
             data['image'] = request.build_absolute_uri(instance.image.url)
        return data

class GalleryGroupSerializer(serializers.ModelSerializer):
    image_count = serializers.IntegerField(source='images.count', read_only=True)
    
    class Meta:
        model = GalleryGroup
        fields = ['id', 'name', 'description', 'is_system', 'image_count', 'created_at']
        read_only_fields = ['is_system', 'created_at']

class GalleryGroupDetailSerializer(GalleryGroupSerializer):
    images = GalleryImageSerializer(many=True, read_only=True)
    
    class Meta(GalleryGroupSerializer.Meta):
        fields = GalleryGroupSerializer.Meta.fields + ['images']
