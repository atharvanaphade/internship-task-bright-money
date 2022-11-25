from django.shortcuts import render

from rest_framework.response import Response
from rest_framework import status, pagination
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

import plaid
from plaid import Client
import json, datetime

from token_exchange.serializers import AccessTokenSerializer
from token_exchange.models import BankItem, APILog

from django.conf import settings

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from token_exchange.tasks import get_transactions, delete_transactions

# Create your views here.

client = plaid.Client(client_id=settings.PLAID_CLIENT_ID, secret=settings.PLAID_SECRET, environment=settings.PLAID_ENV)

class LinkToken(APIView):
    '''
    Get Link Token API
    '''

    def post(self, request):
        user = request.user

        if user.is_authenticated:
            configs = {
				'user': {
					'client_user_id': settings.PLAID_CLIENT_ID
					},

				'products': ['auth', 'transactions'],
				'client_name': "Plaid Test App",
				'country_codes': ['US'],
				'language': 'en',
				'webhook': 'https://sample-webhook-uri.com',
				'link_customization_name': 'default',
				'account_filters': {
				  'depository': {
				      'account_subtypes': ['checking', 'savings'],
				  },
				},
			}

            response = client.LinkToken.create(configs)
            api_log = APILog.objects.create(
                request=response['request_id'],
                api_type="get_link_token",
            )
            api_log.save()
            return Response(
                data=response,
                status=status.HTTP_201_CREATED
            )

        return Response({"error": "User is not Authenticated!"}, status=status.HTTP_401_UNAUTHORIZED)

class AccessToken(APIView):
    '''
    To retrieve access token to a item
    '''

    def post(self, request):

        request_data = request.POST
        public_token = request_data.get('public_token')
        try:
            exchange_response = client.Item.public_token.exchange(public_token)
            serializer = AccessTokenSerializer(data=exchange_response)
            if serializer.is_valid():
                access_token = serializer.validated_data['access_token']
                bank_item = BankItem.objects.create(
                    access_token=access_token,
                    bank_item_id=serializer.validated_data['item_id'],
                    request_id=serializer.validated_data['request_id'],
                    user=self.request.user
                )
                bank_item.save()
                api_log = APILog.objects.create(
                    request_id=serializer.validated_data['request_id'],
                    api_type="get_access_token"
                )
                api_log.save()
                get_transactions(access_token).delay()
        except plaid.errors.PlaidError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        return Response(data=exchange_response, status=status.HTTP_200_OK)

class ItemsView(APIView):

    pagination.PageNumberPagination.page_size = 10

    def get(self,request):

        bank_item = BankItem.objects.filter(user=self.request.user)
        if len(bank_item)>0:
            
            try:
                access_token_obj_list = bank_item.values('access_token')
                items_responses=[]
                for access_token_obj in access_token_obj_list:
                    access_token = access_token_obj['access_token']
                    item_response=client.Item.get(access_token)
                    items_responses.append(item_response['item'])

                    api_log_obj = APILog.objects.create(
                        request_id=item_response['request_id'], 
                        api_type="get_items"
                    )
                    api_log_obj.save()
                
            except plaid.errors.PlaidError as e:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            return Response(data={'items_list': items_responses}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

class AccountsView(APIView):

    pagination.PageNumberPagination.page_size = 10

    def get(self,request):
        bank_item = BankItem.objects.filter(user=self.request.user)
        if len(bank_item)>0:
            
            try:
                access_token_obj_list = bank_item.values('access_token')
                accounts_responses=[]
                for access_token_obj in access_token_obj_list:
                    access_token = access_token_obj['access_token']
                    account_response = client.Accounts.get(access_token)
                    accounts_responses.append(account_response['accounts'])

                    api_log_obj = APILog.objects.create(
                        request_id=account_response['request_id'], 
                        api_type="get_accounts"
                    )
                    api_log_obj.save()

            except plaid.errors.PlaidError as e:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            return Response(data={'accounts_list': accounts_responses}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

class TransactionView(APIView):

    pagination.PageNumberPagination.page_size = 10

    def get(self,request):

        bank_item = BankItem.objects.filter(user=self.request.user)
        if len(bank_item)>0:
            
            try:
                access_token_obj_list = bank_item.values('access_token')
                transactions_responses=[]

                start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-30))
                end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())

                for access_token_obj in access_token_obj_list:
                    access_token = access_token_obj['access_token']
                    transaction_response = client.Transactions.get(access_token,start_date,end_date)
                    transactions_responses.append(transaction_response['transactions'])

                    api_log_obj = APILog.objects.create(
                        request_id=transaction_response['request_id'], 
                        api_type="get_transactions"
                    )
                    api_log_obj.save()
                
            except plaid.errors.PlaidError as e:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            return Response(data={'transactions_list': transactions_responses}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

@csrf_exempt
def transactionWebhook(request):
	request_data = request.POST
	webhook_type = request_data.get('webhook_type')
	webhook_code = request_data.get('webhook_code')


	if webhook_type == 'TRANSACTIONS':
		item_id = request_data.get('item_id')
		
		if webhook_code == 'TRANSACTIONS_REMOVED':
			removed_transactions = request_data.get('removed_transactions')
			delete_transactions.delay(item_id, removed_transactions)

		else:
			new_transactions = request_data.get('new_transactions')
			get_transactions.delay(None, item_id, new_transactions)

	return HttpResponse('Webhook received', status=status.HTTP_200_OK)
