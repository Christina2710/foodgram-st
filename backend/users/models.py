from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class MyUser(AbstractUser):
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    username = models.CharField(max_length=150, unique=True, validators=[
        RegexValidator(
            regex=r'^[\w.@+-]+$',
            message='Имя пользователя может содержать только'
                  + 'буквы, цифры, и символы: . @ + - _'
        )
    ])
    # Поле для аватара
    avatar = models.ImageField(
        upload_to='avatar_images',
        blank=True,
        verbose_name='Аватар'
    )
    # Поле, указанное в USERNAME_FIELD считается обязательным.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')
