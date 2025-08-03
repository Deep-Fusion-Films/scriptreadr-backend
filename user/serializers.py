from rest_framework.serializers import ModelSerializer
from user.models import User
from rest_framework import serializers


class UserSerializer(ModelSerializer):
    email = serializers.EmailField()
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password:
            instance.set_password(password)
        else:
            instance.set_unusable_password()
        instance.save()
        return instance

 