from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (CreateView, DeleteView,
                                  DetailView, ListView, UpdateView)

from .models import Category, Comment, Post
from .forms import CommentForm, MainForm
from .constants import MAX_LENGTH


class OnlyAuthorMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user == self.get_object().author


class OnlyPostAuthorMixin(OnlyAuthorMixin):
    pass


class OnlyCommentAuthorMixin(OnlyAuthorMixin):
    pass


class PostListView(ListView):
    model = Post
    queryset = Post.objects.published_posts()
    template_name = 'blog/post_list.html'
    paginate_by = MAX_LENGTH
    context_object_name = 'post_list'


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    slug_field = 'id'
    slug_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        user = self.request.user
        if user.is_authenticated and user == post.author:
            return post
        return get_object_or_404(
            Post,
            pk=self.kwargs['post_id'],
            is_published=True,
            category__is_published=True
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            comments=self.object.comments.all(),
            form=CommentForm()
        )


class CategoryListView(ListView):
    model = Category
    template_name = 'blog/category.html'
    context_object_name = 'post_list'
    paginate_by = MAX_LENGTH

    def get_category(self):
        category_slug = self.kwargs.get('category_slug')
        return get_object_or_404(
            Category,
            slug=category_slug,
            is_published=True
        )

    def get_queryset(self):
        category = self.get_category()
        return category.posts.published_posts()

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            category=self.get_category()
        )


class ProfileDetailView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    context_object_name = 'profile'
    paginate_by = MAX_LENGTH

    def get_user_object(self):
        return get_object_or_404(User, username=self.kwargs.get('username'))

    def get_context_data(self, **kwargs):
        author = self.get_user_object()
        posts = (author.posts.all() if self.request.user == author
                 else author.posts.published_posts())

        paginator = Paginator(posts, self.paginate_by)
        page = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page)

        return super().get_context_data(**kwargs, page_obj=page_obj)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = (
        'username', 'first_name', 'last_name', 'email'
    )
    template_name = 'blog/edit_profile.html'

    def get_object(self):
        # Проверка, что редактируемый профиль принадлежит текущему пользователю
        if self.kwargs['username'] != self.request.user.username:
            raise PermissionDenied
        return self.request.user

    def get_success_url(self):
        return reverse(
            'blog:profile', args=[self.request.user.username]
        )


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/create.html'
    form_class = MainForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:profile', kwargs={'username': self.request.user.username}
        )


class PostUpdateView(OnlyPostAuthorMixin, UpdateView):
    model = Post
    template_name = 'blog/create.html'
    slug_field = 'id'
    slug_url_kwarg = 'post_id'
    form_class = MainForm

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != self.request.user:
            return redirect(
                'blog:post_detail',
                post_id=self.kwargs[self.slug_url_kwarg])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'blog:post_detail', args=[self.kwargs[self.slug_url_kwarg]]
        )


class PostDeleteView(OnlyPostAuthorMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    slug_field = 'id'
    slug_url_kwarg = 'post_id'
    success_url = reverse_lazy('blog:post_list')

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            form=MainForm(instance=self.object)
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/detail.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(
            Post,
            id=self.kwargs.get('post_id')
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail', kwargs={'post_id': self.kwargs.get('post_id')}
        )


class CommentUpdateView(OnlyCommentAuthorMixin, UpdateView):
    model = Comment
    template_name = 'blog/comment.html'
    slug_field = 'id'
    slug_url_kwarg = 'comment_id'
    form_class = CommentForm

    def get_success_url(self):
        return reverse(
            'blog:post_detail', kwargs={'post_id': self.kwargs.get('post_id')}
        )


class CommentDeleteView(OnlyCommentAuthorMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    slug_field = 'id'
    slug_url_kwarg = 'comment_id'
    form_class = CommentForm

    def get_success_url(self):
        return reverse(
            'blog:post_detail', kwargs={'post_id': self.kwargs.get('post_id')}
        )

    def delete(self, request, *args, **kwargs):
        post = self.get_object().post
        super().delete(request, *args, **kwargs)
        return redirect(reverse('blog:post_detail',
                                kwargs={'post_id': post.pk}))
