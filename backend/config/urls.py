from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView
from apps.identity import views as auth
from . import api
from . import health
from .schema import document_actions
from apps.payments.views import skipcash_webhook

document_actions(api,auth)

router=DefaultRouter(trailing_slash=False)
for name,(model,read,write,readonly) in api.REGISTRY.items():
    router.register(name,api.create_viewset(model,read,write,readonly),basename=name)

urlpatterns=[
 path('api/v1/health/live',health.live),
 path('api/v1/health/ready',health.ready),
 path('api/v1/payments/webhooks/skipcash',skipcash_webhook),
 path('api/v1/admin/payment-attempts',api.payment_attempts),
 path('api/v1/admin/payment-attempts/<uuid:pk>/reconcile',api.reconcile_card),
 path('api/v1/admin/notifications',api.notification_jobs),
 path('api/v1/admin/notifications/<uuid:pk>/retry',api.notification_jobs),
 path('api/v1/schema',SpectacularAPIView.as_view(),name='schema'),
 path('api/v1/docs',SpectacularSwaggerView.as_view(url_name='schema')),
 path('api/v1/auth/csrf',auth.csrf),path('api/v1/auth/register',auth.register),path('api/v1/auth/login',auth.signin),
 path('api/v1/auth/session',auth.session),path('api/v1/auth/logout',auth.signout),
 path('api/v1/auth/otp/request',auth.request_otp),path('api/v1/auth/otp/verify',auth.verify_otp),
 path('api/v1/auth/password/reset-request',auth.password_reset_request),
 path('api/v1/auth/password/reset-confirm',auth.password_reset_confirm),
 path('api/v1/auth/password/change',auth.password_change),
 path('api/v1/store/config',api.config),path('api/v1/store/products',api.catalog),path('api/v1/store/products/<slug:code>',api.catalog),
 path('api/v1/analytics/consent',api.analytics_consent),path('api/v1/analytics/product-view',api.product_view),
 path('api/v1/store/homepage',api.content),path('api/v1/store/pages/<slug:slug>',api.content),
 path('api/v1/store/bundles',api.public_bundles),
 path('api/v1/admin/promotions/preview',api.promotion_preview),
 path('api/v1/store/products/<uuid:product_id>/reviews',api.reviews),
 path('api/v1/store/<slug:resource>',api.public_lists),
 path('api/v1/cart',api.cart),path('api/v1/checkout/quote',api.quote),path('api/v1/checkout/orders',api.place),
 path('api/v1/cart/bundles',api.cart_bundles),
 path('api/v1/account/orders',api.my_orders),path('api/v1/orders/<uuid:order_id>',api.my_orders),
 path('api/v1/orders/<uuid:order_id>/invoice',api.invoice),path('api/v1/account/wishlist',api.wishlist),
 path('api/v1/account/addresses',api.addresses),path('api/v1/account/addresses/<uuid:pk>',api.addresses),
 path('api/v1/admin/resources',api.resources),path('api/v1/admin/settings',api.admin_settings),path('api/v1/admin/dashboard',api.dashboard),
 path('api/v1/admin/inventory',api.inventory),path('api/v1/admin/orders',api.admin_orders),
 path('api/v1/admin/orders/<uuid:pk>',api.admin_orders),path('api/v1/admin/orders/<uuid:pk>/<slug:command>',api.admin_orders),
 path('api/v1/admin/refunds/<uuid:pk>/confirm',api.confirm_refund),
 path('api/v1/admin/imports',api.import_jobs),path('api/v1/admin/imports/<uuid:pk>',api.import_jobs),path('api/v1/admin/imports/<uuid:pk>/<slug:command>',api.import_jobs),
 path('api/v1/admin/products/<uuid:pk>/variants',api.add_variant),path('api/v1/admin/<slug:resource>/<uuid:pk>/publish',api.publish_resource),
 path('api/v1/admin/products/<uuid:pk>/attributes',api.product_attributes),
 path('api/v1/admin/',include(router.urls)),
]
if settings.DEBUG:urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
