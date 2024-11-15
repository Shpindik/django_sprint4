from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (CreateView, DeleteView,
                                  DetailView, ListView, UpdateView)

from .constants import POSTS_PER_PAGE_LIMIT
from .forms import CommentForm, PostForm
from .models import Category, Comment, Post


class OnlyAuthorMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user == self.get_object().author


class PostListView(ListView):
    model = Post
    queryset = Post.objects.get_posts()
    template_name = 'blog/post_list.html'
    paginate_by = POSTS_PER_PAGE_LIMIT
    context_object_name = 'post_list'


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    slug_field = 'id'
    slug_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        post = get_object_or_404(queryset, pk=self.kwargs['post_id'])
        if self.request.user == post.author:
            return post
        return get_object_or_404(queryset.get_posts(
            apply_select_related=False,
            apply_annotate=False
        ), pk=self.kwargs['post_id'])

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
    paginate_by = POSTS_PER_PAGE_LIMIT

    def get_category(self):
        return get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )

    def get_queryset(self):
        return self.get_category().posts.get_posts()

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

    def get_author(self):
        return get_object_or_404(
            User,
            **{self.slug_field: self.kwargs[self.slug_url_kwarg]}
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            page_obj=Paginator(
                self.get_author().posts.get_posts(
                    apply_filters=self.request.user != self.get_author(),),
                POSTS_PER_PAGE_LIMIT
            ).get_page(self.request.GET.get('page', 1))
        )


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ('username', 'first_name', 'last_name', 'email')
    template_name = 'blog/edit_profile.html'

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse(
            'blog:profile', args=[self.request.user.username]
        )


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/create.html'
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:profile', args=[self.request.user.username]
        )


class PostUpdateView(OnlyAuthorMixin, UpdateView):
    model = Post
    template_name = 'blog/create.html'
    slug_field = 'id'
    slug_url_kwarg = 'post_id'
    form_class = PostForm

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != self.request.user:
            return redirect(
                'blog:post_detail',
                self.kwargs[self.slug_url_kwarg])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'blog:post_detail', args=[self.kwargs[self.slug_url_kwarg]]
        )


class PostDeleteView(OnlyAuthorMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    slug_field = 'id'
    slug_url_kwarg = 'post_id'
    success_url = reverse_lazy('blog:post_list')

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            form=PostForm(instance=self.object)
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/detail.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(
            Post,
            id=self.kwargs['post_id']
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail', args=[self.kwargs['post_id']]
        )


class BaseCommentView(OnlyAuthorMixin):
    model = Comment
    template_name = 'blog/comment.html'
    slug_field = 'id'
    slug_url_kwarg = 'comment_id'
    form_class = CommentForm

    def get_success_url(self):
        return reverse(
            'blog:post_detail', args=[self.kwargs['post_id']]
        )


class CommentUpdateView(BaseCommentView, UpdateView):
    pass


class CommentDeleteView(BaseCommentView, DeleteView):
    def delete(self, request, *args, **kwargs):
        super().delete(request, *args, **kwargs)
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
