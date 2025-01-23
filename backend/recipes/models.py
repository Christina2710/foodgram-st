from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


MIN_COOKING_TIME = 1
MIN_AMOUNT = 1


class CustomUser(AbstractUser):
    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='Адрес электронной почты'
    )
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    username = models.CharField(max_length=150, unique=True, validators=[
        RegexValidator(
            regex=r'^[\w.@+-]+$',
            message='Имя пользователя может содержать только'
                    'буквы, цифры, и символы: . @ + - _'
        )
    ],
        verbose_name='Имя пользователя'
    )
    # Поле для аватара
    avatar = models.ImageField(
        upload_to='avatar_images',
        blank=True,
        verbose_name='Аватар'
    )
    # Поле, указанное в USERNAME_FIELD считается обязательным.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        ordering = ('username', )  # Указываем поля для сортировки
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Ingredient(models.Model):
    name = models.CharField(max_length=128, verbose_name='Название')
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'продукт'
        verbose_name_plural = 'Продукты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_measurement'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(max_length=256, verbose_name='Название')
    image = models.ImageField(
        upload_to='recipes_images',
        verbose_name='Картинка'
    )
    text = models.TextField(verbose_name='Текстовое описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    cooking_time = models.PositiveIntegerField(
        help_text="Время приготовления в минутах",
        verbose_name='Время приготовления',
        validators=(MinValueValidator(MIN_COOKING_TIME),)
    )
    pub_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_ingredients',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='recipe_ingredients',
        on_delete=models.CASCADE,
        verbose_name='Продукт'
    )
    amount = models.IntegerField(
        verbose_name='Мера',
        validators=(MinValueValidator(MIN_AMOUNT),)
    )

    class Meta:
        verbose_name = 'продукт рецепта'
        verbose_name_plural = 'Продукты рецепта'

    def __str__(self):
        return (f'{self.ingredient.name}: '
                f'{self.amount} '
                f'{self.ingredient.measurement_unit}')


class AbstractRecipeRelation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        # Используется динамическое имя для related_name
        related_name='%(class)ss',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        # Используется динамическое имя для related_name
        related_name='%(class)ss',
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_%(class)s_user_recipe'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'


class FavoriteRecipe(AbstractRecipeRelation):
    class Meta(AbstractRecipeRelation.Meta):
        verbose_name = 'избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(AbstractRecipeRelation):
    class Meta(AbstractRecipeRelation.Meta):
        verbose_name = 'рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'


class Subscribe(models.Model):
    # Это пользователь, который совершает действие подписки
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='users',
        verbose_name='Пользователь'
    )
    # Это пользователь, на которого совершается подписка
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authors',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_subscription'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.author.username}'
