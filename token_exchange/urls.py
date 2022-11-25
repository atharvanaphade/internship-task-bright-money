from django.urls import path

from token_exchange.views import LinkToken, AccessToken, ItemsView, AccountsView, TransactionView, transactionWebhook

urlpatterns = [
    path('link_token/', LinkToken.as_view(), name='get_plaid_link_token'),
    path('get_access_token/', AccessToken.as_view(), name='plain_link_public_token'),
    path('get_items/', ItemsView.as_view(), name='get_items'),
    path('get_accounts/', AccountsView.as_view(), name='get_accounts'),
    path('get_transactions/', TransactionView.as_view(), name='get_transactions'),
    path('transaction_webhook/', transactionWebhook, name='transaction_webhook'),
]
