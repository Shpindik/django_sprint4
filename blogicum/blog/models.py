from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count
from django.utils import timezone

from .constants import MAX_TEXT_LENGTH, PAGINATE_DISPLAY


User = get_user_model()


class FilterQuerySet(models.QuerySet):
    def get_posts(
            self,
            apply_filters=True,
            apply_select_related=True,
            apply_annotate=True
    ):
        posts = self  # Переименовано для большей ясности
        if apply_filters:
            posts = posts.filter(
                is_published=True,
                category__is_published=True,
                pub_date__lt=timezone.now()
            )
        if apply_select_related:
            posts = posts.select_related(
                'author',
                'category',
                'location'
            )
        if apply_annotate:
            posts = posts.annotate(
                comment_count=Count('comments')
            ).order_by(*self.model._meta.ordering)
        return posts


class PublicationBaseModel(models.Model):
    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубликовано',
        help_text='Снимите галочку, чтобы скрыть публикацию.'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )

    class Meta:
        abstract = True
        ordering = ('-created_at',)


class Category(PublicationBaseModel):
    title = models.CharField(
        max_length=MAX_TEXT_LENGTH,
        verbose_name='Заголовок'
    )
    description = models.TextField(verbose_name='Описание')
    slug = models.SlugField(
        unique=True,
        verbose_name='Идентификатор',
        help_text='Идентификатор страницы для URL; разрешены символы латиницы,'
                  ' цифры, дефис и подчёркивание.'
    )

    class Meta(PublicationBaseModel.Meta):
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.title[:PAGINATE_DISPLAY]


class Location(PublicationBaseModel):
    name = models.CharField(
        max_length=MAX_TEXT_LENGTH,
        verbose_name='Название места'
    )

    class Meta(PublicationBaseModel.Meta):
        verbose_name = 'местоположение'
        verbose_name_plural = 'Местоположения'

    def __str__(self):
        return self.name[:PAGINATE_DISPLAY]


class Post(PublicationBaseModel):
    title = models.CharField(
        max_length=MAX_TEXT_LENGTH,
        verbose_name='Заголовок'
    )
    text = models.TextField(verbose_name='Текст')
    pub_date = models.DateTimeField(
        verbose_name='Дата и время публикации',
        help_text='Если установить дату и время в будущем — '
                  'можно делать отложенные публикации.'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор публикации'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Местоположение'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Категория'
    )
    image = models.ImageField('Фото', upload_to='posts_images', blank=True)
    objects = FilterQuerySet.as_manager()

    class Meta(PublicationBaseModel.Meta):
        verbose_name = 'публикация'
        verbose_name_plural = 'Публикации'
        ordering = ('-pub_date',)
        default_related_name = 'posts'

    def __str__(self):
        return self.title[:PAGINATE_DISPLAY]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name='Пост'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    text = models.TextField(verbose_name='Комментарий')
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'комментарий'
        verbose_name_plural = 'Комментарии'
        default_related_name = 'comments'
        ordering = ('created_at',)

    def __str__(self):
        return self.text[:PAGINATE_DISPLAY]
