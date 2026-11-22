from django.urls import path
from .views import Asset3DListView, AnimationClipListView

urlpatterns = [
    path("api/assets/3d/", Asset3DListView.as_view(), name="assets-3d-list"),
    path("api/assets/animations/", AnimationClipListView.as_view(), name="assets-animations-list"),
]
